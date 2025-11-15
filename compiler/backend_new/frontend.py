"""High level Compiscript frontend that builds the IR tree."""

from __future__ import annotations

import ast as pyast
import os
import sys
from typing import List

from antlr4 import FileStream, CommonTokenStream

from .ir_nodes import (
    ProgramIR,
    GlobalVariable,
    FunctionIR,
    Parameter,
    BlockStmt,
    VarDeclStmt,
    PrintStmt,
    ReturnStmt,
    Statement,
    Expression,
    IntLiteral,
    StringLiteral,
    VarExpr,
    BinaryExpr,
    CallExpr,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
GRAMMAR_DIR = os.path.join(PROJECT_ROOT, "program", "grammar")
GRAMMAR_GEN_DIR = os.path.join(GRAMMAR_DIR, "gen")
for path in (GRAMMAR_GEN_DIR, GRAMMAR_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from CompiscriptVisitor import CompiscriptVisitor


class _ExprBuilder(pyast.NodeVisitor):
    def build(self, text: str) -> Expression:
        node = pyast.parse(text, mode="eval").body
        return self.visit(node)

    def visit_Name(self, node: pyast.Name) -> Expression:
        return VarExpr(name=node.id)

    def visit_Constant(self, node: pyast.Constant) -> Expression:
        if isinstance(node.value, int):
            return IntLiteral(value=node.value)
        if isinstance(node.value, str):
            return StringLiteral(value=node.value)
        raise NotImplementedError(f"Unsupported literal {node.value!r}")

    def visit_Call(self, node: pyast.Call) -> Expression:
        if not isinstance(node.func, pyast.Name):
            raise NotImplementedError("Only simple function calls supported")
        callee = node.func.id
        args = [self.visit(arg) for arg in node.args]
        return CallExpr(callee=callee, args=args)

    def visit_BinOp(self, node: pyast.BinOp) -> Expression:
        if not isinstance(node.op, pyast.Add):
            raise NotImplementedError("Only addition is supported")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return BinaryExpr(op="+", left=left, right=right)

    def generic_visit(self, node):
        raise NotImplementedError(f"Unsupported expression: {pyast.dump(node)}")


class IRBuilder(CompiscriptVisitor):
    """Builds ProgramIR from an ANTLR parse tree (limited subset)."""

    def __init__(self) -> None:
        super().__init__()
        self.expr_builder = _ExprBuilder()

    def build(self, source_path: str) -> ProgramIR:
        stream = FileStream(source_path, encoding="utf-8")
        lexer = CompiscriptLexer(stream)
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        tree = parser.program()
        return self.visitProgram(tree)

    # ---------------- Program / Blocks ----------------

    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        globals: List[GlobalVariable] = []
        functions: List[FunctionIR] = []
        main_statements: List[Statement] = []

        stmts = ctx.statement()
        for stmt_ctx in stmts:
            node = None
            if stmt_ctx.functionDeclaration():
                node = self.visitFunctionDeclaration(stmt_ctx.functionDeclaration())
            elif stmt_ctx.variableDeclaration():
                node = self.visitVariableDeclaration(stmt_ctx.variableDeclaration())
            elif stmt_ctx.printStatement():
                node = self.visitPrintStatement(stmt_ctx.printStatement())
            else:
                node = self.visitChildren(stmt_ctx)
            if isinstance(node, FunctionIR):
                functions.append(node)
            elif isinstance(node, Statement):
                main_statements.append(node)

        main_block = BlockStmt(statements=main_statements)
        return ProgramIR(globals=globals, classes=[], functions=functions, main_block=main_block)

    def _build_block(self, block_ctx: CompiscriptParser.BlockContext) -> BlockStmt:
        statements: List[Statement] = []
        for stmt_ctx in block_ctx.statement():
            node = None
            if stmt_ctx.returnStatement():
                node = self.visitReturnStatement(stmt_ctx.returnStatement())
            elif stmt_ctx.variableDeclaration():
                node = self.visitVariableDeclaration(stmt_ctx.variableDeclaration())
            elif stmt_ctx.printStatement():
                node = self.visitPrintStatement(stmt_ctx.printStatement())
            else:
                node = self.visitChildren(stmt_ctx)
            if isinstance(node, Statement):
                statements.append(node)
        return BlockStmt(statements=statements)

    # ---------------- Statements ----------------------

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        params: List[Parameter] = []
        if ctx.parameters():
            for index, param_ctx in enumerate(ctx.parameters().parameter()):
                pname = param_ctx.Identifier().getText()
                params.append(Parameter(name=pname, type="integer"))
        body = self._build_block(ctx.block())
        return FunctionIR(name=name, params=params, return_type="integer", body=body)

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        init_expr = None
        if ctx.initializer():
            init_expr = self._build_expression(ctx.initializer().expression())
        return VarDeclStmt(name=name, var_type="integer", initializer=init_expr)

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr = self._build_expression(ctx.expression())
        return PrintStmt(parts=[expr])

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        value_expr = None
        if ctx.expression():
            value_expr = self._build_expression(ctx.expression())
        return ReturnStmt(value=value_expr)

    # ---------------- Expressions ---------------------

    def _build_expression(self, expr_ctx: CompiscriptParser.ExpressionContext) -> Expression:
        text = expr_ctx.getText()
        return self.expr_builder.build(text)

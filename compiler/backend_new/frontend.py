"""Prototype Compiscript frontend that builds IR nodes for the new backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import os
import sys

from antlr4 import FileStream, CommonTokenStream

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
GRAMMAR_DIR = os.path.join(PROJECT_ROOT, "program", "grammar")
GRAMMAR_GEN_DIR = os.path.join(GRAMMAR_DIR, "gen")
for path in (GRAMMAR_GEN_DIR, GRAMMAR_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from CompiscriptVisitor import CompiscriptVisitor

from .ir_nodes import (
    ProgramIR,
    GlobalVariable,
    FunctionIR,
    Parameter,
    BlockStmt,
    Statement,
    VarDeclStmt,
    ExprStmt,
    PrintStmt,
    Expression,
    IntLiteral,
)


@dataclass
class ParsedProgram:
    ir: ProgramIR


class IRBuilder(CompiscriptVisitor):
    """Minimal IR builder for a subset of Compiscript."""

    def __init__(self) -> None:
        super().__init__()
        self.globals: List[GlobalVariable] = []
        self.functions: List[FunctionIR] = []
        self.main_statements: List[Statement] = []

    # --- entry points ---------------------------------------------------

    def build(self, source_path: str) -> ParsedProgram:
        input_stream = FileStream(source_path, encoding="utf-8")
        lexer = CompiscriptLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        parser = CompiscriptParser(tokens)
        tree = parser.program()
        self.visit(tree)
        main_block = BlockStmt(statements=self.main_statements)
        program = ProgramIR(
            globals=self.globals,
            classes=[],
            functions=self.functions,
            main_block=main_block,
        )
        return ParsedProgram(ir=program)

    # --- visitors -------------------------------------------------------

    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        for stmt_ctx in ctx.statement():
            node = self.visit(stmt_ctx)
            if isinstance(node, GlobalVariable):
                self.globals.append(node)
            elif isinstance(node, FunctionIR):
                self.functions.append(node)
            elif isinstance(node, Statement):
                self.main_statements.append(node)
        return None

    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        expr = IntLiteral(int(ctx.expression().getText()))
        global_var = GlobalVariable(name=name, var_type="integer", mutable=False, initializer=expr)
        return global_var

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        if ctx.expression():
            expr = IntLiteral(int(ctx.expression().getText()))
        else:
            expr = None
        return VarDeclStmt(name=name, var_type="integer", initializer=expr)

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        params: List[Parameter] = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                pname = param_ctx.Identifier().getText()
                params.append(Parameter(name=pname, type="integer"))
        body_block = BlockStmt(statements=[])
        function = FunctionIR(name=name, params=params, return_type="integer", body=body_block)
        return function

    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        expr = self.visit(ctx.expression())
        if isinstance(expr, Expression):
            return ExprStmt(expr=expr)
        return None

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr = IntLiteral(0)
        return PrintStmt(parts=[expr])

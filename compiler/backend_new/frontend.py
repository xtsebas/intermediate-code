"""High level Compiscript frontend that builds the IR tree."""

from __future__ import annotations

import ast as pyast
import os
import re
import sys
from typing import List, Optional

from antlr4 import FileStream, CommonTokenStream

from .ir_nodes import (
    ProgramIR,
    GlobalVariable,
    FunctionIR,
    ClassIR,
    FieldIR,
    MethodIR,
    Parameter,
    BlockStmt,
    VarDeclStmt,
    AssignStmt,
    ExprStmt,
    PrintStmt,
    ReturnStmt,
    BreakStmt,
    ContinueStmt,
    Statement,
    Expression,
    IntLiteral,
    StringLiteral,
    BoolLiteral,
    VarExpr,
    BinaryExpr,
    CallExpr,
    MethodCallExpr,
    ArrayIndexExpr,
    FieldAccessExpr,
    NewObjectExpr,
    IfStmt,
    WhileStmt,
    ForStmt,
    DoWhileStmt,
    ForeachStmt,
    ArrayLiteral,
    ArrayIndexExpr,
    SwitchStmt,
    CaseClause,
    TryCatchStmt,
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
    NEW_CALL_RE = re.compile(r"\bnew\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    def build(self, text: str) -> Expression:
        text = self._transform_new_calls(text)
        node = pyast.parse(text, mode="eval").body
        return self.visit(node)

    def _transform_new_calls(self, text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            class_name = match.group(1)
            return f'__new__("{class_name}",'

        return self.NEW_CALL_RE.sub(repl, text)

    def visit_Name(self, node: pyast.Name) -> Expression:
        return VarExpr(name=node.id)

    def visit_Constant(self, node: pyast.Constant) -> Expression:
        if isinstance(node.value, int):
            return IntLiteral(value=node.value)
        if isinstance(node.value, str):
            return StringLiteral(value=node.value)
        if isinstance(node.value, bool):
            return BoolLiteral(value=node.value)
        raise NotImplementedError(f"Unsupported literal {node.value!r}")

    def visit_Call(self, node: pyast.Call) -> Expression:
        if isinstance(node.func, pyast.Attribute):
            obj = self.visit(node.func.value)
            args = [self.visit(arg) for arg in node.args]
            return MethodCallExpr(obj=obj, method=node.func.attr, args=args)
        if isinstance(node.func, pyast.Name) and node.func.id == "__new__":
            if not node.args:
                raise NotImplementedError("new expressions require class name")
            class_name_expr = self.visit(node.args[0])
            if not isinstance(class_name_expr, StringLiteral):
                raise NotImplementedError("new expressions must include class name literal")
            args = [self.visit(arg) for arg in node.args[1:]]
            return NewObjectExpr(class_name=class_name_expr.value, args=args)
        if not isinstance(node.func, pyast.Name):
            raise NotImplementedError("Unsupported call target")
        callee = node.func.id
        args = [self.visit(arg) for arg in node.args]
        return CallExpr(callee=callee, args=args)

    def visit_BinOp(self, node: pyast.BinOp) -> Expression:
        op_map = {
            pyast.Add: "+",
            pyast.Sub: "-",
            pyast.Mult: "*",
            pyast.Div: "/",
        }
        op_type = type(node.op)
        if op_type not in op_map:
            raise NotImplementedError(f"Unsupported binary op {op_type}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return BinaryExpr(op=op_map[op_type], left=left, right=right)

    def visit_UnaryOp(self, node: pyast.UnaryOp) -> Expression:
        if isinstance(node.op, pyast.USub):
            operand = self.visit(node.operand)
            zero = IntLiteral(value=0)
            return BinaryExpr(op="-", left=zero, right=operand)
        raise NotImplementedError("Unsupported unary op")

    def visit_Compare(self, node: pyast.Compare) -> Expression:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise NotImplementedError("Chained comparisons not supported")
        op_type = type(node.ops[0])
        op_map = {
            pyast.Gt: ">",
            pyast.Lt: "<",
            pyast.GtE: ">=",
            pyast.LtE: "<=",
            pyast.Eq: "==",
            pyast.NotEq: "!=",
        }
        if op_type not in op_map:
            raise NotImplementedError(f"Unsupported comparison {op_type}")
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        return BinaryExpr(op=op_map[op_type], left=left, right=right)

    def visit_List(self, node: pyast.List) -> Expression:
        elements = [self.visit(el) for el in node.elts]
        return ArrayLiteral(elements=elements)

    def visit_Subscript(self, node: pyast.Subscript) -> Expression:
        array_expr = self.visit(node.value)
        index_node = node.slice
        if isinstance(index_node, pyast.Index):  # py38 compatibility
            index_node = index_node.value
        index_expr = self.visit(index_node)
        return ArrayIndexExpr(array_expr=array_expr, index_expr=index_expr)

    def visit_Attribute(self, node: pyast.Attribute) -> Expression:
        obj = self.visit(node.value)
        return FieldAccessExpr(obj=obj, field=node.attr)

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
        classes: List[ClassIR] = []
        main_statements: List[Statement] = []

        stmts = ctx.statement()
        for stmt_ctx in stmts:
            if stmt_ctx.functionDeclaration():
                functions.append(self.visitFunctionDeclaration(stmt_ctx.functionDeclaration()))
                continue
            if stmt_ctx.classDeclaration():
                classes.append(self.visitClassDeclaration(stmt_ctx.classDeclaration()))
                continue
            if stmt_ctx.constantDeclaration():
                globals.append(self._build_global_constant(stmt_ctx.constantDeclaration()))
                continue
            node = self._convert_statement(stmt_ctx)
            if isinstance(node, VarDeclStmt) and isinstance(node.initializer, ArrayLiteral):
                globals.append(
                    GlobalVariable(
                        name=node.name,
                        var_type=node.var_type,
                        mutable=True,
                        initializer=node.initializer,
                    )
                )
                continue
            if isinstance(node, Statement):
                main_statements.append(node)

        main_block = BlockStmt(statements=main_statements)
        return ProgramIR(globals=globals, classes=classes, functions=functions, main_block=main_block)

    def _build_block(self, block_ctx: CompiscriptParser.BlockContext) -> BlockStmt:
        statements: List[Statement] = []
        for stmt_ctx in block_ctx.statement():
            node = self._convert_statement(stmt_ctx)
            if isinstance(node, Statement):
                statements.append(node)
        return BlockStmt(statements=statements)

    def visitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext) -> ClassIR:
        name_tokens = ctx.Identifier()
        name = name_tokens[0].getText()
        base = name_tokens[1].getText() if len(name_tokens) > 1 else None
        fields: List[FieldIR] = []
        methods: List[MethodIR] = []
        for member in ctx.classMember():
            if member.variableDeclaration():
                decl = self.visitVariableDeclaration(member.variableDeclaration())
                fields.append(FieldIR(name=decl.name, field_type=decl.var_type, default_value=decl.initializer))
            elif member.constantDeclaration():
                decl = self.visitConstantDeclaration(member.constantDeclaration())
                fields.append(FieldIR(name=decl.name, field_type=decl.var_type, default_value=decl.initializer))
            elif member.functionDeclaration():
                methods.append(self._build_method_ir(name, member.functionDeclaration()))
        return ClassIR(name=name, base=base, fields=fields, methods=methods)

    def _build_method_ir(self, class_name: str, ctx: CompiscriptParser.FunctionDeclarationContext) -> MethodIR:
        method_name = ctx.Identifier().getText()
        params: List[Parameter] = [Parameter(name="this", type=class_name)]
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                pname = param_ctx.Identifier().getText()
                ptype = "integer"
                if param_ctx.type_():
                    ptype = param_ctx.type_().getText()
                params.append(Parameter(name=pname, type=ptype))
        is_constructor = method_name == "constructor"
        return_type = "void" if is_constructor else self._resolve_return_type(ctx.type_())
        body = self._build_block(ctx.block())
        ir_name = f"{class_name}_{method_name}"
        return MethodIR(
            name=ir_name,
            owner=class_name,
            method_name=method_name,
            params=params,
            return_type=return_type,
            body=body,
            is_constructor=is_constructor,
        )

    def _build_global_constant(self, ctx: CompiscriptParser.ConstantDeclarationContext) -> GlobalVariable:
        name = ctx.Identifier().getText()
        init_expr = self._build_expression(ctx.expression())
        var_type = self._resolve_declared_type(ctx.typeAnnotation(), init_expr)
        return GlobalVariable(name=name, var_type=var_type, mutable=False, initializer=init_expr)

    def _resolve_return_type(self, type_ctx) -> str:
        if type_ctx:
            return type_ctx.getText()
        return "integer"

    def _resolve_declared_type(self, type_ctx, initializer: Optional[Expression]) -> str:
        if type_ctx and type_ctx.type_():
            return type_ctx.type_().getText()
        if isinstance(initializer, StringLiteral):
            return "string"
        if isinstance(initializer, BoolLiteral):
            return "boolean"
        if isinstance(initializer, NewObjectExpr):
            return initializer.class_name
        if isinstance(initializer, ArrayLiteral):
            return "integer[]"
        return "integer"

    # ---------------- Statements ----------------------

    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        params: List[Parameter] = []
        if ctx.parameters():
            for index, param_ctx in enumerate(ctx.parameters().parameter()):
                pname = param_ctx.Identifier().getText()
                ptype = "integer"
                if param_ctx.type_():
                    ptype = param_ctx.type_().getText()
                params.append(Parameter(name=pname, type=ptype))
        body = self._build_block(ctx.block())
        return_type = self._resolve_return_type(ctx.type_())
        return FunctionIR(name=name, params=params, return_type=return_type, body=body)

    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        init_expr = None
        if ctx.initializer():
            init_expr = self._build_expression(ctx.initializer().expression())
        var_type = self._resolve_declared_type(ctx.typeAnnotation(), init_expr)
        return VarDeclStmt(name=name, var_type=var_type, initializer=init_expr)

    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        init_expr = self._build_expression(ctx.expression())
        var_type = self._resolve_declared_type(ctx.typeAnnotation(), init_expr)
        return VarDeclStmt(name=name, var_type=var_type, initializer=init_expr)

    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        if ctx.Identifier() and len(ctx.expression()) == 1:
            name = ctx.Identifier().getText()
            value_expr = self._build_expression(ctx.expression(0))
            return AssignStmt(target=VarExpr(name=name), value=value_expr)
        if len(ctx.expression()) == 2 and ctx.Identifier():
            obj_expr = self._build_expression(ctx.expression(0))
            field_name = ctx.Identifier().getText()
            value_expr = self._build_expression(ctx.expression(1))
            target = FieldAccessExpr(obj=obj_expr, field=field_name)
            return AssignStmt(target=target, value=value_expr)
        raise NotImplementedError("Property assignments not supported yet")

    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        expr = self._build_expression(ctx.expression())
        return ExprStmt(expr=expr)

    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr = self._build_expression(ctx.expression())
        return PrintStmt(parts=[expr])

    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        return BreakStmt()

    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        return ContinueStmt()

    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        condition = self._build_expression(ctx.expression())
        then_block = self._build_block(ctx.block(0))
        else_block = self._build_block(ctx.block(1)) if ctx.block(1) else None
        return IfStmt(condition=condition, then_block=then_block, else_block=else_block)

    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        condition = self._build_expression(ctx.expression())
        body = self._build_block(ctx.block())
        return WhileStmt(condition=condition, body=body)

    def visitDoWhileStatement(self, ctx: CompiscriptParser.DoWhileStatementContext):
        body = self._build_block(ctx.block())
        condition = self._build_expression(ctx.expression())
        return DoWhileStmt(body=body, condition=condition)

    def visitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        init_stmt = None
        if ctx.variableDeclaration():
            init_stmt = self.visitVariableDeclaration(ctx.variableDeclaration())
        elif ctx.assignment():
            init_stmt = self.visitAssignment(ctx.assignment())
        condition_expr = self._build_expression(ctx.expression(0)) if ctx.expression(0) else None
        update_stmt = None
        if ctx.expression(1):
            update_text = ctx.expression(1).getText()
            if "=" in update_text and all(op not in update_text for op in ["==", "<=", ">=", "!="]):
                name, rhs = update_text.split("=", 1)
                update_stmt = AssignStmt(target=VarExpr(name=name.strip()), value=self._build_expression_text(rhs))
            else:
                update_stmt = ExprStmt(expr=self._build_expression(ctx.expression(1)))
        body = self._build_block(ctx.block())
        return ForStmt(init=init_stmt, condition=condition_expr, update=update_stmt, body=body)

    def visitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        iterator = ctx.Identifier().getText()
        iterable = self._build_expression(ctx.expression())
        body = self._build_block(ctx.block())
        return ForeachStmt(iterator=iterator, iterable=iterable, body=body)

    def visitTryCatchStatement(self, ctx: CompiscriptParser.TryCatchStatementContext):
        try_block = self._build_block(ctx.block(0))
        catch_var = ctx.Identifier().getText()
        catch_block = self._build_block(ctx.block(1))
        return TryCatchStmt(try_block=try_block, catch_var=catch_var, catch_block=catch_block)

    def visitSwitchStatement(self, ctx: CompiscriptParser.SwitchStatementContext):
        expression = self._build_expression(ctx.expression())
        cases: List[CaseClause] = []
        for case_ctx in ctx.switchCase():
            value = self._build_expression(case_ctx.expression())
            body_statements: List[Statement] = []
            for stmt_ctx in case_ctx.statement():
                stmt = self._convert_statement(stmt_ctx)
                if isinstance(stmt, Statement):
                    body_statements.append(stmt)
            body = BlockStmt(statements=body_statements)
            cases.append(CaseClause(value=value, body=body))
        if ctx.defaultCase():
            default_statements: List[Statement] = []
            for stmt_ctx in ctx.defaultCase().statement():
                stmt = self._convert_statement(stmt_ctx)
                if isinstance(stmt, Statement):
                    default_statements.append(stmt)
            default_body = BlockStmt(statements=default_statements)
            cases.append(CaseClause(value=None, body=default_body))
        return SwitchStmt(expression=expression, cases=cases)

    def _convert_statement(self, stmt_ctx) -> Optional[Statement]:
        if stmt_ctx.returnStatement():
            return self.visitReturnStatement(stmt_ctx.returnStatement())
        if stmt_ctx.assignment():
            return self.visitAssignment(stmt_ctx.assignment())
        if stmt_ctx.expressionStatement():
            return self.visitExpressionStatement(stmt_ctx.expressionStatement())
        if stmt_ctx.whileStatement():
            return self.visitWhileStatement(stmt_ctx.whileStatement())
        if stmt_ctx.doWhileStatement():
            return self.visitDoWhileStatement(stmt_ctx.doWhileStatement())
        if stmt_ctx.forStatement():
            return self.visitForStatement(stmt_ctx.forStatement())
        if stmt_ctx.foreachStatement():
            return self.visitForeachStatement(stmt_ctx.foreachStatement())
        if stmt_ctx.tryCatchStatement():
            return self.visitTryCatchStatement(stmt_ctx.tryCatchStatement())
        if stmt_ctx.switchStatement():
            return self.visitSwitchStatement(stmt_ctx.switchStatement())
        if stmt_ctx.ifStatement():
            return self.visitIfStatement(stmt_ctx.ifStatement())
        if stmt_ctx.classDeclaration():
            return None
        if stmt_ctx.breakStatement():
            return self.visitBreakStatement(stmt_ctx.breakStatement())
        if stmt_ctx.continueStatement():
            return self.visitContinueStatement(stmt_ctx.continueStatement())
        if stmt_ctx.constantDeclaration():
            return self.visitConstantDeclaration(stmt_ctx.constantDeclaration())
        if stmt_ctx.variableDeclaration():
            return self.visitVariableDeclaration(stmt_ctx.variableDeclaration())
        if stmt_ctx.printStatement():
            return self.visitPrintStatement(stmt_ctx.printStatement())
        return self.visitChildren(stmt_ctx)

    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        value_expr = None
        if ctx.expression():
            value_expr = self._build_expression(ctx.expression())
        return ReturnStmt(value=value_expr)

    # ---------------- Expressions ---------------------

    def _build_expression(self, expr_ctx: CompiscriptParser.ExpressionContext) -> Expression:
        text = expr_ctx.getText()
        return self._build_expression_text(text)

    def _build_expression_text(self, text: str) -> Expression:
        if text == "true":
            return BoolLiteral(value=True)
        if text == "false":
            return BoolLiteral(value=False)
        if text == "this":
            return VarExpr(name="this")
        return self.expr_builder.build(text)

"""High level IR node definitions for the revamped Compiscript backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union, Sequence


# ---------------------------- Expressions -----------------------------------


class Expression:
    """Base class for AST expressions used by the backend."""


@dataclass
class IntLiteral(Expression):
    value: int


@dataclass
class StringLiteral(Expression):
    value: str


@dataclass
class BoolLiteral(Expression):
    value: bool


@dataclass
class NullLiteral(Expression):
    pass


@dataclass
class VarExpr(Expression):
    name: str


@dataclass
class BinaryExpr(Expression):
    op: str
    left: Expression
    right: Expression


@dataclass
class UnaryExpr(Expression):
    op: str
    operand: Expression


@dataclass
class CallExpr(Expression):
    callee: str
    args: List[Expression]


@dataclass
class MethodCallExpr(Expression):
    obj: Expression
    method: str
    args: List[Expression]


@dataclass
class ArrayLiteral(Expression):
    elements: List[Expression]


@dataclass
class MatrixLiteral(Expression):
    rows: List[ArrayLiteral]


@dataclass
class ArrayIndexExpr(Expression):
    array_expr: Expression
    index_expr: Expression


@dataclass
class FieldAccessExpr(Expression):
    obj: Expression
    field: str


@dataclass
class NewObjectExpr(Expression):
    class_name: str
    args: List[Expression]


# ---------------------------- Statements -------------------------------------


class Statement:
    """Base statement type."""


@dataclass
class BlockStmt(Statement):
    statements: List[Statement]


@dataclass
class VarDeclStmt(Statement):
    name: str
    var_type: str
    initializer: Optional[Expression] = None


@dataclass
class AssignStmt(Statement):
    target: Union[VarExpr, FieldAccessExpr, ArrayIndexExpr]
    value: Expression


@dataclass
class ExprStmt(Statement):
    expr: Expression


@dataclass
class PrintStmt(Statement):
    parts: List[Expression]


@dataclass
class IfStmt(Statement):
    condition: Expression
    then_block: BlockStmt
    else_block: Optional[BlockStmt] = None


@dataclass
class WhileStmt(Statement):
    condition: Expression
    body: BlockStmt


@dataclass
class DoWhileStmt(Statement):
    body: BlockStmt
    condition: Expression


@dataclass
class ForStmt(Statement):
    init: Statement
    condition: Expression
    update: Statement
    body: BlockStmt


@dataclass
class ForeachStmt(Statement):
    iterator: str
    iterable: Expression
    body: BlockStmt


@dataclass
class CaseClause:
    value: Optional[int]
    body: BlockStmt


@dataclass
class SwitchStmt(Statement):
    expression: Expression
    cases: List[CaseClause]


@dataclass
class TryCatchStmt(Statement):
    try_block: BlockStmt
    catch_var: str
    catch_block: BlockStmt


@dataclass
class ReturnStmt(Statement):
    value: Optional[Expression]


@dataclass
class BreakStmt(Statement):
    pass


@dataclass
class ContinueStmt(Statement):
    pass


# ---------------------------- Functions & Classes ----------------------------


@dataclass
class Parameter:
    name: str
    type: str


@dataclass
class FunctionIR:
    name: str
    params: List[Parameter]
    return_type: str
    body: BlockStmt


@dataclass
class MethodIR(FunctionIR):
    is_constructor: bool = False


@dataclass
class FieldIR:
    name: str
    field_type: str
    default_value: Optional[Expression] = None


@dataclass
class ClassIR:
    name: str
    base: Optional[str]
    fields: List[FieldIR]
    methods: List[MethodIR]


@dataclass
class GlobalVariable:
    name: str
    var_type: str
    mutable: bool
    initializer: Optional[Expression]


@dataclass
class ProgramIR:
    globals: List[GlobalVariable]
    classes: List[ClassIR]
    functions: List[FunctionIR]
    main_block: BlockStmt

    def all_strings(self) -> List[str]:
        """Collects all string literals to preallocate in the data section."""

        collector: List[str] = []

        def visit_expr(expr: Expression):
            if isinstance(expr, StringLiteral):
                collector.append(expr.value)
            elif isinstance(expr, ArrayLiteral):
                for sub in expr.elements:
                    visit_expr(sub)
            elif isinstance(expr, MatrixLiteral):
                for row in expr.rows:
                    visit_expr(row)
            elif isinstance(expr, BinaryExpr):
                visit_expr(expr.left)
                visit_expr(expr.right)
            elif isinstance(expr, UnaryExpr):
                visit_expr(expr.operand)
            elif isinstance(expr, CallExpr):
                for a in expr.args:
                    visit_expr(a)
            elif isinstance(expr, MethodCallExpr):
                visit_expr(expr.obj)
                for a in expr.args:
                    visit_expr(a)
            elif isinstance(expr, ArrayIndexExpr):
                visit_expr(expr.array_expr)
                visit_expr(expr.index_expr)
            elif isinstance(expr, FieldAccessExpr):
                visit_expr(expr.obj)
            elif isinstance(expr, NewObjectExpr):
                for a in expr.args:
                    visit_expr(a)

        def visit_stmt(stmt: Statement):
            if isinstance(stmt, BlockStmt):
                for sub in stmt.statements:
                    visit_stmt(sub)
            elif isinstance(stmt, VarDeclStmt):
                if stmt.initializer:
                    visit_expr(stmt.initializer)
            elif isinstance(stmt, AssignStmt):
                visit_expr(stmt.value)
            elif isinstance(stmt, ExprStmt):
                visit_expr(stmt.expr)
            elif isinstance(stmt, PrintStmt):
                for p in stmt.parts:
                    visit_expr(p)
            elif isinstance(stmt, IfStmt):
                visit_expr(stmt.condition)
                visit_stmt(stmt.then_block)
                if stmt.else_block:
                    visit_stmt(stmt.else_block)
            elif isinstance(stmt, WhileStmt):
                visit_expr(stmt.condition)
                visit_stmt(stmt.body)
            elif isinstance(stmt, DoWhileStmt):
                visit_stmt(stmt.body)
                visit_expr(stmt.condition)
            elif isinstance(stmt, ForStmt):
                visit_stmt(stmt.init)
                visit_expr(stmt.condition)
                visit_stmt(stmt.update)
                visit_stmt(stmt.body)
            elif isinstance(stmt, ForeachStmt):
                visit_expr(stmt.iterable)
                visit_stmt(stmt.body)
            elif isinstance(stmt, SwitchStmt):
                visit_expr(stmt.expression)
                for case in stmt.cases:
                    visit_stmt(case.body)
            elif isinstance(stmt, TryCatchStmt):
                visit_stmt(stmt.try_block)
                visit_stmt(stmt.catch_block)
            elif isinstance(stmt, ReturnStmt):
                if stmt.value:
                    visit_expr(stmt.value)

        for glob in self.globals:
            if glob.initializer:
                visit_expr(glob.initializer)

        for cls in self.classes:
            for fld in cls.fields:
                if fld.default_value:
                    visit_expr(fld.default_value)
            for m in cls.methods:
                visit_stmt(m.body)

        for fn in self.functions:
            visit_stmt(fn.body)

        visit_stmt(self.main_block)
        return collector

"""Lowers ProgramIR into TAC using TACGenerator (limited subset)."""

from __future__ import annotations

from typing import Dict, List

from .ir_nodes import (
    ProgramIR,
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
from .tac import TACInstruction, TACOp, TACProgram
from .tac_generator import TACGenerator


def lower_program(ir: ProgramIR) -> TACProgram:
    gen = TACGenerator()
    string_labels: Dict[str, str] = {}
    for text in ir.all_strings():
        label = gen.declare_string(text)
        string_labels[text] = label

    lowerer = _IRToTACLower(gen, string_labels)

    for function in ir.functions:
        gen.start_function(function.name)
        for index, param in enumerate(function.params):
            gen.frame.ensure(param.name)
            gen.emit(TACInstruction(op=TACOp.PARAM, dest=param.name, arg1=index))
        lowerer.lower_block(function.body)
        gen.commit_function()

    # main function from top-level statements
    gen.start_function("main")
    lowerer.lower_block(ir.main_block)
    gen.call(None, "exit_program", [])
    gen.commit_function()

    return gen.program


class _IRToTACLower:
    def __init__(self, gen: TACGenerator, strings: Dict[str, str]) -> None:
        self.gen = gen
        self.string_labels = strings

    def lower_block(self, block: BlockStmt) -> None:
        for stmt in block.statements:
            self.lower_statement(stmt)

    def lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, VarDeclStmt):
            if stmt.initializer is None:
                return
            operand = self.eval_expr(stmt.initializer)
            self._store_operand(stmt.name, operand)
        elif isinstance(stmt, PrintStmt):
            for part in self._flatten_print(stmt.parts[0]):
                if isinstance(part, StringLiteral):
                    label = self.string_labels[part.value]
                    self.gen.call(None, "print_string", [label])
                else:
                    operand = self.eval_expr(part)
                    self.gen.call(None, "print_int", [operand])
            self.gen.call(None, "print_newline", [])
        elif isinstance(stmt, ReturnStmt):
            value = None
            if stmt.value is not None:
                value = self.eval_expr(stmt.value)
            self.gen.ret(value)

    def _store_operand(self, name: str, operand):
        if isinstance(operand, int):
            self.gen.assign_const(name, operand)
        elif isinstance(operand, str):
            self.gen.copy(name, operand)
        else:
            raise TypeError("Unsupported operand type")

    def eval_expr(self, expr: Expression):
        if isinstance(expr, IntLiteral):
            return expr.value
        if isinstance(expr, VarExpr):
            return expr.name
        if isinstance(expr, BinaryExpr):
            if expr.op != "+":
                raise NotImplementedError("Only addition is supported")
            left = self.eval_expr(expr.left)
            right = self.eval_expr(expr.right)
            dest = self.gen.new_temp()
            self.gen.binary(TACOp.ADD, dest, left, right)
            return dest
        if isinstance(expr, CallExpr):
            dest = self.gen.new_temp()
            args = [self.eval_expr(arg) for arg in expr.args]
            self.gen.call(dest, expr.callee, args)
            return dest
        if isinstance(expr, StringLiteral):
            return self.string_labels[expr.value]
        raise NotImplementedError(f"Unsupported expression: {expr}")

    def _flatten_print(self, expr: Expression) -> List[Expression]:
        if isinstance(expr, BinaryExpr) and expr.op == "+":
            return self._flatten_print(expr.left) + self._flatten_print(expr.right)
        return [expr]

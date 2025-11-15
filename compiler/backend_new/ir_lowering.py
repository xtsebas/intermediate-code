"""Lowers ProgramIR into TAC using TACGenerator (limited subset)."""

from __future__ import annotations

from typing import Dict, List

from .ir_nodes import (
    ProgramIR,
    BlockStmt,
    VarDeclStmt,
    AssignStmt,
    ExprStmt,
    PrintStmt,
    ReturnStmt,
    IfStmt,
    WhileStmt,
    DoWhileStmt,
    ForStmt,
    ForeachStmt,
    Statement,
    Expression,
    IntLiteral,
    StringLiteral,
    BoolLiteral,
    VarExpr,
    BinaryExpr,
    CallExpr,
    ArrayLiteral,
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
        self.label_counter = 0
        self.literal_arrays: Dict[str, List[int]] = {}

    def lower_block(self, block: BlockStmt) -> None:
        for stmt in block.statements:
            self.lower_statement(stmt)

    def lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, VarDeclStmt):
            if stmt.initializer is None:
                return
            if isinstance(stmt.initializer, ArrayLiteral):
                values = self._literal_array_values(stmt.initializer)
                self.literal_arrays[stmt.name] = values
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
        elif isinstance(stmt, IfStmt):
            self._lower_if(stmt)
        elif isinstance(stmt, AssignStmt):
            value = self.eval_expr(stmt.value)
            if isinstance(stmt.target, VarExpr):
                self._store_operand(stmt.target.name, value)
            else:
                raise NotImplementedError("Only simple variable assignment supported")
        elif isinstance(stmt, ExprStmt):
            self.eval_expr(stmt.expr)
        elif isinstance(stmt, WhileStmt):
            self._lower_while(stmt)
        elif isinstance(stmt, DoWhileStmt):
            self._lower_do_while(stmt)
        elif isinstance(stmt, ForStmt):
            self._lower_for(stmt)
        elif isinstance(stmt, ForeachStmt):
            self._lower_foreach(stmt)

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
        if isinstance(expr, BoolLiteral):
            return 1 if expr.value else 0
        if isinstance(expr, VarExpr):
            return expr.name
        if isinstance(expr, BinaryExpr):
            arith_map = {
                "+": TACOp.ADD,
                "-": TACOp.SUB,
                "*": TACOp.MUL,
                "/": TACOp.DIV,
            }
            comp_map = {
                "<": TACOp.LT,
                "<=": TACOp.LE,
                ">": TACOp.GT,
                ">=": TACOp.GE,
                "==": TACOp.EQ,
                "!=": TACOp.NE,
            }
            if expr.op in arith_map:
                left = self.eval_expr(expr.left)
                right = self.eval_expr(expr.right)
                dest = self.gen.new_temp()
                self.gen.binary(arith_map[expr.op], dest, left, right)
                return dest
            if expr.op in comp_map:
                left = self.eval_expr(expr.left)
                right = self.eval_expr(expr.right)
                dest = self.gen.new_temp()
                self.gen.binary(comp_map[expr.op], dest, left, right)
                return dest
            raise NotImplementedError(f"Unsupported binary op {expr.op}")
        if isinstance(expr, CallExpr):
            dest = self.gen.new_temp()
            args = [self.eval_expr(arg) for arg in expr.args]
            self.gen.call(dest, expr.callee, args)
            return dest
        if isinstance(expr, StringLiteral):
            return self.string_labels[expr.value]
        if isinstance(expr, ArrayLiteral):
            raise NotImplementedError("Array literals are only supported in variable declarations currently")
        raise NotImplementedError(f"Unsupported expression: {expr}")

    def _flatten_print(self, expr: Expression) -> List[Expression]:
        if isinstance(expr, BinaryExpr) and expr.op == "+":
            return self._flatten_print(expr.left) + self._flatten_print(expr.right)
        return [expr]

    def _lower_if(self, stmt: IfStmt) -> None:
        true_label = self._new_label("if_true")
        false_label = self._new_label("if_false")
        end_label = self._new_label("if_end")
        cond = self.eval_expr(stmt.condition)
        target_false = false_label if stmt.else_block else end_label
        self.gen.cjump(cond, true_label)
        self.gen.jump(target_false)
        self.gen.label(true_label)
        self.lower_block(stmt.then_block)
        self.gen.jump(end_label)
        if stmt.else_block:
            self.gen.label(false_label)
            self.lower_block(stmt.else_block)
        self.gen.label(end_label)

    def _lower_while(self, stmt: WhileStmt) -> None:
        start_label = self._new_label("while_start")
        body_label = self._new_label("while_body")
        end_label = self._new_label("while_end")
        self.gen.label(start_label)
        cond = self.eval_expr(stmt.condition)
        self.gen.cjump(cond, body_label)
        self.gen.jump(end_label)
        self.gen.label(body_label)
        self.lower_block(stmt.body)
        self.gen.jump(start_label)
        self.gen.label(end_label)

    def _new_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def _lower_do_while(self, stmt: DoWhileStmt) -> None:
        body_label = self._new_label("do_body")
        self.gen.label(body_label)
        self.lower_block(stmt.body)
        cond = self.eval_expr(stmt.condition)
        self.gen.cjump(cond, body_label)

    def _lower_for(self, stmt: ForStmt) -> None:
        if stmt.init:
            self.lower_statement(stmt.init)
        start_label = self._new_label("for_start")
        body_label = self._new_label("for_body")
        end_label = self._new_label("for_end")
        self.gen.label(start_label)
        if stmt.condition:
            cond = self.eval_expr(stmt.condition)
            self.gen.cjump(cond, body_label)
            self.gen.jump(end_label)
        else:
            self.gen.jump(body_label)
        self.gen.label(body_label)
        self.lower_block(stmt.body)
        if stmt.update:
            self.lower_statement(stmt.update)
        self.gen.jump(start_label)
        self.gen.label(end_label)

    def _lower_foreach(self, stmt: ForeachStmt) -> None:
        if isinstance(stmt.iterable, VarExpr):
            values = self.literal_arrays.get(stmt.iterable.name)
            if values is None:
                raise NotImplementedError("Foreach currently supports literal array variables only")
            for value in values:
                self._store_operand(stmt.iterator, value)
                self.lower_block(stmt.body)
        else:
            raise NotImplementedError("Foreach iterable not supported")

    def _literal_array_values(self, array_expr: ArrayLiteral) -> List[int]:
        values: List[int] = []
        for element in array_expr.elements:
            if isinstance(element, IntLiteral):
                values.append(element.value)
            else:
                raise NotImplementedError("Array literals support only integer elements for now")
        return values

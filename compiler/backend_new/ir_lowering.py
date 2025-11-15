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
    TryCatchStmt,
    SwitchStmt,
    CaseClause,
    Statement,
    Expression,
    IntLiteral,
    StringLiteral,
    BoolLiteral,
    VarExpr,
    BinaryExpr,
    CallExpr,
    ArrayLiteral,
    ArrayIndexExpr,
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
        self.array_labels: Dict[str, str] = {}
        self.array_label_lengths: Dict[str, int] = {}
        self.try_stack: List[dict] = []

    def lower_block(self, block: BlockStmt) -> None:
        for stmt in block.statements:
            self.lower_statement(stmt)

    def lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, VarDeclStmt):
            if stmt.initializer is None:
                return
            if isinstance(stmt.initializer, ArrayLiteral):
                values = self._literal_array_values(stmt.initializer)
                label = stmt.name
                self.gen.declare_array(label, values)
                self.literal_arrays[stmt.name] = values
                self.array_labels[stmt.name] = label
                self.array_label_lengths[label] = len(values)
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
                    if isinstance(operand, str) and operand in self.string_labels.values():
                        self.gen.call(None, "print_string", [operand])
                    else:
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
        elif isinstance(stmt, TryCatchStmt):
            self._lower_try_catch(stmt)
        elif isinstance(stmt, SwitchStmt):
            self._lower_switch(stmt)

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
            if expr.name in self.array_labels:
                return self.array_labels[expr.name]
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
        if isinstance(expr, ArrayIndexExpr):
            base = self.eval_expr(expr.array_expr)
            index = self.eval_expr(expr.index_expr)
            length = None
            if isinstance(base, str):
                length = self.array_label_lengths.get(base)
                if length is None and base in self.array_labels.values():
                    length = self.array_label_lengths.get(base)
            if self.try_stack and length is not None:
                self._emit_bounds_check(index, length)
            dest = self.gen.new_temp()
            self.gen.array_get(dest, base, index)
            return dest
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
    def _emit_bounds_check(self, index_operand, length: int) -> None:
        context = self.try_stack[-1]
        upper_ok = self._new_label("bounds_upper_ok")
        lower_ok = self._new_label("bounds_lower_ok")
        temp = self.gen.new_temp()
        self.gen.binary(TACOp.LT, temp, index_operand, length)
        self.gen.cjump(temp, upper_ok)
        self._jump_to_catch(context["error_label"])
        self.gen.label(upper_ok)
        temp2 = self.gen.new_temp()
        self.gen.binary(TACOp.GE, temp2, index_operand, 0)
        self.gen.cjump(temp2, lower_ok)
        self._jump_to_catch(context["error_label"])
        self.gen.label(lower_ok)

    def _jump_to_catch(self, error_label: str) -> None:
        context = self.try_stack[-1]
        self._store_operand(context["catch_var"], error_label)
        self.gen.jump(context["catch_label"])

    def _lower_try_catch(self, stmt: TryCatchStmt) -> None:
        try_label = self._new_label("try_block")
        catch_label = self._new_label("catch_block")
        end_label = self._new_label("try_end")
        error_label = self.string_labels.get("Index out of range")
        if error_label is None:
            error_label = self.gen.declare_string("Index out of range")
            self.string_labels["Index out of range"] = error_label
        context = {
            "catch_label": catch_label,
            "catch_var": stmt.catch_var,
            "error_label": error_label,
        }
        self.try_stack.append(context)
        self.gen.label(try_label)
        self.lower_block(stmt.try_block)
        self.try_stack.pop()
        self.gen.jump(end_label)
        self.gen.label(catch_label)
        self.lower_block(stmt.catch_block)
        self.gen.label(end_label)

    def _lower_switch(self, stmt: SwitchStmt) -> None:
        end_label = self._new_label("switch_end")
        expression_temp = self.eval_expr(stmt.expression)
        case_labels: List[tuple[str, BlockStmt]] = []
        default_case = None
        for case in stmt.cases:
            if case.value is None:
                default_case = case
                continue
            case_label = self._new_label("switch_case")
            case_labels.append((case_label, case.body))
            case_value = self.eval_expr(case.value)
            temp = self.gen.new_temp()
            self.gen.binary(TACOp.EQ, temp, expression_temp, case_value)
            self.gen.cjump(temp, case_label)
        if default_case:
            default_label = self._new_label("switch_default")
            self.gen.jump(default_label)
        else:
            self.gen.jump(end_label)
        for case_label, body in case_labels:
            self.gen.label(case_label)
            self.lower_block(body)
            self.gen.jump(end_label)
        if default_case:
            self.gen.label(default_label)
            self.lower_block(default_case.body)
            self.gen.jump(end_label)
        self.gen.label(end_label)

    def _literal_array_values(self, array_expr: ArrayLiteral) -> List[int]:
        values: List[int] = []
        for element in array_expr.elements:
            if isinstance(element, IntLiteral):
                values.append(element.value)
            else:
                raise NotImplementedError("Array literals support only integer elements for now")
        return values

"""Lowers ProgramIR into TAC using TACGenerator (limited subset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .ir_nodes import (
    ProgramIR,
    GlobalVariable,
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


@dataclass
class ArrayInfo:
    base: str
    length: int
    dimensions: List[int]

    def stride(self, dim_index: int) -> int:
        stride = 1
        for size in self.dimensions[dim_index + 1 :]:
            stride *= size
        return stride


@dataclass
class ArraySignature:
    length: int
    dimensions: List[int]


def lower_program(ir: ProgramIR) -> TACProgram:
    gen = TACGenerator()
    string_labels: Dict[str, str] = {}
    for text in ir.all_strings():
        label = gen.declare_string(text)
        string_labels[text] = label

    lowerer = _IRToTACLower(gen, string_labels)
    lowerer.register_global_arrays(ir.globals)

    for function in ir.functions:
        gen.start_function(function.name)
        lowerer.enter_function(function.name)
        for index, param in enumerate(function.params):
            gen.frame.ensure(param.name)
            gen.emit(TACInstruction(op=TACOp.PARAM, dest=param.name, arg1=index))
        lowerer.lower_block(function.body)
        lowerer.leave_function()
        gen.commit_function()

    # main function from top-level statements
    gen.start_function("main")
    lowerer.enter_function("main")
    lowerer.lower_block(ir.main_block)
    lowerer.leave_function()
    gen.call(None, "exit_program", [])
    gen.commit_function()

    return gen.program


class _IRToTACLower:
    def __init__(self, gen: TACGenerator, strings: Dict[str, str]) -> None:
        self.gen = gen
        self.string_labels = strings
        self.label_counter = 0
        self.global_array_infos: Dict[str, ArrayInfo] = {}
        self.array_infos: Dict[str, ArrayInfo] = {}
        self.function_return_signatures: Dict[str, ArraySignature] = {}
        self.current_function: Optional[str] = None
        self.try_stack: List[dict] = []

    def register_global_arrays(self, globals_list: List[GlobalVariable]) -> None:
        for glob in globals_list:
            initializer = glob.initializer
            if not isinstance(initializer, ArrayLiteral):
                continue
            flat_exprs, dimensions = self._flatten_array_literal(initializer)
            values = self._static_int_values(flat_exprs)
            base_label = glob.name
            self.gen.declare_array(base_label, values)
            info = self._create_array_info(base_label, dimensions)
            self.global_array_infos[base_label] = info
        self.array_infos = dict(self.global_array_infos)

    def enter_function(self, name: str) -> None:
        self.current_function = name
        # Start each function with the global array metadata in scope
        self.array_infos = dict(self.global_array_infos)

    def leave_function(self) -> None:
        self.current_function = None
        self.array_infos = dict(self.global_array_infos)

    def lower_block(self, block: BlockStmt) -> None:
        for stmt in block.statements:
            self.lower_statement(stmt)

    def lower_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, VarDeclStmt):
            if stmt.initializer is None:
                return
            if isinstance(stmt.initializer, ArrayLiteral):
                self._lower_array_declaration(stmt.name, stmt.initializer)
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
            if value is not None:
                self._note_function_array_return(value)
        elif isinstance(stmt, IfStmt):
            self._lower_if(stmt)
        elif isinstance(stmt, AssignStmt):
            value = self.eval_expr(stmt.value)
            if isinstance(stmt.target, VarExpr):
                self._store_operand(stmt.target.name, value)
            elif isinstance(stmt.target, ArrayIndexExpr):
                self._lower_array_assignment(stmt.target, value)
            else:
                raise NotImplementedError("Assignment target not supported")
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
            self._clone_array_info(operand, name)
        else:
            raise TypeError("Unsupported operand type")

    def eval_expr(self, expr: Expression):
        if isinstance(expr, IntLiteral):
            return expr.value
        if isinstance(expr, BoolLiteral):
            return 1 if expr.value else 0
        if isinstance(expr, VarExpr):
            info = self.array_infos.get(expr.name)
            if info:
                return info.base
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
            signature = self.function_return_signatures.get(expr.callee)
            if signature:
                self._register_array_from_signature(dest, signature)
            return dest
        if isinstance(expr, StringLiteral):
            return self.string_labels[expr.value]
        if isinstance(expr, ArrayIndexExpr):
            base_expr, index_exprs = self._unwrap_array_access(expr)
            base_operand = self.eval_expr(base_expr)
            info = self.array_infos.get(base_operand)
            if not info:
                raise NotImplementedError("Array access requires known array metadata")
            if len(index_exprs) != len(info.dimensions):
                raise NotImplementedError("Partial array indexing not supported yet")
            index_operands = [self.eval_expr(sub) for sub in index_exprs]
            if self.try_stack:
                for operand, limit in zip(index_operands, info.dimensions):
                    self._emit_bounds_check(operand, limit)
            linear_index = self._linearize_indices(index_operands, info.dimensions)
            dest = self.gen.new_temp()
            self.gen.array_get(dest, base_operand, linear_index)
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
        iterable_operand = self.eval_expr(stmt.iterable)
        info = self.array_infos.get(iterable_operand)
        if not info:
            raise NotImplementedError("Foreach requires iterable array metadata")
        index_temp = self.gen.new_temp()
        self.gen.assign_const(index_temp, 0)
        start_label = self._new_label("foreach_start")
        body_label = self._new_label("foreach_body")
        end_label = self._new_label("foreach_end")
        self.gen.label(start_label)
        cond_temp = self.gen.new_temp()
        self.gen.binary(TACOp.LT, cond_temp, index_temp, info.length)
        self.gen.cjump(cond_temp, body_label)
        self.gen.jump(end_label)
        self.gen.label(body_label)
        value_temp = self.gen.new_temp()
        self.gen.array_get(value_temp, iterable_operand, index_temp)
        self._store_operand(stmt.iterator, value_temp)
        self.lower_block(stmt.body)
        self.gen.binary(TACOp.ADD, index_temp, index_temp, 1)
        self.gen.jump(start_label)
        self.gen.label(end_label)

    def _lower_array_declaration(self, name: str, literal: ArrayLiteral) -> None:
        flat_exprs, dimensions = self._flatten_array_literal(literal)
        total_elements = len(flat_exprs)
        size_bytes = total_elements * 4
        pointer = self.gen.new_temp()
        self.gen.heap_alloc(pointer, size_bytes)
        self._store_operand(name, pointer)
        self._register_array_info(name, dimensions)
        for index, element_expr in enumerate(flat_exprs):
            value = self.eval_expr(element_expr)
            self.gen.array_set(name, index, value)

    def _lower_array_assignment(self, target: ArrayIndexExpr, value_operand) -> None:
        base_expr, index_exprs = self._unwrap_array_access(target)
        base_operand = self.eval_expr(base_expr)
        info = self.array_infos.get(base_operand)
        if not info:
            raise NotImplementedError("Array assignment requires known array metadata")
        if len(index_exprs) != len(info.dimensions):
            raise NotImplementedError("Partial array assignment not supported")
        index_operands = [self.eval_expr(expr) for expr in index_exprs]
        if self.try_stack:
            for operand, limit in zip(index_operands, info.dimensions):
                self._emit_bounds_check(operand, limit)
        linear_index = self._linearize_indices(index_operands, info.dimensions)
        self.gen.array_set(base_operand, linear_index, value_operand)

    def _unwrap_array_access(self, expr: ArrayIndexExpr) -> Tuple[Expression, List[Expression]]:
        indices: List[Expression] = []
        current: Expression = expr
        while isinstance(current, ArrayIndexExpr):
            indices.insert(0, current.index_expr)
            current = current.array_expr
        return current, indices

    def _linearize_indices(self, operands: List, dimensions: Sequence[int]):
        if not operands:
            return 0
        accumulator = None
        for dim_index, operand in enumerate(operands):
            stride = 1
            for size in dimensions[dim_index + 1 :]:
                stride *= size
            term = operand
            if stride != 1:
                term = self._multiply_operand(term, stride)
            if accumulator is None:
                accumulator = term
            else:
                accumulator = self._add_operands(accumulator, term)
        return accumulator if accumulator is not None else 0

    def _multiply_operand(self, operand, factor: int):
        if isinstance(operand, int):
            return operand * factor
        temp = self.gen.new_temp()
        self.gen.binary(TACOp.MUL, temp, operand, factor)
        return temp

    def _add_operands(self, left, right):
        if isinstance(left, int) and isinstance(right, int):
            return left + right
        if isinstance(left, int):
            temp_left = self.gen.new_temp()
            self.gen.assign_const(temp_left, left)
            left = temp_left
        if isinstance(right, int):
            temp_right = self.gen.new_temp()
            self.gen.assign_const(temp_right, right)
            right = temp_right
        temp = self.gen.new_temp()
        self.gen.binary(TACOp.ADD, temp, left, right)
        return temp

    def _register_array_info(self, base: str, dimensions: Sequence[int]) -> None:
        info = self._create_array_info(base, dimensions)
        self.array_infos[base] = info

    def _create_array_info(self, base: str, dimensions: Sequence[int]) -> ArrayInfo:
        dims = list(dimensions) if dimensions else []
        if not dims:
            dims = [0]
        length = 1
        for size in dims:
            length *= size
        return ArrayInfo(base=base, length=length, dimensions=dims)

    def _clone_array_info(self, source_base: str, target_base: str) -> None:
        info = self.array_infos.get(source_base)
        if not info:
            return
        clone = ArrayInfo(base=target_base, length=info.length, dimensions=list(info.dimensions))
        self.array_infos[target_base] = clone

    def _register_array_from_signature(self, base: str, signature: ArraySignature) -> None:
        info = ArrayInfo(base=base, length=signature.length, dimensions=list(signature.dimensions))
        self.array_infos[base] = info

    def _note_function_array_return(self, operand) -> None:
        if not self.current_function or self.current_function == "main":
            return
        if not isinstance(operand, str):
            return
        info = self.array_infos.get(operand)
        if not info:
            return
        existing = self.function_return_signatures.get(self.current_function)
        if existing:
            if existing.dimensions != info.dimensions:
                raise NotImplementedError("Functions returning arrays with inconsistent shapes")
            return
        self.function_return_signatures[self.current_function] = ArraySignature(
            length=info.length, dimensions=list(info.dimensions)
        )

    def _flatten_array_literal(self, literal: ArrayLiteral) -> Tuple[List[Expression], List[int]]:
        flat: List[Expression] = []
        dimensions: List[int] = []

        def visit(node: ArrayLiteral, depth: int) -> None:
            length = len(node.elements)
            if len(dimensions) <= depth:
                dimensions.append(length)
            elif dimensions[depth] != length:
                raise NotImplementedError("Jagged array literals are not supported")
            if not node.elements:
                return
            if all(isinstance(element, ArrayLiteral) for element in node.elements):
                for sub in node.elements:
                    visit(sub, depth + 1)
            else:
                for element in node.elements:
                    if isinstance(element, ArrayLiteral):
                        raise NotImplementedError("Mixed literal dimensions not supported")
                    flat.append(element)

        visit(literal, 0)
        if not dimensions:
            dimensions = [0]
        return flat, dimensions

    def _static_int_values(self, elements: Sequence[Expression]) -> List[int]:
        values: List[int] = []
        for expr in elements:
            if isinstance(expr, IntLiteral):
                values.append(expr.value)
            else:
                raise NotImplementedError("Global arrays support only integer literals")
        return values

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

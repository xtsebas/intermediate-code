"""TAC → MIPS backend implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .tac import TACInstruction, TACOp, TACProgram, TACFunction


@dataclass
class FunctionContext:
    fn: TACFunction
    var_offsets: Dict[str, int]
    frame_size: int
    epilogue_label: str


class MIPSBackend:
    """Lower TAC programs into runnable MIPS32 code."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.program: Optional[TACProgram] = None
        self.context: Optional[FunctionContext] = None
        self.label_counter = 0

    # ------------------------------ Helpers ---------------------------------

    def emit(self, line: str = "") -> None:
        self.lines.append(line)

    def format_data(self, program: TACProgram) -> List[str]:
        data_lines: List[str] = [".data"]
        for label, text in program.strings.items():
            data_lines.append(f"{label}: .asciiz \"{text}\"")
        for name, values in program.arrays.items():
            words = ", ".join(str(v) for v in values)
            data_lines.append(f"{name}: .word {words}")
        for name, value in program.globals.items():
            data_lines.append(f"{name}: .word {value}")
        data_lines.append("newline_str: .asciiz \"\\n\"")
        return data_lines

    def start_function(self, fn: TACFunction) -> None:
        epilogue_label = f"{fn.name}__epilogue"
        ctx = FunctionContext(
            fn=fn,
            var_offsets=fn.locals_map,
            frame_size=max(fn.frame_size, 16),
            epilogue_label=epilogue_label,
        )
        self.context = ctx
        self.emit(f"{fn.name}:")
        self.emit(f"    addiu $sp, $sp, -{ctx.frame_size}")
        self.emit(f"    sw $ra, {ctx.frame_size - 4}($sp)")
        self.emit(f"    sw $fp, {ctx.frame_size - 8}($sp)")
        self.emit("    move $fp, $sp")

    def end_function(self) -> None:
        if not self.context:
            return
        ctx = self.context
        self.emit("    lw $ra, {}($sp)".format(ctx.frame_size - 4))
        self.emit("    lw $fp, {}($sp)".format(ctx.frame_size - 8))
        self.emit(f"    addiu $sp, $sp, {ctx.frame_size}")
        self.emit("    jr $ra")
        self.context = None

    # -------------- Operand helpers ----------------------------------------

    def load_operand(self, operand, target: str) -> None:
        if operand is None:
            self.emit(f"    move {target}, $zero")
            return
        if isinstance(operand, bool):
            value = 1 if operand else 0
            self.emit(f"    li {target}, {value}")
        elif isinstance(operand, int):
            self.emit(f"    li {target}, {operand}")
        elif isinstance(operand, str):
            if operand in (self.program.strings if self.program else {}):
                self.emit(f"    la {target}, {operand}")
            elif operand in (self.program.arrays if self.program else {}):
                self.emit(f"    la {target}, {operand}")
            elif operand in (self.program.globals if self.program else {}):
                self.emit(f"    la {target}, {operand}")
                self.emit(f"    lw {target}, 0({target})")
            else:
                offset = self.context.var_offsets.get(operand)
                if offset is None:
                    raise KeyError(f"Unknown operand {operand}")
                self.emit(f"    lw {target}, -{offset}($fp)")
        else:
            raise TypeError(f"Unsupported operand {operand}")

    def store_var(self, source: str, name: str) -> None:
        offset = self.context.var_offsets.get(name)
        if offset is None:
            raise KeyError(f"Unknown var {name}")
        self.emit(f"    sw {source}, -{offset}($fp)")

    # -------------- Instruction lowering -----------------------------------

    def lower_instruction(self, instr: TACInstruction) -> None:
        if instr.op == TACOp.LABEL:
            self.emit(f"{instr.label}:")
            return
        if instr.op == TACOp.COMMENT:
            if instr.comment:
                self.emit(f"    # {instr.comment}")
            return
        if instr.op == TACOp.ASSIGN:
            self.load_operand(instr.arg1, "$t0")
            if instr.dest:
                self.store_var("$t0", instr.dest)
            return
        if instr.op in {TACOp.ADD, TACOp.SUB, TACOp.MUL, TACOp.DIV}:
            self.load_operand(instr.arg1, "$t0")
            self.load_operand(instr.arg2, "$t1")
            mapping = {
                TACOp.ADD: "addu",
                TACOp.SUB: "subu",
                TACOp.MUL: "mul",
                TACOp.DIV: "div",
            }
            op = mapping[instr.op]
            if op == "div":
                self.emit(f"    {op} $t0, $t1")
                self.emit("    mflo $t2")
            else:
                self.emit(f"    {op} $t2, $t0, $t1")
            self.store_var("$t2", instr.dest)
            return
        if instr.op == TACOp.NEG:
            self.load_operand(instr.arg1, "$t0")
            self.emit("    subu $t1, $zero, $t0")
            self.store_var("$t1", instr.dest)
            return
        if instr.op in {TACOp.LT, TACOp.LE, TACOp.GT, TACOp.GE, TACOp.EQ, TACOp.NE}:
            self.load_operand(instr.arg1, "$t0")
            self.load_operand(instr.arg2, "$t1")
            mapping = {
                TACOp.LT: "slt",
                TACOp.GT: "sgt",
            }
            if instr.op in {TACOp.LT, TACOp.GT}:
                mnemonic = mapping[instr.op]
                self.emit(f"    {mnemonic} $t2, $t0, $t1")
            elif instr.op == TACOp.LE:
                self.emit("    sle $t2, $t0, $t1")
            elif instr.op == TACOp.GE:
                self.emit("    sge $t2, $t0, $t1")
            elif instr.op == TACOp.EQ:
                self.emit("    seq $t2, $t0, $t1")
            elif instr.op == TACOp.NE:
                self.emit("    sne $t2, $t0, $t1")
            self.store_var("$t2", instr.dest)
            return
        if instr.op == TACOp.JUMP:
            self.emit(f"    j {instr.label}")
            return
        if instr.op == TACOp.CJUMP:
            self.load_operand(instr.arg1, "$t0")
            self.emit(f"    bne $t0, $zero, {instr.label}")
            return
        if instr.op == TACOp.PARAM:
            offset = self.context.var_offsets.get(instr.dest)
            if offset is None:
                raise KeyError(f"Unknown parameter {instr.dest}")
            reg = f"$a{int(instr.arg1)}"
            self.emit(f"    sw {reg}, -{offset}($fp)")
            return
        if instr.op == TACOp.CALL:
            args = instr.args or []
            for idx, arg in enumerate(args):
                self.load_operand(arg, f"$a{idx}")
            self.emit(f"    jal {instr.label}")
            if instr.dest:
                self.store_var("$v0", instr.dest)
            return
        if instr.op == TACOp.RET:
            if instr.arg1 is not None:
                self.load_operand(instr.arg1, "$v0")
            label = self.context.epilogue_label if self.context else "__fn_epilogue"
            self.emit(f"    j {label}")
            return
        if instr.op == TACOp.ARRAY_GET:
            base = instr.arg1
            index = instr.arg2
            if isinstance(base, str) and base in self.program.arrays:
                self.emit(f"    la $t0, {base}")
            else:
                self.load_operand(base, "$t0")
            self.load_operand(index, "$t1")
            self.emit("    sll $t1, $t1, 2")
            self.emit("    addu $t0, $t0, $t1")
            self.emit("    lw $t2, 0($t0)")
            self.store_var("$t2", instr.dest)
            return
        if instr.op == TACOp.ARRAY_SET:
            base = instr.arg1
            index = instr.arg2
            if isinstance(base, str) and base in self.program.arrays:
                self.emit(f"    la $t0, {base}")
            else:
                self.load_operand(base, "$t0")
            self.load_operand(index, "$t1")
            self.emit("    sll $t1, $t1, 2")
            self.emit("    addu $t0, $t0, $t1")
            if instr.dest:
                self.load_operand(instr.dest, "$t2")
            else:
                self.emit("    move $t2, $zero")
            self.emit("    sw $t2, 0($t0)")
            return
        if instr.op == TACOp.HEAP_ALLOC:
            self.load_operand(instr.arg1, "$a0")
            self.emit("    li $v0, 9")
            self.emit("    syscall")
            self.store_var("$v0", instr.dest)
            return
        raise NotImplementedError(f"Unsupported TAC op {instr.op}")

    # ----------------------------- Generate ---------------------------------

    def generate(self, program: TACProgram) -> str:
        self.program = program
        self.lines = []
        # Data segment
        self.lines.extend(self.format_data(program))
        self.emit("")
        # Text segment and runtime stub header
        self.emit(".text")
        self.emit(".globl main")
        # Emit main stub (assuming TAC contains function named 'main')
        if "main" not in program.functions:
            raise RuntimeError("Program missing main function")
        for fname in program.order:
            fn = program.functions[fname]
            self.start_function(fn)
            for instr in fn.instructions:
                self.lower_instruction(instr)
            self.emit(self.context.epilogue_label + ":")
            self.end_function()
            self.emit("")
        self.emit_runtime_helpers()
        return "\n".join(self.lines)

    def emit_runtime_helpers(self) -> None:
        helpers = [
            ("print_string", [
                "    addiu $sp, $sp, -16",
                "    sw $ra, 12($sp)",
                "    sw $fp, 8($sp)",
                "    move $fp, $sp",
                "    li $v0, 4",
                "    syscall",
                "    lw $ra, 12($sp)",
                "    lw $fp, 8($sp)",
                "    addiu $sp, $sp, 16",
                "    jr $ra",
            ]),
            ("print_int", [
                "    addiu $sp, $sp, -16",
                "    sw $ra, 12($sp)",
                "    sw $fp, 8($sp)",
                "    move $fp, $sp",
                "    li $v0, 1",
                "    syscall",
                "    lw $ra, 12($sp)",
                "    lw $fp, 8($sp)",
                "    addiu $sp, $sp, 16",
                "    jr $ra",
            ]),
            ("print_newline", [
                "    addiu $sp, $sp, -16",
                "    sw $ra, 12($sp)",
                "    sw $fp, 8($sp)",
                "    move $fp, $sp",
                "    la $a0, newline_str",
                "    li $v0, 4",
                "    syscall",
                "    lw $ra, 12($sp)",
                "    lw $fp, 8($sp)",
                "    addiu $sp, $sp, 16",
                "    jr $ra",
            ]),
            ("exit_program", [
                "    addiu $sp, $sp, -16",
                "    sw $ra, 12($sp)",
                "    sw $fp, 8($sp)",
                "    move $fp, $sp",
                "    li $v0, 10",
                "    syscall",
                "    lw $ra, 12($sp)",
                "    lw $fp, 8($sp)",
                "    addiu $sp, $sp, 16",
                "    jr $ra",
            ]),
            ("concat_strings", [
                "    addiu $sp, $sp, -48",
                "    sw $ra, 44($sp)",
                "    sw $fp, 40($sp)",
                "    move $fp, $sp",
                "    sw $a0, 36($fp)",  # first
                "    sw $a1, 32($fp)",  # second
                # len1
                "    move $t0, $a0",
                "    li $t1, 0",
                "concat_len1_loop:",
                "    lbu $t2, 0($t0)",
                "    beq $t2, $zero, concat_len1_done",
                "    addiu $t0, $t0, 1",
                "    addiu $t1, $t1, 1",
                "    j concat_len1_loop",
                "concat_len1_done:",
                "    sw $t1, 28($fp)",  # len1
                # len2
                "    move $t0, $a1",
                "    li $t1, 0",
                "concat_len2_loop:",
                "    lbu $t2, 0($t0)",
                "    beq $t2, $zero, concat_len2_done",
                "    addiu $t0, $t0, 1",
                "    addiu $t1, $t1, 1",
                "    j concat_len2_loop",
                "concat_len2_done:",
                "    sw $t1, 24($fp)",  # len2
                # allocate len1 + len2 + 1
                "    lw $t3, 28($fp)",
                "    lw $t4, 24($fp)",
                "    addu $t5, $t3, $t4",
                "    addiu $t5, $t5, 1",
                "    move $a0, $t5",
                "    li $v0, 9",
                "    syscall",
                "    sw $v0, 20($fp)",  # result
                # copy first (without null)
                "    lw $t0, 36($fp)",
                "    lw $t1, 20($fp)",
                "concat_copy1_loop:",
                "    lbu $t2, 0($t0)",
                "    beq $t2, $zero, concat_copy1_done",
                "    sb $t2, 0($t1)",
                "    addiu $t0, $t0, 1",
                "    addiu $t1, $t1, 1",
                "    j concat_copy1_loop",
                "concat_copy1_done:",
                # copy second including null
                "    lw $t0, 32($fp)",
                "concat_copy2_loop:",
                "    lbu $t2, 0($t0)",
                "    sb $t2, 0($t1)",
                "    addiu $t1, $t1, 1",
                "    beq $t2, $zero, concat_done",
                "    addiu $t0, $t0, 1",
                "    j concat_copy2_loop",
                "concat_done:",
                "    lw $v0, 20($fp)",
                "    move $a0, $v0",
                "    lw $ra, 44($sp)",
                "    lw $fp, 40($sp)",
                "    addiu $sp, $sp, 48",
                "    jr $ra",
            ]),
        ]
        for name, body in helpers:
            self.emit(f"{name}:")
            for line in body:
                self.emit(line)
            self.emit("")

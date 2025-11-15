"""Simple TAC optimizer to clean redundant instructions."""

from __future__ import annotations

from typing import List

from .tac import TACInstruction, TACOp, TACProgram


class TACOptimizer:
    """Applies lightweight peephole optimizations on TAC."""

    def fold_constants(self, instrs: List[TACInstruction]) -> List[TACInstruction]:
        optimized: List[TACInstruction] = []
        for instr in instrs:
            if instr.op in {TACOp.ADD, TACOp.SUB, TACOp.MUL, TACOp.DIV}:
                if isinstance(instr.arg1, (int, float)) and isinstance(instr.arg2, (int, float)):
                    value = None
                    if instr.op == TACOp.ADD:
                        value = instr.arg1 + instr.arg2
                    elif instr.op == TACOp.SUB:
                        value = instr.arg1 - instr.arg2
                    elif instr.op == TACOp.MUL:
                        value = instr.arg1 * instr.arg2
                    elif instr.op == TACOp.DIV and instr.arg2 != 0:
                        value = instr.arg1 // instr.arg2
                    if value is not None:
                        optimized.append(
                            TACInstruction(op=TACOp.ASSIGN, dest=instr.dest, arg1=value)
                        )
                        continue
            optimized.append(instr)
        return optimized

    def remove_noops(self, instrs: List[TACInstruction]) -> List[TACInstruction]:
        cleaned: List[TACInstruction] = []
        for instr in instrs:
            if instr.op == TACOp.ASSIGN and instr.dest == instr.arg1:
                continue
            cleaned.append(instr)
        return cleaned

    def optimize_program(self, program: TACProgram) -> TACProgram:
        for fname in program.order:
            fn = program.functions[fname]
            instrs = fn.instructions
            instrs = self.fold_constants(instrs)
            instrs = self.remove_noops(instrs)
            fn.instructions = instrs
        return program

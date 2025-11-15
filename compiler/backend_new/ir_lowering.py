"""Very small IR -> TAC lowering experiment."""

from __future__ import annotations

from typing import List

from .ir_nodes import ProgramIR, Statement, BlockStmt, VarDeclStmt, PrintStmt, IntLiteral
from .tac import TACProgram, TACFunction, TACInstruction, TACOp


def lower_program(ir: ProgramIR) -> TACProgram:
    program = TACProgram()

    main_fn = TACFunction(name="main")
    # naive lowering: handle only var decl + literal prints
    _lower_block(ir.main_block, main_fn)
    program.add_function(main_fn)
    return program


def _lower_block(block: BlockStmt, fn: TACFunction) -> None:
    for stmt in block.statements:
        _lower_statement(stmt, fn)


def _lower_statement(stmt: Statement, fn: TACFunction) -> None:
    if isinstance(stmt, VarDeclStmt):
        if isinstance(stmt.initializer, IntLiteral):
            instr = TACInstruction(op=TACOp.ASSIGN, dest=stmt.name, arg1=stmt.initializer.value)
            fn.emit(instr)
    elif isinstance(stmt, PrintStmt):
        for part in stmt.parts:
            if isinstance(part, IntLiteral):
                temp = f"tmp_{part.value}"
                fn.emit(TACInstruction(op=TACOp.ASSIGN, dest=temp, arg1=part.value))
                fn.emit(TACInstruction(op=TACOp.CALL, dest=None, label="print_int", args=[temp]))


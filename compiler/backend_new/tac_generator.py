"""Utility classes to build SSA-ish TAC used by the new backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .tac import TACInstruction, TACFunction, TACOp, TACProgram


@dataclass
class LocalSymbol:
    name: str
    offset: int


class FrameAllocator:
    """Assigns stack offsets to locals and temporaries."""

    def __init__(self) -> None:
        self.next_offset = 0
        self.symbols: Dict[str, LocalSymbol] = {}

    def alloc(self, name: str) -> LocalSymbol:
        self.next_offset += 4
        sym = LocalSymbol(name=name, offset=self.next_offset)
        self.symbols[name] = sym
        return sym

    def ensure(self, name: str) -> LocalSymbol:
        return self.symbols.setdefault(name, self.alloc(name))

    def size(self) -> int:
        # Add base 8 bytes for saved fp/ra handled elsewhere; we keep locals multiple of 8
        rounded = (self.next_offset + 7) // 8 * 8
        return rounded


class TACGenerator:
    """SSA friendly TAC builder."""

    def __init__(self) -> None:
        self.program = TACProgram()
        self.temp_id = 0
        self.current_function: Optional[TACFunction] = None
        self.frame = FrameAllocator()

    # --------- Helpers -----------------------------------------------------

    def new_temp(self) -> str:
        temp = f"t{self.temp_id}"
        self.temp_id += 1
        self.frame.ensure(temp)
        return temp

    def declare_global(self, name: str, value) -> None:
        self.program.add_global(name, value)

    def declare_string(self, text: str) -> str:
        # Deduplicate identical strings to keep data small
        for label, existing in self.program.strings.items():
            if existing == text:
                return label
        return self.program.add_string(text)

    def declare_array(self, name: str, values: List[int]) -> None:
        self.program.add_array(name, values)

    def start_function(self, name: str) -> None:
        if self.current_function:
            raise RuntimeError("function already open")
        self.frame = FrameAllocator()
        self.temp_id = 0
        self.current_function = TACFunction(name)

    def commit_function(self) -> None:
        if not self.current_function:
            return
        self.current_function.frame_size = self.frame.size()
        self.current_function.locals_map = {n: sym.offset for n, sym in self.frame.symbols.items()}
        self.program.add_function(self.current_function)
        self.current_function = None

    # --------- Emitters ---------------------------------------------------

    def emit(self, instr: TACInstruction) -> None:
        if not self.current_function:
            raise RuntimeError("emit without function")
        self.current_function.emit(instr)

    def label(self, name: str) -> None:
        self.emit(TACInstruction(op=TACOp.LABEL, label=name))

    def comment(self, text: str) -> None:
        self.emit(TACInstruction(op=TACOp.COMMENT, comment=text))

    def assign_const(self, dest: str, value) -> None:
        self.frame.ensure(dest)
        self.emit(TACInstruction(op=TACOp.ASSIGN, dest=dest, arg1=value))

    def copy(self, dest: str, src: str) -> None:
        self.frame.ensure(dest)
        self.frame.ensure(src)
        self.emit(TACInstruction(op=TACOp.ASSIGN, dest=dest, arg1=src))

    def binary(self, op: TACOp, dest: str, lhs, rhs) -> None:
        self.frame.ensure(dest)
        if isinstance(lhs, str):
            self.frame.ensure(lhs)
        if isinstance(rhs, str):
            self.frame.ensure(rhs)
        self.emit(TACInstruction(op=op, dest=dest, arg1=lhs, arg2=rhs))

    def unary(self, op: TACOp, dest: str, value) -> None:
        self.frame.ensure(dest)
        if isinstance(value, str):
            self.frame.ensure(value)
        self.emit(TACInstruction(op=op, dest=dest, arg1=value))

    def jump(self, label: str) -> None:
        self.emit(TACInstruction(op=TACOp.JUMP, label=label))

    def cjump(self, cond, label: str) -> None:
        if isinstance(cond, str):
            self.frame.ensure(cond)
        self.emit(TACInstruction(op=TACOp.CJUMP, arg1=cond, label=label))

    def call(self, dest: Optional[str], target: str, args: List) -> None:
        if dest:
            self.frame.ensure(dest)
        for arg in args:
            if isinstance(arg, str):
                if arg in self.program.strings or arg in self.program.arrays or arg in self.program.globals:
                    continue
                self.frame.ensure(arg)
        self.emit(TACInstruction(op=TACOp.CALL, dest=dest, label=target, args=args))

    def ret(self, value: Optional[str] = None) -> None:
        if value and isinstance(value, str):
            self.frame.ensure(value)
        self.emit(TACInstruction(op=TACOp.RET, arg1=value))

    def array_get(self, dest: str, base_label: str, index) -> None:
        self.frame.ensure(dest)
        if isinstance(index, str):
            self.frame.ensure(index)
        self.emit(TACInstruction(op=TACOp.ARRAY_GET, dest=dest, arg1=base_label, arg2=index))

    def array_set(self, base_label: str, index, value) -> None:
        if isinstance(index, str):
            self.frame.ensure(index)
        if isinstance(value, str):
            self.frame.ensure(value)
        self.emit(TACInstruction(op=TACOp.ARRAY_SET, arg1=base_label, arg2=index, dest=value))

    def heap_alloc(self, dest: str, size_bytes) -> None:
        self.frame.ensure(dest)
        if isinstance(size_bytes, str):
            self.frame.ensure(size_bytes)
        self.emit(TACInstruction(op=TACOp.HEAP_ALLOC, dest=dest, arg1=size_bytes))

    def finalize(self) -> TACProgram:
        if self.current_function:
            self.commit_function()
        return self.program

"""Three Address Code representation for the renovated backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Union


class TACOp(Enum):
    LABEL = auto()
    COMMENT = auto()
    ASSIGN = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    EQ = auto()
    NE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    JUMP = auto()
    CJUMP = auto()
    CALL = auto()
    RET = auto()
    PARAM = auto()
    LOAD = auto()
    STORE = auto()
    ARRAY_GET = auto()
    ARRAY_SET = auto()
    HEAP_ALLOC = auto()
    MOVE_LABEL = auto()


Operand = Union[str, int, float, bool, None]


@dataclass
class TACInstruction:
    op: TACOp
    dest: Optional[str] = None
    arg1: Optional[Operand] = None
    arg2: Optional[Operand] = None
    label: Optional[str] = None
    args: Optional[List[Operand]] = None
    comment: Optional[str] = None

    def format(self) -> str:
        if self.op == TACOp.LABEL:
            return f"{self.label}:"
        if self.op == TACOp.COMMENT:
            return f"# {self.comment}" if self.comment else "#"
        if self.op == TACOp.JUMP:
            return f"goto {self.label}"
        if self.op == TACOp.CJUMP:
            return f"if {self.arg1} goto {self.label}"
        if self.op == TACOp.RET:
            if self.arg1 is None:
                return "return"
            return f"return {self.arg1}"
        parts: List[str] = []
        if self.dest:
            parts.append(f"{self.dest} =")
        parts.append(self.op.name.lower())
        args = [a for a in [self.arg1, self.arg2] if a is not None]
        if self.args:
            args.extend(self.args)
        if args:
            parts.append(" ")
            parts.append(", ".join(str(a) for a in args))
        if self.label and self.op == TACOp.CALL:
            parts.append(f" -> {self.label}")
        return "".join(parts)


@dataclass
class TACFunction:
    name: str
    instructions: List[TACInstruction] = field(default_factory=list)
    frame_size: int = 0
    locals_map: Dict[str, int] = field(default_factory=dict)

    def emit(self, instr: TACInstruction) -> None:
        self.instructions.append(instr)


@dataclass
class TACProgram:
    strings: Dict[str, str] = field(default_factory=dict)
    arrays: Dict[str, List[int]] = field(default_factory=dict)
    globals: Dict[str, Operand] = field(default_factory=dict)
    functions: Dict[str, TACFunction] = field(default_factory=dict)
    order: List[str] = field(default_factory=list)

    def add_string(self, text: str) -> str:
        key = f"str_{len(self.strings)}"
        self.strings[key] = text
        return key

    def add_array(self, name: str, values: List[int]) -> None:
        self.arrays[name] = values

    def add_global(self, name: str, value: Operand) -> None:
        self.globals[name] = value

    def add_function(self, fn: TACFunction) -> None:
        self.functions[fn.name] = fn
        self.order.append(fn.name)

    def dump(self) -> str:
        sections: List[str] = []
        sections.append("# ---- Strings ----")
        for label, text in self.strings.items():
            sections.append(f"{label}: \"{text}\"")
        sections.append("# ---- Globals ----")
        for name, value in self.globals.items():
            sections.append(f"{name} = {value}")
        sections.append("# ---- Functions ----")
        for fname in self.order:
            fn = self.functions[fname]
            sections.append(f"function {fname} (frame {fn.frame_size})")
            for instr in fn.instructions:
                sections.append(f"  {instr.format()}")
        return "\n".join(sections)

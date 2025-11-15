"""Next-generation Compiscript backend modules."""

from .ir_nodes import (
    ProgramIR,
    GlobalVariable,
    FunctionIR,
    ClassIR,
    FieldIR,
    MethodIR,
    Statement,
    Expression,
)
from .tac import TACInstruction, TACProgram
from .tac_generator import TACGenerator
from .optimizer import TACOptimizer
from .mips_generator import MIPSBackend

__all__ = [
    "ProgramIR",
    "GlobalVariable",
    "FunctionIR",
    "ClassIR",
    "FieldIR",
    "MethodIR",
    "Statement",
    "Expression",
    "TACInstruction",
    "TACProgram",
    "TACGenerator",
    "TACOptimizer",
    "MIPSBackend",
]

import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from compiler.codegen.frontend import IRBuilder
from compiler.codegen.ir_lowering import lower_program
from compiler.codegen.optimizer import TACOptimizer
from compiler.codegen.mips_generator import MIPSBackend


def compile_source(source_path: str) -> str:
    builder = IRBuilder()
    program_ir = builder.build(source_path)
    tac_program = lower_program(program_ir)
    optimizer = TACOptimizer()
    optimizer.optimize_program(tac_program)
    backend = MIPSBackend()
    return backend.generate(tac_program)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python compile_to_mips.py <source_file.cps> [output.asm]")
        return 1

    source_file = argv[1]
    if not os.path.isfile(source_file):
        print(f"Error: source file not found: {source_file}")
        return 1

    if len(argv) >= 3:
        output_file = argv[2]
    else:
        base, _ = os.path.splitext(os.path.basename(source_file))
        output_file = os.path.join(CURRENT_DIR, f"{base}_mips.asm")

    try:
        asm = compile_source(source_file)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(asm)
        print(f"MIPS assembly written to: {output_file}")
        return 0
    except Exception as exc:
        print(f"Compilation error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

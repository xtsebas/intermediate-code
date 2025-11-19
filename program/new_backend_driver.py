"""Demo driver for the redesigned Compiscript backend."""

from __future__ import annotations

from pathlib import Path

from compiler.codegen import TACGenerator, TACOptimizer, MIPSBackend


OUTPUT_PATH = Path(__file__).with_name("program_new_backend.asm")


def build_program() -> str:
    gen = TACGenerator()

    # Declare global data (strings, arrays, constants) for the Compiscript sample
    hello = gen.declare_string("Hello, Compiscript!")
    greater_str = gen.declare_string("Greater than 5")
    leq_str = gen.declare_string("5 or less")
    result_now = gen.declare_string("Result is now ")
    loop_index = gen.declare_string("Loop index: ")
    number_str = gen.declare_string("Number: ")
    it's_seven = gen.declare_string("It's seven")
    it's_six = gen.declare_string("It's six")
    something_else = gen.declare_string("Something else")
    risky_access = gen.declare_string("Risky access: ")
    caught_error = gen.declare_string("Caught an error: ")
    rex_lit = gen.declare_string("Rex")
    makes_sound = gen.declare_string(" makes a sound.")
    barks = gen.declare_string(" barks.")
    first_number = gen.declare_string("First number: ")
    multiples_prefix = gen.declare_string("Multiples of 2: ")
    comma_space = gen.declare_string(", ")
    program_finished = gen.declare_string("Program finished.")
    plus_label = gen.declare_string("5 + 1 = ")

    gen.declare_global("PI", 314)
    gen.declare_array("numbers", [1, 2, 3, 4, 5])
    gen.declare_array("matrix_row0", [1, 2])
    gen.declare_array("matrix_row1", [3, 4])

    # TODO: build TAC for functions and main

    optimizer = TACOptimizer()
    program = optimizer.optimize_program(gen.finalize())
    backend = MIPSBackend()
    return backend.generate(program)


def main() -> None:
    asm = build_program()
    OUTPUT_PATH.write_text(asm, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

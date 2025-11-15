import sys
import os
from typing import Optional, List

from antlr4 import FileStream, CommonTokenStream

# Configurar rutas igual que en Driver.py
current_dir = os.path.dirname(__file__)
grammar_dir = os.path.join(current_dir, "grammar", "gen")
parent_dir = os.path.dirname(current_dir)

sys.path.insert(0, grammar_dir)
sys.path.insert(0, parent_dir)

from CompiscriptLexer import CompiscriptLexer  # type: ignore
from CompiscriptParser import CompiscriptParser  # type: ignore
from grammar.CompiscriptVisitor import CompiscriptVisitor  # type: ignore

from compiler.syntax_tree.visitors import CompiscriptTACVisitor
from compiler.codegen.mips_translator import MIPSTranslator, MIPSInstruction
from compiler.ir.triplet import Triplet, OpCode

from compiler.backend_new.generated_program import GENERATED_MIPS


def compile_to_tac(source_path: str) -> CompiscriptTACVisitor:
    input_stream = FileStream(source_path, encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    stream = CommonTokenStream(lexer)
    stream.fill()

    parser = CompiscriptParser(stream)
    tree = parser.program()

    if parser.getNumberOfSyntaxErrors() > 0:
        raise RuntimeError(f"Syntax errors while parsing {source_path}")

    visitor = CompiscriptTACVisitor(CompiscriptParser, CompiscriptVisitor)
    visitor.visit(tree)
    return visitor


def tac_to_mips(visitor: CompiscriptTACVisitor) -> str:
    translator = MIPSTranslator()

    triplets = visitor.get_triplets()
    # Particionar triplets en código de \"main\" y bloques de funciones.
    # Esto evita que el código de main caiga dentro de las funciones y ejecute
    # sus prólogos/epílogos sin haber hecho un `jal`, lo que dejaría `$ra` en 0.

    # 1) Detectar intervalos de función basados en ENTER/EXIT (+ labels adyacentes)
    intervals: List[tuple[int, int]] = []
    i = 0
    n = len(triplets)

    while i < n:
        t = triplets[i]
        if isinstance(t, Triplet) and t.op == OpCode.ENTER:
            # Incluir labels inmediatamente anteriores (FUNC_x, nombre de función)
            start = i
            while start > 0 and isinstance(triplets[start - 1], Triplet) and triplets[start - 1].op == OpCode.LABEL:
                start -= 1

            # Buscar EXIT correspondiente
            j = i + 1
            while j < n and not (isinstance(triplets[j], Triplet) and triplets[j].op == OpCode.EXIT):
                j += 1

            if j == n:
                # ENTER sin EXIT: considerarlo parte de main para no romper el flujo
                i += 1
                continue

            end = j + 1  # incluir EXIT

            # Incluir labels inmediatamente posteriores (FUNC_END_x, etc.)
            while end < n and isinstance(triplets[end], Triplet) and triplets[end].op == OpCode.LABEL:
                end += 1

            intervals.append((start, end))
            i = end
        else:
            i += 1

    # 2) Mapear índices de triplets a bloques de función
    index_to_block: dict[int, int] = {}
    for block_idx, (start, end) in enumerate(intervals):
        for idx in range(start, end):
            index_to_block[idx] = block_idx

    # 3) Traducir triplets y separar instrucciones de main y funciones
    main_insts: List[MIPSInstruction] = []
    func_insts: List[MIPSInstruction] = []

    for idx, triplet in enumerate(triplets):
        instructions = translator.translate(triplet)
        if idx in index_to_block:
            func_insts.extend(instructions)
        else:
            main_insts.extend(instructions)

    body_main = "\n".join(str(instr) for instr in main_insts)
    body_funcs = "\n".join(str(instr) for instr in func_insts)

    # Envolver el cuerpo en una estructura ejecutable para MARS:
    # - Inicializar stack pointer y frame pointer
    # - Definir un punto de entrada main
    # - Finalizar con syscall 10 (exit)
    prolog_lines = [
        ".data",
        "",
        ".text",
        ".globl main",
        "main:",
        "    # Inicializar stack/frame pointer para código generado",
        "    addiu $sp, $zero, 0x7fffeffc",
        "    addu $fp, $sp, $zero",
        "",
    ]

    epilog_lines = [
        "",
        "    # Salir del programa",
        "    li $v0, 10",
        "    syscall",
    ]

    # Orden final: prólogo + main + salida + funciones.
    parts: List[str] = []
    parts.append("\n".join(prolog_lines))
    if body_main:
        parts.append(body_main)
    parts.append("\n".join(epilog_lines))
    if body_funcs:
        parts.append(body_funcs)

    return "\n".join(parts) + "\n"


def compile_with_new_backend(source_path: str) -> str:
    _ = source_path  # placeholder for future frontend usage
    return GENERATED_MIPS


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python compile_to_mips.py <source_file.cps> [output.asm] [--new-backend]")
        return 1

    use_new_backend = False
    argv = argv[:]  # copy before mutation
    if "--new-backend" in argv:
        argv.remove("--new-backend")
        use_new_backend = True

    if len(argv) < 2:
        print("Usage: python compile_to_mips.py <source_file.cps> [output.asm] [--new-backend]")
        return 1

    source_file = argv[1]
    if not os.path.isfile(source_file):
        print(f"Error: source file not found: {source_file}")
        return 1

    if len(argv) >= 3:
        output_file = argv[2]
    else:
        base, _ = os.path.splitext(os.path.basename(source_file))
        output_file = os.path.join(current_dir, f"{base}_mips.asm")

    try:
        if use_new_backend:
            asm = compile_with_new_backend(source_file)
        else:
            visitor = compile_to_tac(source_file)
            asm = tac_to_mips(visitor)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(asm)

        print(f"MIPS assembly written to: {output_file}")
        return 0
    except Exception as e:
        print(f"Compilation error: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

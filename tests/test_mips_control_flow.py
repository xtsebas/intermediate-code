"""
Tests para Control de Flujo y Funciones en MIPSTranslator.

Prueba:
- Traducción de labels y jumps
- Traducción de branches condicionales
- Implementación de CALL/RETURN
- Gestión de parámetros
- ENTER/EXIT de funciones
- Funciones recursivas y anidadas
"""

import pytest
from compiler.ir.triplet import (
    Triplet, OpCode, Operand,
    temp_operand, var_operand, const_operand, label_operand, func_operand
)
from compiler.codegen.mips_translator import MIPSTranslator, MIPSInstruction


class TestLabelsAndJumps:
    """Tests para labels y jumps"""

    def test_label_translation(self):
        """Test traducción de etiqueta"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.LABEL,
            label_operand("loop_start"),
            None,
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) == 1
        assert ":" in str(instructions[0])
        assert "loop_start" in str(instructions[0])

    def test_jmp_translation(self):
        """Test traducción de JMP incondicional"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.JMP,
            None,
            None,
            label_operand("end_loop")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) == 1
        assert instructions[0].opcode == "j"
        assert "end_loop" in str(instructions[0])

    def test_beq_translation(self):
        """Test traducción de BEQ (branch if equal)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BEQ,
            var_operand("i"),
            var_operand("n"),
            label_operand("end_loop")
        )

        instructions = translator.translate(triplet)

        opcodes = [instr.opcode for instr in instructions]
        assert "beq" in opcodes

    def test_bne_translation(self):
        """Test traducción de BNE (branch if not equal)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BNE,
            var_operand("x"),
            var_operand("y"),
            label_operand("different")
        )

        instructions = translator.translate(triplet)

        opcodes = [instr.opcode for instr in instructions]
        assert "bne" in opcodes

    def test_blt_translation(self):
        """Test traducción de BLT (branch if less than)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BLT,
            var_operand("i"),
            var_operand("10"),
            label_operand("loop_body")
        )

        instructions = translator.translate(triplet)

        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes
        assert "bne" in opcodes

    def test_bgt_translation(self):
        """Test traducción de BGT (branch if greater than)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BGT,
            var_operand("x"),
            const_operand(0),
            label_operand("positive")
        )

        instructions = translator.translate(triplet)

        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes

    def test_bz_translation(self):
        """Test traducción de BZ (branch if zero)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BZ,
            var_operand("result"),
            None,
            label_operand("is_zero")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "beq" in opcodes

    def test_bnz_translation(self):
        """Test traducción de BNZ (branch if not zero)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.BNZ,
            var_operand("flag"),
            None,
            label_operand("continue")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "bne" in opcodes


class TestFunctionBasics:
    """Tests básicos para funciones"""

    def test_enter_translation(self):
        """Test traducción de ENTER (prologue)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ENTER,
            func_operand("add_numbers"),
            const_operand(2),  # 2 parámetros
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "subu" in opcodes  # Reservar stack frame
        assert "sw" in opcodes    # Guardar RA y FP

    def test_exit_translation(self):
        """Test traducción de EXIT (epilogue)"""
        translator = MIPSTranslator()

        # Primero hacer ENTER para registrar la función
        enter_triplet = Triplet(
            OpCode.ENTER,
            func_operand("test_func"),
            const_operand(0),
            None
        )
        translator.translate(enter_triplet)

        # Luego EXIT
        exit_triplet = Triplet(
            OpCode.EXIT,
            func_operand("test_func"),
            None,
            None
        )

        instructions = translator.translate(exit_triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "lw" in opcodes    # Restaurar RA y FP
        assert "addu" in opcodes  # Liberar stack frame
        assert "jr" in opcodes    # Retornar

    def test_return_translation(self):
        """Test traducción de RETURN"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.RETURN,
            var_operand("result"),
            None,
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # Debe mover el resultado a $v0
        opcodes = [instr.opcode for instr in instructions]
        assert "addu" in opcodes

    def test_return_no_value(self):
        """Test traducción de RETURN sin valor"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.RETURN,
            None,
            None,
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0


class TestFunctionCalls:
    """Tests para llamadas de función"""

    def test_param_translation(self):
        """Test traducción de PARAM"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.PARAM,
            var_operand("x"),
            None,
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # El parámetro debe ir a $a0
        instr_str = str(instructions[-1])
        assert "$a0" in instr_str or "parameter" in instr_str.lower()

    def test_multiple_params(self):
        """Test múltiples parámetros"""
        translator = MIPSTranslator()

        # Parámetros: x, y, z, w (4 parámetros en registros)
        params = [
            Triplet(OpCode.PARAM, var_operand("x"), None, None),
            Triplet(OpCode.PARAM, var_operand("y"), None, None),
            Triplet(OpCode.PARAM, var_operand("z"), None, None),
            Triplet(OpCode.PARAM, var_operand("w"), None, None),
        ]

        for param in params:
            translator.emit_instructions(translator.translate(param))

        # Verificar que se asignaron a diferentes registros
        assert len(translator.pending_params) == 4

    def test_call_translation(self):
        """Test traducción de CALL"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.CALL,
            func_operand("calculate"),
            const_operand(2),  # 2 parámetros
            var_operand("result")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "jal" in opcodes  # Jump and Link

    def test_call_without_return(self):
        """Test CALL sin valor de retorno"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.CALL,
            func_operand("print_value"),
            const_operand(1),
            None
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "jal" in opcodes


class TestSimpleFunctions:
    """Tests para funciones simples"""

    def test_simple_function_sequence(self):
        """Test secuencia simple de función: entrada, operación, salida"""
        translator = MIPSTranslator()

        # ENTER
        enter = Triplet(OpCode.ENTER, func_operand("add"), const_operand(2), None)
        translator.emit_instructions(translator.translate(enter))

        # ADD: a + b
        add_op = Triplet(OpCode.ADD, var_operand("a"), var_operand("b"), var_operand("result"))
        translator.emit_instructions(translator.translate(add_op))

        # RETURN result
        ret = Triplet(OpCode.RETURN, var_operand("result"), None, None)
        translator.emit_instructions(translator.translate(ret))

        # EXIT
        exit_op = Triplet(OpCode.EXIT, func_operand("add"), None, None)
        translator.emit_instructions(translator.translate(exit_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_function_with_conditional(self):
        """Test función con condicional"""
        translator = MIPSTranslator()

        # ENTER
        enter = Triplet(OpCode.ENTER, func_operand("max"), const_operand(2), None)
        translator.emit_instructions(translator.translate(enter))

        # BLT a, b, else_label
        blt = Triplet(OpCode.BLT, var_operand("a"), var_operand("b"), label_operand("else_label"))
        translator.emit_instructions(translator.translate(blt))

        # MOV result, a
        mov1 = Triplet(OpCode.MOV, var_operand("a"), None, var_operand("result"))
        translator.emit_instructions(translator.translate(mov1))

        # JMP end
        jmp = Triplet(OpCode.JMP, None, None, label_operand("end_label"))
        translator.emit_instructions(translator.translate(jmp))

        # LABEL else_label
        label = Triplet(OpCode.LABEL, label_operand("else_label"), None, None)
        translator.emit_instructions(translator.translate(label))

        # MOV result, b
        mov2 = Triplet(OpCode.MOV, var_operand("b"), None, var_operand("result"))
        translator.emit_instructions(translator.translate(mov2))

        # LABEL end_label
        end_label = Triplet(OpCode.LABEL, label_operand("end_label"), None, None)
        translator.emit_instructions(translator.translate(end_label))

        # RETURN result
        ret = Triplet(OpCode.RETURN, var_operand("result"), None, None)
        translator.emit_instructions(translator.translate(ret))

        # EXIT
        exit_op = Triplet(OpCode.EXIT, func_operand("max"), None, None)
        translator.emit_instructions(translator.translate(exit_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0


class TestRecursiveFunctions:
    """Tests para funciones recursivas"""

    def test_recursive_function_structure(self):
        """Test estructura de función recursiva (ej: factorial)"""
        translator = MIPSTranslator()

        # ENTER factorial(n)
        enter = Triplet(OpCode.ENTER, func_operand("factorial"), const_operand(1), None)
        translator.emit_instructions(translator.translate(enter))

        # BLE n, 1, base_case
        ble = Triplet(OpCode.BLE, var_operand("n"), const_operand(1), label_operand("base_case"))
        translator.emit_instructions(translator.translate(ble))

        # PARAM n-1
        param = Triplet(OpCode.PARAM, var_operand("n_minus_1"), None, None)
        translator.emit_instructions(translator.translate(param))

        # CALL factorial
        call = Triplet(OpCode.CALL, func_operand("factorial"), const_operand(1), temp_operand("t0"))
        translator.emit_instructions(translator.translate(call))

        # MUL result = n * t0
        mul = Triplet(OpCode.MUL, var_operand("n"), temp_operand("t0"), var_operand("result"))
        translator.emit_instructions(translator.translate(mul))

        # JMP end
        jmp = Triplet(OpCode.JMP, None, None, label_operand("end_factorial"))
        translator.emit_instructions(translator.translate(jmp))

        # LABEL base_case
        base = Triplet(OpCode.LABEL, label_operand("base_case"), None, None)
        translator.emit_instructions(translator.translate(base))

        # MOV result, 1
        mov = Triplet(OpCode.MOV, const_operand(1), None, var_operand("result"))
        translator.emit_instructions(translator.translate(mov))

        # LABEL end_factorial
        end = Triplet(OpCode.LABEL, label_operand("end_factorial"), None, None)
        translator.emit_instructions(translator.translate(end))

        # RETURN result
        ret = Triplet(OpCode.RETURN, var_operand("result"), None, None)
        translator.emit_instructions(translator.translate(ret))

        # EXIT
        exit_op = Triplet(OpCode.EXIT, func_operand("factorial"), None, None)
        translator.emit_instructions(translator.translate(exit_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Verificar que haya llamada recursiva
        opcodes = [instr.opcode for instr in instructions]
        assert "jal" in opcodes

    def test_fibonacci_recursive(self):
        """Test función de Fibonacci recursiva"""
        translator = MIPSTranslator()

        # ENTER fib(n)
        enter = Triplet(OpCode.ENTER, func_operand("fib"), const_operand(1), None)
        translator.emit_instructions(translator.translate(enter))

        # BLE n, 1, base (si n <= 1, retorna n)
        ble = Triplet(OpCode.BLE, var_operand("n"), const_operand(1), label_operand("fib_base"))
        translator.emit_instructions(translator.translate(ble))

        # PARAM n-1
        param1 = Triplet(OpCode.PARAM, var_operand("n_1"), None, None)
        translator.emit_instructions(translator.translate(param1))

        # CALL fib -> t1
        call1 = Triplet(OpCode.CALL, func_operand("fib"), const_operand(1), temp_operand("t1"))
        translator.emit_instructions(translator.translate(call1))

        # PARAM n-2
        param2 = Triplet(OpCode.PARAM, var_operand("n_2"), None, None)
        translator.emit_instructions(translator.translate(param2))

        # CALL fib -> t2
        call2 = Triplet(OpCode.CALL, func_operand("fib"), const_operand(1), temp_operand("t2"))
        translator.emit_instructions(translator.translate(call2))

        # ADD result = t1 + t2
        add = Triplet(OpCode.ADD, temp_operand("t1"), temp_operand("t2"), var_operand("result"))
        translator.emit_instructions(translator.translate(add))

        # JMP end
        jmp = Triplet(OpCode.JMP, None, None, label_operand("fib_end"))
        translator.emit_instructions(translator.translate(jmp))

        # LABEL fib_base
        base = Triplet(OpCode.LABEL, label_operand("fib_base"), None, None)
        translator.emit_instructions(translator.translate(base))

        # MOV result, n
        mov = Triplet(OpCode.MOV, var_operand("n"), None, var_operand("result"))
        translator.emit_instructions(translator.translate(mov))

        # LABEL fib_end
        end = Triplet(OpCode.LABEL, label_operand("fib_end"), None, None)
        translator.emit_instructions(translator.translate(end))

        # RETURN result
        ret = Triplet(OpCode.RETURN, var_operand("result"), None, None)
        translator.emit_instructions(translator.translate(ret))

        # EXIT
        exit_op = Triplet(OpCode.EXIT, func_operand("fib"), None, None)
        translator.emit_instructions(translator.translate(exit_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Debe haber dos llamadas recursivas
        call_count = sum(1 for instr in instructions if instr.opcode == "jal")
        assert call_count >= 2


class TestNestedFunctions:
    """Tests para funciones anidadas/llamadas anidadas"""

    def test_nested_function_calls(self):
        """Test llamadas de función anidadas"""
        translator = MIPSTranslator()

        # Simulación: f(g(x))
        # Cargar x
        mov_x = Triplet(OpCode.MOV, var_operand("x"), None, var_operand("x"))
        translator.emit_instructions(translator.translate(mov_x))

        # PARAM x
        param_g = Triplet(OpCode.PARAM, var_operand("x"), None, None)
        translator.emit_instructions(translator.translate(param_g))

        # CALL g -> result_g
        call_g = Triplet(OpCode.CALL, func_operand("g"), const_operand(1), temp_operand("result_g"))
        translator.emit_instructions(translator.translate(call_g))

        # PARAM result_g
        param_f = Triplet(OpCode.PARAM, temp_operand("result_g"), None, None)
        translator.emit_instructions(translator.translate(param_f))

        # CALL f -> result_f
        call_f = Triplet(OpCode.CALL, func_operand("f"), const_operand(1), var_operand("result"))
        translator.emit_instructions(translator.translate(call_f))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Debe haber dos llamadas (g y f)
        call_count = sum(1 for instr in instructions if instr.opcode == "jal")
        assert call_count == 2

    def test_three_level_nesting(self):
        """Test anidamiento de 3 niveles: h(g(f(x)))"""
        translator = MIPSTranslator()

        # CALL f(x)
        param_f = Triplet(OpCode.PARAM, var_operand("x"), None, None)
        translator.emit_instructions(translator.translate(param_f))

        call_f = Triplet(OpCode.CALL, func_operand("f"), const_operand(1), temp_operand("t_f"))
        translator.emit_instructions(translator.translate(call_f))

        # CALL g(t_f)
        param_g = Triplet(OpCode.PARAM, temp_operand("t_f"), None, None)
        translator.emit_instructions(translator.translate(param_g))

        call_g = Triplet(OpCode.CALL, func_operand("g"), const_operand(1), temp_operand("t_g"))
        translator.emit_instructions(translator.translate(call_g))

        # CALL h(t_g)
        param_h = Triplet(OpCode.PARAM, temp_operand("t_g"), None, None)
        translator.emit_instructions(translator.translate(param_h))

        call_h = Triplet(OpCode.CALL, func_operand("h"), const_operand(1), var_operand("result"))
        translator.emit_instructions(translator.translate(call_h))

        instructions = translator.get_instructions()
        # Debe haber 3 llamadas
        call_count = sum(1 for instr in instructions if instr.opcode == "jal")
        assert call_count == 3

    def test_multiple_function_sequence(self):
        """Test secuencia de múltiples funciones"""
        translator = MIPSTranslator()

        functions = ["func1", "func2", "func3"]

        for func in functions:
            # ENTER
            enter = Triplet(OpCode.ENTER, func_operand(func), const_operand(0), None)
            translator.emit_instructions(translator.translate(enter))

            # ADD a + b
            add = Triplet(OpCode.ADD, var_operand("a"), var_operand("b"), var_operand("result"))
            translator.emit_instructions(translator.translate(add))

            # RETURN
            ret = Triplet(OpCode.RETURN, var_operand("result"), None, None)
            translator.emit_instructions(translator.translate(ret))

            # EXIT
            exit_op = Triplet(OpCode.EXIT, func_operand(func), None, None)
            translator.emit_instructions(translator.translate(exit_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Verificar que haya 3 funciones
        enter_count = sum(1 for instr in instructions if "Function:" in instr.comment if instr.comment)
        assert enter_count == 3


class TestLoops:
    """Tests para loops"""

    def test_simple_loop(self):
        """Test loop simple: for i=0 to n"""
        translator = MIPSTranslator()

        # MOV i, 0
        mov = Triplet(OpCode.MOV, const_operand(0), None, var_operand("i"))
        translator.emit_instructions(translator.translate(mov))

        # LABEL loop_start
        label_start = Triplet(OpCode.LABEL, label_operand("loop_start"), None, None)
        translator.emit_instructions(translator.translate(label_start))

        # BLT i, n, loop_end
        blt = Triplet(OpCode.BLT, var_operand("i"), var_operand("n"), label_operand("loop_end"))
        translator.emit_instructions(translator.translate(blt))

        # Cuerpo del loop (simulado)
        add = Triplet(OpCode.ADD, var_operand("sum"), var_operand("i"), var_operand("sum"))
        translator.emit_instructions(translator.translate(add))

        # i = i + 1
        inc = Triplet(OpCode.ADD, var_operand("i"), const_operand(1), var_operand("i"))
        translator.emit_instructions(translator.translate(inc))

        # JMP loop_start
        jmp = Triplet(OpCode.JMP, None, None, label_operand("loop_start"))
        translator.emit_instructions(translator.translate(jmp))

        # LABEL loop_end
        label_end = Triplet(OpCode.LABEL, label_operand("loop_end"), None, None)
        translator.emit_instructions(translator.translate(label_end))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Verificar que hay branch y jump
        opcodes = [instr.opcode for instr in instructions]
        # BLT es pseudo-instrucción que se expande a slt + bne
        assert "slt" in opcodes
        assert "bne" in opcodes
        assert "j" in opcodes

    def test_nested_loops(self):
        """Test loops anidados"""
        translator = MIPSTranslator()

        # Outer loop: i = 0 to m
        mov_i = Triplet(OpCode.MOV, const_operand(0), None, var_operand("i"))
        translator.emit_instructions(translator.translate(mov_i))

        label_outer = Triplet(OpCode.LABEL, label_operand("outer_loop"), None, None)
        translator.emit_instructions(translator.translate(label_outer))

        blt_outer = Triplet(OpCode.BLT, var_operand("i"), var_operand("m"), label_operand("outer_end"))
        translator.emit_instructions(translator.translate(blt_outer))

        # Inner loop: j = 0 to n
        mov_j = Triplet(OpCode.MOV, const_operand(0), None, var_operand("j"))
        translator.emit_instructions(translator.translate(mov_j))

        label_inner = Triplet(OpCode.LABEL, label_operand("inner_loop"), None, None)
        translator.emit_instructions(translator.translate(label_inner))

        blt_inner = Triplet(OpCode.BLT, var_operand("j"), var_operand("n"), label_operand("inner_end"))
        translator.emit_instructions(translator.translate(blt_inner))

        # Cuerpo
        add = Triplet(OpCode.ADD, var_operand("sum"), var_operand("sum"), var_operand("sum"))
        translator.emit_instructions(translator.translate(add))

        inc_j = Triplet(OpCode.ADD, var_operand("j"), const_operand(1), var_operand("j"))
        translator.emit_instructions(translator.translate(inc_j))

        jmp_inner = Triplet(OpCode.JMP, None, None, label_operand("inner_loop"))
        translator.emit_instructions(translator.translate(jmp_inner))

        label_inner_end = Triplet(OpCode.LABEL, label_operand("inner_end"), None, None)
        translator.emit_instructions(translator.translate(label_inner_end))

        # Fin loop interior
        inc_i = Triplet(OpCode.ADD, var_operand("i"), const_operand(1), var_operand("i"))
        translator.emit_instructions(translator.translate(inc_i))

        jmp_outer = Triplet(OpCode.JMP, None, None, label_operand("outer_loop"))
        translator.emit_instructions(translator.translate(jmp_outer))

        label_outer_end = Triplet(OpCode.LABEL, label_operand("outer_end"), None, None)
        translator.emit_instructions(translator.translate(label_outer_end))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        # Verificar que hay múltiples labels y jumps
        label_count = sum(1 for instr in instructions if ":" in str(instr))
        jmp_count = sum(1 for instr in instructions if instr.opcode == "j")
        assert label_count >= 4  # outer, inner, inner_end, outer_end
        assert jmp_count >= 2    # jump al inner, jump al outer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

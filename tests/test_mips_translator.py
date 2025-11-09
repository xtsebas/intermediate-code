"""
Tests para MIPSTranslator.

Prueba:
- Traducción de operaciones aritméticas
- Traducción de operaciones lógicas
- Traducción de comparaciones
- Traducción de MOV y asignaciones
- Casos complejos con múltiples operaciones
"""

import pytest
from compiler.ir.triplet import (
    Triplet, OpCode, Operand,
    temp_operand, var_operand, const_operand, label_operand
)
from compiler.codegen.mips_translator import MIPSTranslator, MIPSInstruction


class TestMIPSInstructionBasics:
    """Tests básicos para MIPSInstruction"""

    def test_instruction_creation(self):
        """Test creación de instrucción MIPS"""
        instr = MIPSInstruction("addu", ["$t0", "$t1", "$t2"])
        assert instr.opcode == "addu"
        assert len(instr.args) == 3

    def test_instruction_with_comment(self):
        """Test instrucción con comentario"""
        instr = MIPSInstruction("addu", ["$t0", "$t1", "$t2"], "Addition")
        assert instr.comment == "Addition"
        assert "Addition" in str(instr)

    def test_instruction_without_args(self):
        """Test instrucción sin argumentos"""
        instr = MIPSInstruction("nop")
        assert instr.args == []
        assert str(instr) == "nop"

    def test_instruction_string_format(self):
        """Test formato string de instrucción"""
        instr = MIPSInstruction("addu", ["$t0", "$t1", "$t2"], "Add")
        result = str(instr)
        assert "addu" in result
        assert "$t0" in result


class TestTranslatorInitialization:
    """Tests para inicialización del traductor"""

    def test_translator_creation(self):
        """Test creación del traductor"""
        translator = MIPSTranslator()
        assert translator is not None
        assert len(translator.instructions) == 0

    def test_translator_with_saved_regs(self):
        """Test traductor con registros salvados"""
        translator = MIPSTranslator(use_saved_regs=True)
        assert translator.register_pool.use_saved_regs == True

    def test_translator_without_saved_regs(self):
        """Test traductor sin registros salvados"""
        translator = MIPSTranslator(use_saved_regs=False)
        assert translator.register_pool.use_saved_regs == False


class TestArithmeticTranslation:
    """Tests para traducción de operaciones aritméticas"""

    def test_add_translation(self):
        """Test traducción de ADD"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ADD,
            var_operand("a"),
            var_operand("b"),
            var_operand("c"),
            "a + b"
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # Verificar que contiene una instrucción addu
        opcodes = [instr.opcode for instr in instructions]
        assert "addu" in opcodes

    def test_sub_translation(self):
        """Test traducción de SUB"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.SUB,
            var_operand("a"),
            var_operand("b"),
            var_operand("c"),
            "a - b"
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "subu" in opcodes

    def test_mul_translation(self):
        """Test traducción de MUL"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MUL,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "mult" in opcodes
        assert "mflo" in opcodes

    def test_div_translation(self):
        """Test traducción de DIV"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.DIV,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "div" in opcodes
        assert "mflo" in opcodes

    def test_mod_translation(self):
        """Test traducción de MOD"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOD,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "div" in opcodes
        assert "mfhi" in opcodes

    def test_neg_translation(self):
        """Test traducción de NEG"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.NEG,
            var_operand("a"),
            None,
            var_operand("b")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "subu" in opcodes


class TestLogicalTranslation:
    """Tests para traducción de operaciones lógicas"""

    def test_and_translation(self):
        """Test traducción de AND"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.AND,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "and" in opcodes

    def test_or_translation(self):
        """Test traducción de OR"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.OR,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "or" in opcodes

    def test_not_translation(self):
        """Test traducción de NOT"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.NOT,
            var_operand("a"),
            None,
            var_operand("b")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "nor" in opcodes


class TestComparisonTranslation:
    """Tests para traducción de comparaciones"""

    def test_eq_translation(self):
        """Test traducción de EQ (igualdad)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.EQ,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "subu" in opcodes  # Restar para comparación
        assert "nor" in opcodes   # NOT para resultado

    def test_ne_translation(self):
        """Test traducción de NE (desigualdad)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.NE,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "subu" in opcodes
        assert "sltu" in opcodes

    def test_lt_translation(self):
        """Test traducción de LT (menor que)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.LT,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes

    def test_le_translation(self):
        """Test traducción de LE (menor o igual)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.LE,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes
        assert "nor" in opcodes

    def test_gt_translation(self):
        """Test traducción de GT (mayor que)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.GT,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes

    def test_ge_translation(self):
        """Test traducción de GE (mayor o igual)"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.GE,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "slt" in opcodes
        assert "nor" in opcodes


class TestMOVTranslation:
    """Tests para traducción de MOV y asignaciones"""

    def test_mov_variable_translation(self):
        """Test traducción de MOV con variable"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            var_operand("a"),
            None,
            var_operand("b")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        assert "addu" in opcodes or "lw" in opcodes

    def test_mov_constant_translation(self):
        """Test traducción de MOV con constante"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            const_operand(42),
            None,
            var_operand("x")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # Debe contener addiu para cargar constante
        opcodes = [instr.opcode for instr in instructions]
        assert "addiu" in opcodes

    def test_mov_constant_to_register(self):
        """Test MOV de constante a registro"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            const_operand(100),
            None,
            temp_operand("t0")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # Debe usar addiu para cargar la constante
        instr_str = str(instructions[0])
        assert "addiu" in instr_str or "100" in instr_str


class TestLabelTranslation:
    """Tests para traducción de etiquetas"""

    def test_label_translation(self):
        """Test traducción de LABEL"""
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


class TestComplexExpressions:
    """Tests para casos complejos con múltiples operaciones"""

    def test_expression_a_plus_b_times_c(self):
        """Test: a + (b * c)"""
        translator = MIPSTranslator()

        # b * c
        mul_triplet = Triplet(
            OpCode.MUL,
            var_operand("b"),
            var_operand("c"),
            temp_operand("t0")
        )

        # a + t0
        add_triplet = Triplet(
            OpCode.ADD,
            var_operand("a"),
            temp_operand("t0"),
            var_operand("result")
        )

        translator.emit_instructions(translator.translate(mul_triplet))
        translator.emit_instructions(translator.translate(add_triplet))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_expression_with_comparison(self):
        """Test: result = (a < b) + 1"""
        translator = MIPSTranslator()

        # a < b
        cmp_triplet = Triplet(
            OpCode.LT,
            var_operand("a"),
            var_operand("b"),
            temp_operand("cmp_result")
        )

        # cmp_result + 1
        add_triplet = Triplet(
            OpCode.ADD,
            temp_operand("cmp_result"),
            const_operand(1),
            var_operand("result")
        )

        translator.emit_instructions(translator.translate(cmp_triplet))
        translator.emit_instructions(translator.translate(add_triplet))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_complex_expression_chain(self):
        """Test cadena compleja: ((a + b) * (c - d)) / e"""
        translator = MIPSTranslator()

        # a + b
        add1 = Triplet(OpCode.ADD, var_operand("a"), var_operand("b"), temp_operand("t1"))
        # c - d
        sub = Triplet(OpCode.SUB, var_operand("c"), var_operand("d"), temp_operand("t2"))
        # t1 * t2
        mul = Triplet(OpCode.MUL, temp_operand("t1"), temp_operand("t2"), temp_operand("t3"))
        # t3 / e
        div = Triplet(OpCode.DIV, temp_operand("t3"), var_operand("e"), var_operand("result"))

        translator.emit_instructions(translator.translate(add1))
        translator.emit_instructions(translator.translate(sub))
        translator.emit_instructions(translator.translate(mul))
        translator.emit_instructions(translator.translate(div))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        assert len(instructions) >= 4  # Al menos una instrucción por operación

    def test_logical_expression(self):
        """Test: result = (a & b) | (c & d)"""
        translator = MIPSTranslator()

        # a & b
        and1 = Triplet(OpCode.AND, var_operand("a"), var_operand("b"), temp_operand("t1"))
        # c & d
        and2 = Triplet(OpCode.AND, var_operand("c"), var_operand("d"), temp_operand("t2"))
        # t1 | t2
        or_op = Triplet(OpCode.OR, temp_operand("t1"), temp_operand("t2"), var_operand("result"))

        translator.emit_instructions(translator.translate(and1))
        translator.emit_instructions(translator.translate(and2))
        translator.emit_instructions(translator.translate(or_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_all_comparisons_sequence(self):
        """Test secuencia de todas las comparaciones"""
        translator = MIPSTranslator()

        comparisons = [
            (OpCode.EQ, "a == b"),
            (OpCode.NE, "a != b"),
            (OpCode.LT, "a < b"),
            (OpCode.LE, "a <= b"),
            (OpCode.GT, "a > b"),
            (OpCode.GE, "a >= b"),
        ]

        for i, (op, desc) in enumerate(comparisons):
            triplet = Triplet(
                op,
                var_operand("a"),
                var_operand("b"),
                temp_operand(f"cmp{i}"),
                desc
            )
            translator.emit_instructions(translator.translate(triplet))

        instructions = translator.get_instructions()
        assert len(instructions) > 0
        assert len(instructions) >= 6  # Al menos una instrucción por comparación


class TestTranslatorState:
    """Tests para estado del traductor"""

    def test_get_instructions(self):
        """Test obtención de instrucciones"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ADD,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        translator.emit_instructions(translator.translate(triplet))
        instructions = translator.get_instructions()

        assert len(instructions) > 0
        assert all(isinstance(instr, MIPSInstruction) for instr in instructions)

    def test_get_assembly(self):
        """Test obtención de código assembly"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ADD,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        translator.emit_instructions(translator.translate(triplet))
        assembly = translator.get_assembly()

        assert isinstance(assembly, str)
        assert len(assembly) > 0

    def test_reset(self):
        """Test reinicio del traductor"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ADD,
            var_operand("a"),
            var_operand("b"),
            var_operand("c")
        )

        translator.emit_instructions(translator.translate(triplet))
        assert len(translator.instructions) > 0

        translator.reset()
        assert len(translator.instructions) == 0
        assert len(translator.operand_to_register) == 0

    def test_translator_str(self):
        """Test representación en string del traductor"""
        translator = MIPSTranslator()
        str_rep = str(translator)
        assert "MIPSTranslator" in str_rep


class TestEdgeCases:
    """Tests para casos especiales"""

    def test_zero_operand(self):
        """Test con constante cero"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            const_operand(0),
            None,
            var_operand("x")
        )

        instructions = translator.translate(triplet)
        assert len(instructions) > 0

    def test_negative_constant(self):
        """Test con constante negativa"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            const_operand(-42),
            None,
            var_operand("x")
        )

        instructions = translator.translate(triplet)
        assert len(instructions) > 0

    def test_large_constant(self):
        """Test con constante grande"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.MOV,
            const_operand(100000),
            None,
            var_operand("x")
        )

        instructions = translator.translate(triplet)
        assert len(instructions) > 0

    def test_multiple_operations_same_variable(self):
        """Test múltiples operaciones con la misma variable"""
        translator = MIPSTranslator()

        # a = b + c
        op1 = Triplet(OpCode.ADD, var_operand("b"), var_operand("c"), var_operand("a"))
        # a = a + b
        op2 = Triplet(OpCode.ADD, var_operand("a"), var_operand("b"), var_operand("a"))

        translator.emit_instructions(translator.translate(op1))
        translator.emit_instructions(translator.translate(op2))

        instructions = translator.get_instructions()
        assert len(instructions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

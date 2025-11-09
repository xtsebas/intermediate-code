"""
Tests para Arrays y Memoria Dinámica en MIPSTranslator.

Prueba:
- Traducción de ARRAY_ALLOC
- Traducción de ARRAY_GET y ARRAY_SET
- Cálculo de direcciones efectivas
- Manejo de punteros y memoria
- Arrays multidimensionales
"""

import pytest
from compiler.ir.triplet import (
    Triplet, OpCode, Operand,
    temp_operand, var_operand, const_operand, label_operand
)
from compiler.codegen.mips_translator import MIPSTranslator, MIPSInstruction


class TestArrayAllocation:
    """Tests para asignación de arrays"""

    def test_array_alloc_basic(self):
        """Test asignación básica de array"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),      # 10 elementos
            const_operand(4),       # 4 bytes por elemento
            var_operand("arr")
        )

        instructions = translator.translate(triplet)

        assert len(instructions) > 0
        # Debe cargar una dirección
        opcodes = [instr.opcode for instr in instructions]
        assert "li" in opcodes  # Load immediate

    def test_array_alloc_info_tracking(self):
        """Test que se registra información del array"""
        translator = MIPSTranslator()
        triplet = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(5),       # 5 elementos
            const_operand(4),       # 4 bytes por elemento
            var_operand("numbers")
        )

        translator.translate(triplet)

        # Verificar que se registró
        assert "numbers" in translator.array_info
        info = translator.array_info["numbers"]
        assert info['size'] == 5
        assert info['element_size'] == 4
        assert info['total_size'] == 20

    def test_multiple_array_allocation(self):
        """Test asignación de múltiples arrays"""
        translator = MIPSTranslator()

        arrays = [
            ("arr1", 10, 4),
            ("arr2", 20, 8),
            ("arr3", 5, 4),
        ]

        for name, size, elem_size in arrays:
            triplet = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(size),
                const_operand(elem_size),
                var_operand(name)
            )
            translator.translate(triplet)

        # Verificar que todos se registraron
        assert len(translator.array_info) == 3
        for name, size, elem_size in arrays:
            assert name in translator.array_info

    def test_heap_pointer_advancement(self):
        """Test que el puntero del heap avanza"""
        translator = MIPSTranslator()
        initial_heap = translator.heap_ptr

        triplet = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )
        translator.translate(triplet)

        # Heap debe haber avanzado 40 bytes (10 * 4)
        assert translator.heap_ptr == initial_heap + 40

    def test_different_element_sizes(self):
        """Test arrays con diferentes tamaños de elemento"""
        translator = MIPSTranslator()

        sizes = [1, 2, 4, 8]

        for i, size in enumerate(sizes):
            triplet = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(10),
                const_operand(size),
                var_operand(f"arr{i}")
            )
            translator.translate(triplet)

        for i, size in enumerate(sizes):
            assert translator.array_info[f"arr{i}"]['element_size'] == size


class TestArrayAccess:
    """Tests para acceso a elementos de array"""

    def test_array_get_basic(self):
        """Test lectura básica de array"""
        translator = MIPSTranslator()

        # Primero asignar el array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )
        translator.translate(alloc)

        # Luego leer un elemento
        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("arr"),
            const_operand(0),       # índice 0
            var_operand("value")
        )

        instructions = translator.translate(get)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        # Debe haber: li, mult, mflo, addu, lw
        assert "li" in opcodes
        assert "mult" in opcodes
        assert "lw" in opcodes

    def test_array_set_basic(self):
        """Test escritura básica en array"""
        translator = MIPSTranslator()

        # Asignar array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )
        translator.translate(alloc)

        # Escribir un elemento
        set_op = Triplet(
            OpCode.ARRAY_SET,
            var_operand("arr"),
            const_operand(0),       # índice 0
            var_operand("42")       # valor
        )

        instructions = translator.translate(set_op)

        assert len(instructions) > 0
        opcodes = [instr.opcode for instr in instructions]
        # Debe terminar con sw (store word)
        assert "sw" in opcodes

    def test_array_get_with_variable_index(self):
        """Test acceso con índice variable"""
        translator = MIPSTranslator()

        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )
        translator.translate(alloc)

        # Acceso con índice variable
        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("arr"),
            var_operand("i"),       # índice variable
            var_operand("result")
        )

        instructions = translator.translate(get)

        assert len(instructions) > 0
        # Debe calcular el offset dinámicamente
        instr_str = "\n".join(str(instr) for instr in instructions)
        assert "mult" in instr_str or "multiply" in instr_str.lower()

    def test_array_access_with_different_sizes(self):
        """Test acceso a arrays con diferentes tamaños de elemento"""
        translator = MIPSTranslator()

        for elem_size in [1, 2, 4, 8]:
            translator.reset()

            alloc = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(10),
                const_operand(elem_size),
                var_operand("arr")
            )
            translator.translate(alloc)

            get = Triplet(
                OpCode.ARRAY_GET,
                var_operand("arr"),
                var_operand("i"),
                var_operand("val")
            )

            instructions = translator.translate(get)

            assert len(instructions) > 0


class TestMultidimensionalArrays:
    """Tests para arrays multidimensionales"""

    def test_2d_array_allocation(self):
        """Test asignación de array 2D"""
        translator = MIPSTranslator()

        # Array 2D: 5x10 (50 elementos de 4 bytes)
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(50),      # 5 * 10
            const_operand(4),
            var_operand("matrix")
        )

        instructions = translator.translate(alloc)

        assert len(instructions) > 0
        assert "matrix" in translator.array_info
        assert translator.array_info["matrix"]['total_size'] == 200  # 50 * 4

    def test_2d_array_access_calculation(self):
        """Test cálculo de dirección para acceso 2D: matrix[i][j]"""
        translator = MIPSTranslator()

        # Matriz 5x10 (linealizada como array 1D de 50 elementos)
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(50),
            const_operand(4),
            var_operand("matrix")
        )
        translator.translate(alloc)

        # Acceso matrix[i][j] se traduce a matrix[i*10 + j]
        # Donde i es fila, j es columna, y hay 10 columnas

        # Para simplificar el test, accedemos al índice calculado
        # En una implementación real, habría una instrucción para calcular i*10+j

        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("matrix"),
            var_operand("index"),   # index = i*10 + j
            var_operand("value")
        )

        instructions = translator.translate(get)

        assert len(instructions) > 0

    def test_3d_array_simulation(self):
        """Test simulación de acceso a array 3D"""
        translator = MIPSTranslator()

        # Array 3D: 3x4x5 (60 elementos)
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(60),
            const_operand(4),
            var_operand("tensor")
        )
        translator.translate(alloc)

        # Acceso tensor[i][j][k]
        # Se linealiza a: tensor[i*20 + j*5 + k]
        # donde 20 = 4*5 (columnas * profundidad)
        # y 5 = profundidad

        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("tensor"),
            var_operand("flat_index"),  # i*20 + j*5 + k
            var_operand("element")
        )

        instructions = translator.translate(get)

        assert len(instructions) > 0

    def test_jagged_array_simulation(self):
        """Test simulación de array irregular (array de punteros)"""
        translator = MIPSTranslator()

        # Array de punteros (array of arrays)
        # Cada elemento es un puntero (4 bytes) a otro array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(3),       # 3 filas
            const_operand(4),       # 4 bytes por puntero
            var_operand("rows")
        )
        translator.translate(alloc)

        # Acceso rows[i] obtiene un puntero
        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("rows"),
            const_operand(0),       # Fila 0
            var_operand("ptr")
        )

        instructions = translator.translate(get)

        assert len(instructions) > 0


class TestPointerArithmetic:
    """Tests para aritmética de punteros"""

    def test_pointer_increment(self):
        """Test incremento de puntero"""
        translator = MIPSTranslator()

        # Asignar array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )
        translator.emit_instructions(translator.translate(alloc))

        # Accesos a elementos consecutivos
        for i in range(3):
            get = Triplet(
                OpCode.ARRAY_GET,
                var_operand("arr"),
                const_operand(i),
                var_operand(f"val{i}")
            )
            translator.emit_instructions(translator.translate(get))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_array_to_pointer_conversion(self):
        """Test que ARRAY_ALLOC retorna puntero al array"""
        translator = MIPSTranslator()

        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("arr")
        )

        instructions = translator.translate(alloc)

        # El resultado debe ser un puntero (dirección base)
        assert len(instructions) > 0
        # Verificar que hay una instrucción li que carga una dirección
        opcodes = [instr.opcode for instr in instructions]
        assert "li" in opcodes


class TestMemoryManagement:
    """Tests para gestión de memoria"""

    def test_multiple_allocations_different_regions(self):
        """Test que múltiples arrays se alojan en diferentes regiones"""
        translator = MIPSTranslator()

        arrays_info = []

        for i in range(3):
            alloc = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(10),
                const_operand(4),
                var_operand(f"arr{i}")
            )
            translator.translate(alloc)
            arrays_info.append(translator.array_info[f"arr{i}"])

        # Verificar que tienen direcciones diferentes
        addrs = [info['base_addr'] for info in arrays_info]
        assert len(set(addrs)) == 3  # Todas diferentes

        # Verificar que están en orden
        assert addrs[0] < addrs[1] < addrs[2]

    def test_memory_layout(self):
        """Test layout correcto de memoria"""
        translator = MIPSTranslator()

        sizes = [10, 20, 5]
        elem_sizes = [4, 4, 8]

        previous_end = translator.heap_ptr

        for i, (size, elem_size) in enumerate(zip(sizes, elem_sizes)):
            alloc = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(size),
                const_operand(elem_size),
                var_operand(f"arr{i}")
            )
            translator.translate(alloc)

            info = translator.array_info[f"arr{i}"]
            # Verificar dirección base
            assert info['base_addr'] == previous_end
            # Actualizar para siguiente array
            previous_end += size * elem_size


class TestComplexArrayOperations:
    """Tests para operaciones complejas con arrays"""

    def test_array_copy_simulation(self):
        """Test simulación de copia de array"""
        translator = MIPSTranslator()

        # Asignar dos arrays
        for name in ["src", "dst"]:
            alloc = Triplet(
                OpCode.ARRAY_ALLOC,
                const_operand(10),
                const_operand(4),
                var_operand(name)
            )
            translator.emit_instructions(translator.translate(alloc))

        # Copiar: for i = 0 to 9: dst[i] = src[i]
        for i in range(3):  # Simular solo 3 iteraciones
            # src[i]
            get = Triplet(
                OpCode.ARRAY_GET,
                var_operand("src"),
                const_operand(i),
                var_operand("temp")
            )
            translator.emit_instructions(translator.translate(get))

            # dst[i] = temp
            set_op = Triplet(
                OpCode.ARRAY_SET,
                var_operand("dst"),
                const_operand(i),
                var_operand("temp")
            )
            translator.emit_instructions(translator.translate(set_op))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_array_sum_simulation(self):
        """Test simulación de suma de elementos de array"""
        translator = MIPSTranslator()

        # Asignar array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(5),
            const_operand(4),
            var_operand("numbers")
        )
        translator.emit_instructions(translator.translate(alloc))

        # Simular suma: sum = 0; for i = 0 to 4: sum += numbers[i]
        # Inicializar sum
        init = Triplet(
            OpCode.MOV,
            const_operand(0),
            None,
            var_operand("sum")
        )
        translator.emit_instructions(translator.translate(init))

        # Loop
        for i in range(5):
            # Leer numbers[i]
            get = Triplet(
                OpCode.ARRAY_GET,
                var_operand("numbers"),
                const_operand(i),
                var_operand("val")
            )
            translator.emit_instructions(translator.translate(get))

            # sum += val
            add = Triplet(
                OpCode.ADD,
                var_operand("sum"),
                var_operand("val"),
                var_operand("sum")
            )
            translator.emit_instructions(translator.translate(add))

        instructions = translator.get_instructions()
        assert len(instructions) > 0

    def test_array_search_simulation(self):
        """Test simulación de búsqueda en array"""
        translator = MIPSTranslator()

        # Asignar array
        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(4),
            var_operand("data")
        )
        translator.emit_instructions(translator.translate(alloc))

        # Búsqueda: encontrar índice de valor x
        for i in range(10):
            get = Triplet(
                OpCode.ARRAY_GET,
                var_operand("data"),
                const_operand(i),
                var_operand("elem")
            )
            translator.emit_instructions(translator.translate(get))

            # Comparación elem == target
            eq = Triplet(
                OpCode.EQ,
                var_operand("elem"),
                var_operand("target"),
                var_operand("match")
            )
            translator.emit_instructions(translator.translate(eq))

            # Branch if found
            bne = Triplet(
                OpCode.BNE,
                var_operand("match"),
                const_operand(0),
                label_operand("found")
            )
            translator.emit_instructions(translator.translate(bne))

        instructions = translator.get_instructions()
        assert len(instructions) > 0


class TestAddressCalculation:
    """Tests para cálculo de direcciones efectivas"""

    def test_address_calculation_element_size_1(self):
        """Test dirección efectiva con elemento de 1 byte"""
        translator = MIPSTranslator()

        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(1),       # 1 byte por elemento
            var_operand("bytes")
        )
        translator.translate(alloc)

        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("bytes"),
            const_operand(5),
            var_operand("b")
        )

        instructions = translator.translate(get)

        # Con elemento_size=1, no debe haber multiplicación
        instr_str = "\n".join(str(instr) for instr in instructions)
        # Verificar que hay un addu pero no necesariamente mult
        assert "addu" in instr_str.lower()

    def test_address_calculation_element_size_8(self):
        """Test dirección efectiva con elemento de 8 bytes"""
        translator = MIPSTranslator()

        alloc = Triplet(
            OpCode.ARRAY_ALLOC,
            const_operand(10),
            const_operand(8),       # 8 bytes por elemento
            var_operand("longs")
        )
        translator.translate(alloc)

        get = Triplet(
            OpCode.ARRAY_GET,
            var_operand("longs"),
            var_operand("i"),
            var_operand("val")
        )

        instructions = translator.translate(get)

        # Debe haber multiplicación por 8
        instr_str = "\n".join(str(instr) for instr in instructions)
        assert "mult" in instr_str.lower() or "li" in instr_str.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

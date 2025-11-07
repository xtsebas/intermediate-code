import pytest
from compiler.codegen.stack_manager import (
    StackManager, RegisterType, RegisterClass, MipsRegister,
    RegisterAllocator, StackFrameLayout
)


class TestMipsRegister:
    """Tests para la clase MipsRegister"""

    def test_register_creation(self):
        """Verifica que se cree un registro correctamente"""
        reg = MipsRegister(
            reg_type=RegisterType.T0,
            reg_number=8,
            reg_class=RegisterClass.TEMPORARY,
            is_caller_saved=True,
            is_callee_saved=False
        )
        assert reg.reg_type == RegisterType.T0
        assert reg.reg_number == 8
        assert reg.is_caller_saved is True
        assert reg.is_callee_saved is False

    def test_register_name(self):
        """Verifica el nombre del registro con símbolo $"""
        reg = MipsRegister(
            reg_type=RegisterType.V0,
            reg_number=2,
            reg_class=RegisterClass.RETURN,
            is_caller_saved=True,
            is_callee_saved=False
        )
        assert reg.name == "$v0"
        assert reg.number_name == "$2"

    def test_register_string_representation(self):
        """Verifica la representación string del registro"""
        reg = MipsRegister(
            reg_type=RegisterType.S0,
            reg_number=16,
            reg_class=RegisterClass.SAVED,
            is_caller_saved=False,
            is_callee_saved=True
        )
        assert str(reg) == "$s0"
        assert "S0" in repr(reg)


class TestRegisterAllocator:
    """Tests para RegisterAllocator"""

    def test_allocator_initialization(self):
        """Verifica que el asignador se inicialice correctamente"""
        allocator = RegisterAllocator()
        assert len(allocator.temp_registers) == 10  # t0-t7, t8-t9
        assert allocator.free_count() == 10

    def test_allocate_register(self):
        """Verifica la asignación de registros"""
        allocator = RegisterAllocator()
        reg = allocator.allocate("var1")
        assert reg is not None
        assert allocator.is_allocated("var1")
        assert allocator.get_register("var1") == reg
        assert allocator.free_count() == 9

    def test_allocate_multiple_registers(self):
        """Verifica la asignación de múltiples registros"""
        allocator = RegisterAllocator()
        regs = []
        for i in range(5):
            reg = allocator.allocate(f"var{i}")
            assert reg is not None
            regs.append(reg)

        assert allocator.free_count() == 5
        # Verificar que son registros diferentes
        assert len(set(regs)) == 5

    def test_allocate_all_registers(self):
        """Verifica el comportamiento cuando se agotan los registros"""
        allocator = RegisterAllocator()
        for i in range(10):
            allocator.allocate(f"var{i}")

        # Intentar asignar otro debe retornar None
        reg = allocator.allocate("var10")
        assert reg is None
        assert allocator.free_count() == 0

    def test_deallocate_register(self):
        """Verifica la liberación de registros"""
        allocator = RegisterAllocator()
        allocator.allocate("var1")
        assert allocator.free_count() == 9

        success = allocator.deallocate("var1")
        assert success is True
        assert allocator.free_count() == 10
        assert not allocator.is_allocated("var1")

    def test_deallocate_nonexistent_register(self):
        """Verifica la liberación de registros inexistentes"""
        allocator = RegisterAllocator()
        success = allocator.deallocate("nonexistent")
        assert success is False

    def test_allocator_reset(self):
        """Verifica el reinicio del asignador"""
        allocator = RegisterAllocator()
        allocator.allocate("var1")
        allocator.allocate("var2")
        assert allocator.free_count() == 8

        allocator.reset()
        assert allocator.free_count() == 10
        assert len(allocator.allocated_temps) == 0


class TestStackFrameLayout:
    """Tests para StackFrameLayout"""

    def test_frame_creation(self):
        """Verifica la creación de un frame"""
        frame = StackFrameLayout()
        assert frame.total_frame_size == 0

    def test_frame_size_calculation_no_locals(self):
        """Verifica el cálculo del tamaño sin variables locales"""
        frame = StackFrameLayout()
        frame.saved_regs_size = 32  # 8 registros * 4 bytes
        frame.locals_size = 0
        size = frame.calculate_total_size()

        assert size == 40  # 8 (RA + old FP) + 32 (saved regs)
        assert frame.total_frame_size == 40

    def test_frame_size_calculation_with_locals(self):
        """Verifica el cálculo del tamaño con variables locales"""
        frame = StackFrameLayout()
        frame.saved_regs_size = 32
        frame.locals_size = 24  # 6 variables locales
        size = frame.calculate_total_size()

        assert size == 64  # 8 + 32 + 24
        assert frame.total_frame_size == 64

    def test_frame_register_offset(self):
        """Verifica el cálculo de offset de registros guardados"""
        frame = StackFrameLayout()
        # Crear registros salvados
        saved_regs = []
        for i in range(3):
            reg = MipsRegister(
                reg_type=RegisterType.S0,
                reg_number=16 + i,
                reg_class=RegisterClass.SAVED,
                is_caller_saved=False,
                is_callee_saved=True
            )
            saved_regs.append(reg)

        frame.saved_reg_list = saved_regs
        frame.saved_regs_size = 12
        frame.locals_size = 0
        frame.calculate_total_size()

        # Verificar offsets
        offset_s0 = frame.get_register_offset(saved_regs[0])
        offset_s1 = frame.get_register_offset(saved_regs[1])
        offset_s2 = frame.get_register_offset(saved_regs[2])

        assert offset_s0 == -12
        assert offset_s1 == -16
        assert offset_s2 == -20


class TestStackManager:
    """Tests para StackManager"""

    def test_initialization(self):
        """Verifica la inicialización del StackManager"""
        manager = StackManager()
        assert manager.get_stack_depth() == 0
        assert manager.current_frame is None
        assert len(manager.callee_saved_regs) == 8  # s0-s7

    def test_push_frame(self):
        """Verifica la creación de un frame"""
        manager = StackManager()
        frame = manager.push_frame(param_count=2, local_var_count=3)

        assert manager.get_stack_depth() == 1
        assert manager.current_frame == frame
        assert frame.locals_size == 12  # 3 variables * 4 bytes

    def test_push_multiple_frames(self):
        """Verifica el manejo de múltiples frames (funciones anidadas)"""
        manager = StackManager()

        frame1 = manager.push_frame(param_count=2, local_var_count=2)
        assert manager.get_stack_depth() == 1

        frame2 = manager.push_frame(param_count=1, local_var_count=3)
        assert manager.get_stack_depth() == 2

        assert manager.current_frame == frame2
        assert manager.function_stack[0] == frame1

    def test_pop_frame(self):
        """Verifica la eliminación de un frame"""
        manager = StackManager()
        frame1 = manager.push_frame()
        frame2 = manager.push_frame()

        popped = manager.pop_frame()
        assert popped == frame2
        assert manager.get_stack_depth() == 1
        assert manager.current_frame == frame1

    def test_pop_frame_empty(self):
        """Verifica pop en stack vacío"""
        manager = StackManager()
        popped = manager.pop_frame()
        assert popped is None

    def test_get_current_frame(self):
        """Verifica obtención del frame actual"""
        manager = StackManager()
        assert manager.get_current_frame() is None

        frame = manager.push_frame()
        assert manager.get_current_frame() == frame

    # ========== PROLOGUE/EPILOGUE TESTS ==========

    def test_prologue_generation_empty_frame(self):
        """Verifica generación de prólogo con frame vacío"""
        manager = StackManager()
        manager.push_frame()

        instructions = manager.generate_prologue()

        assert len(instructions) > 0
        # Debe haber instrucciones de setup
        assert any("$fp" in instr for instr in instructions)
        assert any("$ra" in instr for instr in instructions)

    def test_prologue_generation_with_locals(self):
        """Verifica generación de prólogo con variables locales"""
        manager = StackManager()
        manager.push_frame(local_var_count=4)

        instructions = manager.generate_prologue()

        # Debe haber instrucción de allocate frame
        assert any("subu" in instr and "$sp" in instr for instr in instructions)
        # Debe guardar RA
        assert any("sw $ra" in instr for instr in instructions)
        # Debe establecer FP
        assert any("addu $fp" in instr for instr in instructions)

    def test_prologue_registers_saved(self):
        """Verifica que el prólogo guarde los registros correctos"""
        manager = StackManager()
        frame = manager.push_frame()
        manager.current_frame = frame

        instructions = manager.generate_prologue()

        # Debe guardar registros callee-saved (s0-s7)
        saved_count = sum(1 for instr in instructions if "sw $s" in instr)
        assert saved_count == 8  # 8 registros savedados

    def test_epilogue_generation(self):
        """Verifica generación de epílogo"""
        manager = StackManager()
        manager.push_frame()

        instructions = manager.generate_epilogue()

        assert len(instructions) > 0
        # Debe tener jr $ra
        assert any("jr $ra" in instr for instr in instructions)
        # Debe restaurar RA
        assert any("lw $ra" in instr for instr in instructions)
        # Debe restaurar registros
        assert any("lw $s" in instr for instr in instructions)

    def test_epilogue_symmetry_with_prologue(self):
        """Verifica que epílogo sea simétrico con prólogo"""
        manager = StackManager()
        manager.push_frame(local_var_count=3)

        prologue = manager.generate_prologue()
        epilogue = manager.generate_epilogue()

        # Mismo número de instrucciones aproximadamente
        assert len(epilogue) >= len(prologue) - 2

        # Las instrucciones de restore deben ser inversas a save
        saves = [i for i in prologue if " sw " in i]
        restores = [i for i in epilogue if " lw " in i]
        assert len(saves) == len(restores)

    def test_prologue_no_frame(self):
        """Verifica error si no hay frame activo"""
        manager = StackManager()
        with pytest.raises(RuntimeError):
            manager.generate_prologue()

    def test_epilogue_no_frame(self):
        """Verifica error si no hay frame activo"""
        manager = StackManager()
        with pytest.raises(RuntimeError):
            manager.generate_epilogue()

    # ========== CALLER/CALLEE TESTS ==========

    def test_caller_prologue_no_args(self):
        """Verifica prólogo del caller sin argumentos"""
        manager = StackManager()
        instructions = manager.generate_caller_prologue(arg_count=0)
        assert len(instructions) == 0

    def test_caller_prologue_with_extra_args(self):
        """Verifica prólogo del caller con más de 4 argumentos"""
        manager = StackManager()
        instructions = manager.generate_caller_prologue(arg_count=6)

        # Debe hacer espacio para 2 argumentos extras (6 - 4)
        assert len(instructions) > 0
        assert any("subu" in instr and "sp" in instr for instr in instructions)

    def test_caller_epilogue_no_args(self):
        """Verifica epílogo del caller sin argumentos"""
        manager = StackManager()
        instructions = manager.generate_caller_epilogue(arg_count=0)
        assert len(instructions) == 0

    def test_caller_epilogue_with_extra_args(self):
        """Verifica epílogo del caller con argumentos extra en stack"""
        manager = StackManager()
        instructions = manager.generate_caller_epilogue(arg_count=6)

        # Debe limpiar 2 argumentos extras
        assert len(instructions) > 0
        assert any("addu" in instr and "sp" in instr for instr in instructions)

    def test_caller_prologue_epilogue_symmetry(self):
        """Verifica simetría entre caller prologue y epilogue"""
        manager = StackManager()
        prologue = manager.generate_caller_prologue(arg_count=5)
        epilogue = manager.generate_caller_epilogue(arg_count=5)

        assert len(prologue) == len(epilogue)

    # ========== REGISTER PUSH/POP TESTS ==========

    def test_push_single_register(self):
        """Verifica push de un registro individual"""
        manager = StackManager()
        reg = manager.get_register_by_type(RegisterType.T0)
        instr = manager.push_register(reg, 0)

        assert "sw" in instr
        assert "$t0" in instr
        assert "$sp" in instr

    def test_push_zero_register(self):
        """Verifica que no se intente guardar $zero"""
        manager = StackManager()
        reg = manager.get_register_by_type(RegisterType.ZERO)
        instr = manager.push_register(reg, 0)

        assert "#" in instr  # Es un comentario
        assert "sw" not in instr

    def test_pop_single_register(self):
        """Verifica pop de un registro individual"""
        manager = StackManager()
        reg = manager.get_register_by_type(RegisterType.T1)
        instr = manager.pop_register(reg, 4)

        assert "lw" in instr
        assert "$t1" in instr
        assert "$sp" in instr

    def test_push_multiple_registers(self):
        """Verifica push de múltiples registros temporales"""
        manager = StackManager()
        regs = [
            manager.get_register_by_type(RegisterType.T0),
            manager.get_register_by_type(RegisterType.T1),
            manager.get_register_by_type(RegisterType.T2),
        ]
        instructions = manager.push_temp_registers(regs)

        assert len(instructions) > 0
        # Primera instrucción debe ser subu
        assert "subu" in instructions[0] and "$sp" in instructions[0]
        # Debe haber 3 instrucciones sw
        sw_count = sum(1 for instr in instructions if "sw" in instr)
        assert sw_count == 3
        # Última instrucción de push no debería tener pop
        assert not any("lw" in instr for instr in instructions)

    def test_pop_multiple_registers(self):
        """Verifica pop de múltiples registros temporales"""
        manager = StackManager()
        regs = [
            manager.get_register_by_type(RegisterType.T0),
            manager.get_register_by_type(RegisterType.T1),
            manager.get_register_by_type(RegisterType.T2),
        ]
        instructions = manager.pop_temp_registers(regs)

        assert len(instructions) > 0
        # Debe haber 3 instrucciones lw
        lw_count = sum(1 for instr in instructions if "lw" in instr)
        assert lw_count == 3
        # Última instrucción debe ser addu para liberar espacio
        assert "addu" in instructions[-1] and "$sp" in instructions[-1]

    def test_push_pop_empty_list(self):
        """Verifica push/pop con lista vacía"""
        manager = StackManager()
        push_instrs = manager.push_temp_registers([])
        pop_instrs = manager.pop_temp_registers([])

        assert len(push_instrs) == 0
        assert len(pop_instrs) == 0

    # ========== REGISTER CLASSIFICATION TESTS ==========

    def test_get_argument_registers(self):
        """Verifica obtención de registros de argumentos"""
        manager = StackManager()
        arg_regs = manager.get_argument_registers()

        assert len(arg_regs) == 4
        assert all(reg.reg_class == RegisterClass.ARGUMENT for reg in arg_regs)
        assert arg_regs[0].reg_type == RegisterType.A0
        assert arg_regs[3].reg_type == RegisterType.A3

    def test_get_return_registers(self):
        """Verifica obtención de registros de retorno"""
        manager = StackManager()
        ret_regs = manager.get_return_registers()

        assert len(ret_regs) == 2
        assert all(reg.reg_class == RegisterClass.RETURN for reg in ret_regs)
        assert ret_regs[0].reg_type == RegisterType.V0
        assert ret_regs[1].reg_type == RegisterType.V1

    def test_get_temporary_registers(self):
        """Verifica obtención de registros temporales"""
        manager = StackManager()
        temp_regs = manager.get_temporary_registers()

        assert len(temp_regs) == 10  # t0-t7, t8-t9
        assert all(reg.is_caller_saved for reg in temp_regs)
        assert all(not reg.is_callee_saved for reg in temp_regs)

    def test_get_saved_registers(self):
        """Verifica obtención de registros salvados"""
        manager = StackManager()
        saved_regs = manager.get_saved_registers()

        assert len(saved_regs) == 8  # s0-s7
        assert all(reg.is_callee_saved for reg in saved_regs)
        assert all(not reg.is_caller_saved for reg in saved_regs)

    def test_is_caller_saved(self):
        """Verifica clasificación de caller-saved"""
        manager = StackManager()
        t0 = manager.get_register_by_type(RegisterType.T0)
        s0 = manager.get_register_by_type(RegisterType.S0)

        assert manager.is_caller_saved(t0) is True
        assert manager.is_caller_saved(s0) is False

    def test_is_callee_saved(self):
        """Verifica clasificación de callee-saved"""
        manager = StackManager()
        t0 = manager.get_register_by_type(RegisterType.T0)
        s0 = manager.get_register_by_type(RegisterType.S0)

        assert manager.is_callee_saved(s0) is True
        assert manager.is_callee_saved(t0) is False

    # ========== UTILITY TESTS ==========

    def test_get_register_by_type(self):
        """Verifica obtención de registro por tipo"""
        manager = StackManager()
        reg = manager.get_register_by_type(RegisterType.V0)

        assert reg.reg_type == RegisterType.V0
        assert reg.reg_number == 2

    def test_register_map_completeness(self):
        """Verifica que todos los registros están mapeados"""
        manager = StackManager()

        # Debería haber 32 registros
        assert len(manager.register_map) == 32

        # Verificar registros clave
        assert RegisterType.ZERO in manager.register_map
        assert RegisterType.SP in manager.register_map
        assert RegisterType.RA in manager.register_map
        assert RegisterType.FP in manager.register_map

    def test_reset(self):
        """Verifica reinicio del manager"""
        manager = StackManager()
        manager.push_frame()
        manager.push_frame()
        manager.register_allocator.allocate("var1")

        manager.reset()

        assert manager.get_stack_depth() == 0
        assert manager.current_frame is None
        assert manager.register_allocator.free_count() == 10

    def test_string_representation(self):
        """Verifica la representación string del manager"""
        manager = StackManager()
        repr_empty = repr(manager)
        assert "StackManager" in repr_empty
        assert "depth=0" in repr_empty

        manager.push_frame()
        repr_with_frame = repr(manager)
        assert "depth=1" in repr_with_frame

    # ========== EDGE CASES AND INTEGRATION TESTS ==========

    def test_large_local_variables(self):
        """Verifica frame con muchas variables locales"""
        manager = StackManager()
        frame = manager.push_frame(local_var_count=100, local_var_size=4)

        assert frame.locals_size == 400
        assert frame.total_frame_size == 440  # 40 (default) + 400

    def test_deeply_nested_functions(self):
        """Verifica manejo de funciones profundamente anidadas"""
        manager = StackManager()

        for i in range(10):
            manager.push_frame()

        assert manager.get_stack_depth() == 10

        for i in range(10):
            manager.pop_frame()

        assert manager.get_stack_depth() == 0
        assert manager.current_frame is None

    def test_prologue_epilogue_consistency(self):
        """Verifica consistencia en la secuencia prologue-epilogue"""
        manager = StackManager()
        manager.push_frame(local_var_count=5)

        prologue = manager.generate_prologue()
        epilogue = manager.generate_epilogue()

        # Contar subu en prologue (debe haber al menos 1)
        subu_count = sum(1 for instr in prologue if "subu $sp" in instr)
        assert subu_count >= 1

        # Contar addu en epilogue (debe haber al menos 1 para deshacer subu)
        addu_count = sum(1 for instr in epilogue if "addu $sp" in instr)
        assert addu_count >= 1

    def test_multiple_functions_sequence(self):
        """Verifica secuencia realista de múltiples funciones"""
        manager = StackManager()

        # Función 1
        manager.push_frame(param_count=2, local_var_count=3)
        prologue1 = manager.generate_prologue()
        assert len(prologue1) > 0

        # Función 2 (anidada)
        manager.push_frame(param_count=1, local_var_count=2)
        prologue2 = manager.generate_prologue()
        assert len(prologue2) > 0

        # Epílogo función 2
        epilogue2 = manager.generate_epilogue()
        assert len(epilogue2) > 0
        manager.pop_frame()

        # Epílogo función 1
        epilogue1 = manager.generate_epilogue()
        assert len(epilogue1) > 0
        manager.pop_frame()

        assert manager.get_stack_depth() == 0

    def test_register_offset_calculation(self):
        """Verifica cálculo correcto de offsets de registros"""
        manager = StackManager()
        frame = manager.push_frame(local_var_count=4)

        # El offset de un registro saved debe ser negativo relativo a FP
        if frame.saved_reg_list:
            offset = frame.get_register_offset(frame.saved_reg_list[0])
            assert offset < 0  # Debería estar por debajo de FP

    def test_argument_passing_conventions(self):
        """Verifica convenciones de paso de argumentos"""
        manager = StackManager()
        arg_regs = manager.get_argument_registers()

        # Los primeros 4 argumentos van en a0-a3
        assert len(arg_regs) == 4
        assert arg_regs[0].reg_type == RegisterType.A0
        assert arg_regs[1].reg_type == RegisterType.A1
        assert arg_regs[2].reg_type == RegisterType.A2
        assert arg_regs[3].reg_type == RegisterType.A3

        # Todos son caller-saved
        assert all(manager.is_caller_saved(reg) for reg in arg_regs)

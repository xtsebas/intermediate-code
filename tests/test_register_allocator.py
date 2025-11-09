"""
Tests para RegisterAllocator.

Prueba:
- Asignación de registros
- Liberación de registros
- Algoritmo LRU
- Gestión de spillage
- Tabla de estado
"""

import pytest
from compiler.codegen.register_allocator import (
    RegisterPool, RegisterType, RegClass, AllocationLocation
)


class TestRegisterPoolBasics:
    """Tests básicos de funcionamiento del RegisterPool"""

    def test_initialization(self):
        """Test que el pool se inicializa correctamente"""
        pool = RegisterPool(use_saved_regs=True)

        assert pool.getAvailableRegisterCount() == 18  # 10 temps + 8 saved
        assert pool.getAllocatedRegisterCount() == 0
        assert pool.getSpilledVariableCount() == 0
        assert pool.getSpillAreaSize() == 0

    def test_initialization_without_saved(self):
        """Test inicialización sin registros salvados"""
        pool = RegisterPool(use_saved_regs=False)

        assert pool.getAvailableRegisterCount() == 10  # solo temporales
        assert pool.getAllocatedRegisterCount() == 0

    def test_register_state_table(self):
        """Test que la tabla de estado de registros se crea correctamente"""
        pool = RegisterPool(use_saved_regs=True)
        status_table = pool.getStatusTable()

        assert len(status_table) == 18
        assert all(status_table[f"t{i}"]['available'] for i in range(10))
        assert all(status_table[f"s{i}"]['available'] for i in range(8))


class TestRegisterAllocation:
    """Tests para asignación de registros"""

    def test_single_allocation(self):
        """Test asignación de un único registro"""
        pool = RegisterPool()
        reg_type, spilled = pool.getReg("var1")

        assert reg_type in [RegisterType.T0, RegisterType.T1, RegisterType.T2,
                           RegisterType.T3, RegisterType.T4, RegisterType.T5,
                           RegisterType.T6, RegisterType.T7, RegisterType.T8,
                           RegisterType.T9]
        assert not spilled
        assert pool.getAvailableRegisterCount() == 17
        assert pool.getAllocatedRegisterCount() == 1

    def test_multiple_allocations(self):
        """Test asignación múltiple de registros"""
        pool = RegisterPool()

        regs = []
        for i in range(5):
            reg_type, spilled = pool.getReg(f"var{i}")
            regs.append(reg_type)
            assert not spilled

        assert pool.getAvailableRegisterCount() == 13
        assert pool.getAllocatedRegisterCount() == 5

        # Verificar que son registros diferentes
        assert len(set(regs)) == 5

    def test_same_variable_returns_same_register(self):
        """Test que pedir el mismo registro dos veces retorna el mismo"""
        pool = RegisterPool()

        reg1, _ = pool.getReg("var1")
        reg2, _ = pool.getReg("var1")

        assert reg1 == reg2
        assert pool.getAllocatedRegisterCount() == 1

    def test_prefer_temporals(self):
        """Test que preferencia de temporales funciona"""
        pool = RegisterPool(use_saved_regs=True)

        # Asignar muchos temporales primero
        temp_regs = []
        for i in range(10):
            reg_type, _ = pool.getReg(f"temp{i}", prefer_temp=True)
            temp_regs.append(reg_type)

        # Todos deben ser temporales
        temp_types = {RegisterType.T0, RegisterType.T1, RegisterType.T2,
                     RegisterType.T3, RegisterType.T4, RegisterType.T5,
                     RegisterType.T6, RegisterType.T7, RegisterType.T8,
                     RegisterType.T9}
        assert all(reg in temp_types for reg in temp_regs)

    def test_allocation_prefers_temporals_by_default(self):
        """Test que por defecto se prefieren temporales"""
        pool = RegisterPool(use_saved_regs=True)

        reg_type, _ = pool.getReg("var1", prefer_temp=True)
        assert reg_type.value.startswith('t')


class TestRegisterFreedom:
    """Tests para liberación de registros"""

    def test_free_single_register(self):
        """Test liberación de un registro"""
        pool = RegisterPool()

        pool.getReg("var1")
        assert pool.getAvailableRegisterCount() == 17

        freed = pool.freeReg("var1")
        assert freed
        assert pool.getAvailableRegisterCount() == 18

    def test_free_nonexistent_variable(self):
        """Test liberar variable que no existe"""
        pool = RegisterPool()
        freed = pool.freeReg("nonexistent")
        assert not freed

    def test_free_all_registers(self):
        """Test freeAll libera todos los registros"""
        pool = RegisterPool()

        for i in range(5):
            pool.getReg(f"var{i}")

        assert pool.getAllocatedRegisterCount() == 5

        pool.freeAll()
        assert pool.getAvailableRegisterCount() == 18
        assert pool.getAllocatedRegisterCount() == 0

    def test_freed_register_can_be_reused(self):
        """Test que un registro liberado puede ser reasignado"""
        pool = RegisterPool()

        reg1, _ = pool.getReg("var1")
        pool.freeReg("var1")

        reg2, _ = pool.getReg("var2")
        assert reg1 == reg2


class TestSpillage:
    """Tests para gestión de spillage"""

    def test_spillage_occurs_when_no_registers_available(self):
        """Test que spillage ocurre cuando no hay registros disponibles"""
        pool = RegisterPool(use_saved_regs=False)  # Solo 10 temporales

        # Asignar todos los registros temporales
        for i in range(10):
            pool.getReg(f"var{i}")

        assert pool.getAvailableRegisterCount() == 0

        # Siguiente asignación debe causar spillage
        reg_type, spilled = pool.getReg("var10")
        assert spilled
        assert pool.getSpilledVariableCount() == 1

    def test_spill_offset_allocation(self):
        """Test que los offsets de spillage se asignan correctamente"""
        pool = RegisterPool(use_saved_regs=False)

        # Asignar todos los temporales
        for i in range(10):
            pool.getReg(f"var{i}")

        # Pedir uno más causa spillage de uno de los anteriores
        pool.getReg("var10")

        # Verificar que alguna variable fue spilleada
        spilled_count = pool.getSpilledVariableCount()
        assert spilled_count == 1

        # Encontrar cuál fue spilleada y verificar su offset
        spilled_vars = [v for v in pool.variable_locations.values()
                       if v.location == AllocationLocation.STACK]
        assert len(spilled_vars) == 1
        assert spilled_vars[0].stack_offset is not None
        assert spilled_vars[0].stack_offset < 0  # Offsets negativos para spillage

    def test_spill_area_size(self):
        """Test que el tamaño del área de spillage se calcula correctamente"""
        pool = RegisterPool(use_saved_regs=False)

        # Asignar todos los temporales
        for i in range(10):
            pool.getReg(f"var{i}")

        # Spillear 3 variables
        for i in range(3):
            pool.getReg(f"spill{i}")

        assert pool.getSpillAreaSize() == 12  # 3 * 4 bytes

    def test_multiple_spillages(self):
        """Test múltiples spillages"""
        pool = RegisterPool(use_saved_regs=False)

        # Asignar todos los temporales
        for i in range(10):
            pool.getReg(f"temp{i}")

        # Spillear varios - cada uno causará spillage (return True)
        for i in range(5):
            _, spilled = pool.getReg(f"spill{i}")
            assert spilled  # Todos causan spillage ya que no hay registros libres

        assert pool.getSpilledVariableCount() == 5
        assert pool.getSpillAreaSize() == 20  # 5 * 4 bytes


class TestLRUEviction:
    """Tests para algoritmo LRU de evicción"""

    def test_lru_evicts_least_recently_used(self):
        """Test que LRU evicta el menos usado recientemente"""
        pool = RegisterPool(use_saved_regs=False)

        # Asignar todos los 10 registros
        for i in range(10):
            pool.getReg(f"var{i}")

        # Acceder a var0 nuevamente para actualizar su last_access
        # Ahora var0 es el más recientemente usado
        pool.getReg("var0")

        # El siguiente debe spillear var1 (la menos recientemente usada ahora)
        pool.getReg("var10")

        # var1 debe estar spilleada (fue la menos recientemente usada)
        var1_location = pool.getVariableLocation("var1")
        assert var1_location.location == AllocationLocation.STACK

    def test_lru_with_saved_registers(self):
        """Test LRU con registros salvados"""
        pool = RegisterPool(use_saved_regs=True)

        # Asignar 18 variables
        for i in range(18):
            pool.getReg(f"var{i}")

        assert pool.getAvailableRegisterCount() == 0

        # Acceder a var0 nuevamente para actualizar su last_access
        pool.getReg("var0")

        # El siguiente debe spillear algo menos reciente que var0
        pool.getReg("var18")

        # var1 debe estar spilleada (fue menos recientemente usada que var0)
        var1_location = pool.getVariableLocation("var1")
        assert var1_location.location == AllocationLocation.STACK


class TestVariableLocationTracking:
    """Tests para seguimiento de ubicación de variables"""

    def test_variable_location_in_register(self):
        """Test que se rastrea correctamente variable en registro"""
        pool = RegisterPool()

        pool.getReg("myvar")
        location = pool.getVariableLocation("myvar")

        assert location is not None
        assert location.location == AllocationLocation.REGISTER
        assert location.register is not None
        assert location.var_name == "myvar"

    def test_variable_location_in_stack(self):
        """Test que se rastrea correctamente variable en stack"""
        pool = RegisterPool(use_saved_regs=False)

        # Llenar todos los registros
        for i in range(10):
            pool.getReg(f"var{i}")

        # Pedir otra variable causa spillage de una existente
        pool.getReg("spillvar")

        # spillvar está en registro (no en stack)
        # Pero alguna otra variable (var0-var9) debe estar en stack
        location_spillvar = pool.getVariableLocation("spillvar")
        assert location_spillvar.location == AllocationLocation.REGISTER

        # Verificar que alguna variable fue spilleada
        spilled_vars = [v for v in pool.variable_locations.values()
                       if v.location == AllocationLocation.STACK]
        assert len(spilled_vars) == 1
        assert spilled_vars[0].stack_offset is not None

    def test_variable_status_table(self):
        """Test que la tabla de estado de variables es correcta"""
        pool = RegisterPool()

        pool.getReg("var1")
        pool.getReg("var2")

        status_table = pool.getVariableStatusTable()

        assert "var1" in status_table
        assert "var2" in status_table
        assert status_table["var1"]["location"] == "register"
        assert status_table["var2"]["location"] == "register"


class TestRegistryStateTable:
    """Tests para tabla de estado de registros"""

    def test_status_table_shows_available(self):
        """Test que tabla de estado muestra registros disponibles"""
        pool = RegisterPool()
        status = pool.getStatusTable()

        assert status["t0"]["available"] == True
        assert status["t0"]["allocated_to"] is None

    def test_status_table_shows_allocated(self):
        """Test que tabla de estado muestra registros asignados"""
        pool = RegisterPool()
        pool.getReg("var1")

        status = pool.getStatusTable()

        # Encontrar cuál registro fue asignado
        allocated = [k for k, v in status.items() if not v["available"]]
        assert len(allocated) == 1
        assert status[allocated[0]]["allocated_to"] == "var1"

    def test_mips_register_numbers_correct(self):
        """Test que los números MIPS de los registros son correctos"""
        pool = RegisterPool()
        status = pool.getStatusTable()

        assert status["t0"]["mips_number"] == "$8"
        assert status["t1"]["mips_number"] == "$9"
        assert status["t8"]["mips_number"] == "$24"
        assert status["t9"]["mips_number"] == "$25"
        assert status["s0"]["mips_number"] == "$16"
        assert status["s7"]["mips_number"] == "$23"


class TestResets:
    """Tests para reinicio del allocator"""

    def test_reset_clears_allocations(self):
        """Test que reset limpia todas las asignaciones"""
        pool = RegisterPool()

        for i in range(5):
            pool.getReg(f"var{i}")

        pool.reset()

        assert pool.getAvailableRegisterCount() == 18
        assert pool.getAllocatedRegisterCount() == 0
        assert pool.getSpilledVariableCount() == 0
        assert pool.getSpillAreaSize() == 0
        assert len(pool.variable_locations) == 0

    def test_reset_clears_allocation_history(self):
        """Test que reset limpia el historial"""
        pool = RegisterPool()

        pool.getReg("var1")
        assert len(pool.allocation_history) > 0

        pool.reset()
        assert len(pool.allocation_history) == 0


class TestAccessTracking:
    """Tests para seguimiento de accesos"""

    def test_access_count_incremented(self):
        """Test que el contador de accesos se incrementa"""
        pool = RegisterPool()

        pool.getReg("var1")
        location1 = pool.getVariableLocation("var1")
        count1 = location1.access_count

        pool.getReg("var1")
        location2 = pool.getVariableLocation("var1")
        count2 = location2.access_count

        assert count2 > count1

    def test_last_access_updated(self):
        """Test que last_access se actualiza"""
        pool = RegisterPool()

        pool.getReg("var1")
        location1 = pool.getVariableLocation("var1")
        access1 = location1.last_access

        pool.getReg("var2")
        pool.getReg("var1")
        location2 = pool.getVariableLocation("var1")
        access2 = location2.last_access

        assert access2 > access1


class TestDebugOutput:
    """Tests para información de debugging"""

    def test_debug_info_output(self):
        """Test que getDebugInfo retorna string válido"""
        pool = RegisterPool()

        pool.getReg("var1")
        debug_info = pool.getDebugInfo()

        assert isinstance(debug_info, str)
        assert "Register Allocator Status" in debug_info
        assert "var1" in debug_info

    def test_str_representation(self):
        """Test la representación en string"""
        pool = RegisterPool()

        pool.getReg("var1")
        pool.getReg("var2")

        str_rep = str(pool)
        assert "RegisterPool" in str_rep
        assert "available=" in str_rep
        assert "allocated=" in str_rep


class TestEdgeCases:
    """Tests para casos especiales"""

    def test_all_temps_then_all_saved(self):
        """Test asignar todos los temporales y luego salvados"""
        pool = RegisterPool(use_saved_regs=True)

        # Asignar todos los temporales
        for i in range(10):
            reg_type, spilled = pool.getReg(f"temp{i}", prefer_temp=True)
            assert reg_type in [RegisterType.T0, RegisterType.T1, RegisterType.T2,
                              RegisterType.T3, RegisterType.T4, RegisterType.T5,
                              RegisterType.T6, RegisterType.T7, RegisterType.T8,
                              RegisterType.T9]
            assert not spilled

        # Ahora asignar salvados
        for i in range(8):
            reg_type, spilled = pool.getReg(f"saved{i}", prefer_temp=True)
            assert reg_type in [RegisterType.S0, RegisterType.S1, RegisterType.S2,
                              RegisterType.S3, RegisterType.S4, RegisterType.S5,
                              RegisterType.S6, RegisterType.S7]
            assert not spilled

        assert pool.getAvailableRegisterCount() == 0
        assert pool.getAllocatedRegisterCount() == 18

    def test_interleaved_allocate_free(self):
        """Test asignación y liberación intercalada"""
        pool = RegisterPool()

        reg1, _ = pool.getReg("var1")
        reg2, _ = pool.getReg("var2")

        pool.freeReg("var1")
        reg3, _ = pool.getReg("var3")

        # reg3 puede ser igual a reg1 (porque fue liberado)
        assert pool.getAllocatedRegisterCount() == 2

    def test_large_spillage(self):
        """Test spillage con muchas variables"""
        pool = RegisterPool(use_saved_regs=True)

        # Asignar 30 variables (18 en registros, 12 spilleadas)
        for i in range(30):
            pool.getReg(f"var{i}")

        assert pool.getAllocatedRegisterCount() == 18
        assert pool.getSpilledVariableCount() == 12
        assert pool.getSpillAreaSize() == 48  # 12 * 4 bytes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

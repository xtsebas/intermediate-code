from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import OrderedDict


class RegisterType(Enum):
    """Tipos de registros MIPS disponibles para asignación"""
    T0 = "t0"   # $8  - temporales (caller-saved)
    T1 = "t1"   # $9
    T2 = "t2"   # $10
    T3 = "t3"   # $11
    T4 = "t4"   # $12
    T5 = "t5"   # $13
    T6 = "t6"   # $14
    T7 = "t7"   # $15
    T8 = "t8"   # $24 - temporales (caller-saved)
    T9 = "t9"   # $25

    S0 = "s0"   # $16 - saved (callee-saved)
    S1 = "s1"   # $17
    S2 = "s2"   # $18
    S3 = "s3"   # $19
    S4 = "s4"   # $20
    S5 = "s5"   # $21
    S6 = "s6"   # $22
    S7 = "s7"   # $23


class RegClass(Enum):
    """Clasificación de registros"""
    TEMPORARY = "temporary"  # t0-t7, t8-t9 (caller-saved)
    SAVED = "saved"          # s0-s7 (callee-saved)


class AllocationLocation(Enum):
    """Ubicación posible de una variable"""
    REGISTER = "register"
    STACK = "stack"
    UNALLOCATED = "unallocated"


@dataclass
class RegisterState:
    """Estado de un registro individual"""
    reg_type: RegisterType
    reg_class: RegClass
    mips_number: int      # Número de registro MIPS ($8, $9, etc.)
    is_available: bool = True
    allocated_to: Optional[str] = None  # Nombre de variable/temp
    last_access: int = -1  # Para LRU
    spill_offset: Optional[int] = None  # Offset en stack si está spilleado

    def __str__(self) -> str:
        status = "FREE" if self.is_available else f"USED({self.allocated_to})"
        return f"${self.reg_type.value}({status})"


@dataclass
class VariableLocation:
    """Ubicación de una variable en memoria/registros"""
    var_name: str
    location: AllocationLocation
    register: Optional[RegisterState] = None
    stack_offset: Optional[int] = None
    access_count: int = 0
    last_access: int = -1


class RegisterPool:
    """
    Gestor de pool de registros MIPS con asignación inteligente y spillage.

    Características:
    - Asignación automática de registros disponibles
    - Algoritmo LRU para evicción cuando no hay registros libres
    - Spillage automático a stack
    - Tabla de estado de todos los registros
    """

    def __init__(self, use_saved_regs: bool = True):
        """
        Inicializa el RegisterPool.

        Args:
            use_saved_regs: Si True, incluye registros s0-s7; si False, solo t0-t9
        """
        self.use_saved_regs = use_saved_regs
        self.access_counter = 0  # Para implementar LRU
        self.stack_offset = 0    # Offset actual para spillage
        self.spill_base = -4     # Base offset para spillage (relativo a FP)

        # Pool de registros
        self.registers: Dict[RegisterType, RegisterState] = {}
        self.temp_registers: List[RegisterType] = []
        self.saved_registers: List[RegisterType] = []

        # Tabla de ubicaciones de variables
        self.variable_locations: Dict[str, VariableLocation] = {}

        # Historial de asignaciones (para debugging)
        self.allocation_history: List[Tuple[str, RegisterType, str]] = []

        self._init_registers()

    def _init_registers(self):
        """Inicializa el pool de registros disponibles"""
        # Temporales (t0-t7, t8-t9)
        temp_types = [
            RegisterType.T0, RegisterType.T1, RegisterType.T2, RegisterType.T3,
            RegisterType.T4, RegisterType.T5, RegisterType.T6, RegisterType.T7,
            RegisterType.T8, RegisterType.T9
        ]

        temp_mips_nums = [8, 9, 10, 11, 12, 13, 14, 15, 24, 25]

        for reg_type, mips_num in zip(temp_types, temp_mips_nums):
            self.registers[reg_type] = RegisterState(
                reg_type=reg_type,
                reg_class=RegClass.TEMPORARY,
                mips_number=mips_num,
                is_available=True
            )
            self.temp_registers.append(reg_type)

        # Salvados (s0-s7)
        if self.use_saved_regs:
            saved_types = [
                RegisterType.S0, RegisterType.S1, RegisterType.S2, RegisterType.S3,
                RegisterType.S4, RegisterType.S5, RegisterType.S6, RegisterType.S7
            ]

            saved_mips_nums = list(range(16, 24))

            for reg_type, mips_num in zip(saved_types, saved_mips_nums):
                self.registers[reg_type] = RegisterState(
                    reg_type=reg_type,
                    reg_class=RegClass.SAVED,
                    mips_number=mips_num,
                    is_available=True
                )
                self.saved_registers.append(reg_type)

    def getReg(self, var_name: str, prefer_temp: bool = True) -> Tuple[RegisterType, bool]:
        """
        Obtiene un registro para una variable.

        Algoritmo:
        1. Si la variable ya tiene registro, retorna ese
        2. Si hay registros libres, asigna uno
        3. Si no hay libres, usa LRU para evictar y spillear

        Args:
            var_name: Nombre de la variable/temporal
            prefer_temp: Preferir registros temporales sobre salvados

        Returns:
            (RegisterType asignado, bool indicando si fue spilleado)
        """
        # Si ya está asignada, retorna su registro
        if var_name in self.variable_locations:
            loc = self.variable_locations[var_name]
            if loc.location == AllocationLocation.REGISTER:
                loc.access_count += 1
                loc.last_access = self.access_counter
                # También actualizar el RegisterState para que LRU funcione correctamente
                if loc.register:
                    loc.register.last_access = self.access_counter
                self.access_counter += 1
                return (loc.register.reg_type, False)

        # Buscar registro disponible
        available_reg = self._find_available_register(prefer_temp)

        if available_reg:
            # Asignar registro
            reg_state = self.registers[available_reg]
            reg_state.is_available = False
            reg_state.allocated_to = var_name
            reg_state.last_access = self.access_counter

            # Crear entrada en tabla de variables
            self.variable_locations[var_name] = VariableLocation(
                var_name=var_name,
                location=AllocationLocation.REGISTER,
                register=reg_state,
                access_count=1,
                last_access=self.access_counter
            )

            self.allocation_history.append((var_name, available_reg, "allocated"))
            self.access_counter += 1

            return (available_reg, False)

        # No hay registros disponibles - spill usando LRU
        victim_reg = self._find_lru_register(prefer_temp)
        if not victim_reg:
            raise RuntimeError("No registers available for allocation")

        # Spillear el registro víctima
        spilled_var = self._spill_register(victim_reg)

        # Asignar el registro liberado a la nueva variable
        reg_state = self.registers[victim_reg]
        reg_state.is_available = False
        reg_state.allocated_to = var_name
        reg_state.last_access = self.access_counter

        self.variable_locations[var_name] = VariableLocation(
            var_name=var_name,
            location=AllocationLocation.REGISTER,
            register=reg_state,
            access_count=1,
            last_access=self.access_counter
        )

        self.allocation_history.append((var_name, victim_reg, f"allocated_after_spill({spilled_var})"))
        self.access_counter += 1

        return (victim_reg, True)

    def freeReg(self, var_name: str) -> bool:
        """
        Libera un registro asignado a una variable.

        Args:
            var_name: Nombre de la variable

        Returns:
            True si se liberó con éxito, False si no estaba asignada
        """
        if var_name not in self.variable_locations:
            return False

        loc = self.variable_locations[var_name]

        if loc.location == AllocationLocation.REGISTER and loc.register:
            reg_state = loc.register
            reg_state.is_available = True
            reg_state.allocated_to = None

            self.allocation_history.append((var_name, reg_state.reg_type, "freed"))
            return True

        return False

    def freeAll(self):
        """Libera todos los registros asignados"""
        for reg_state in self.registers.values():
            if not reg_state.is_available:
                reg_state.is_available = True
                reg_state.allocated_to = None

    def _find_available_register(self, prefer_temp: bool) -> Optional[RegisterType]:
        """Encuentra un registro disponible"""
        # Preferir temporales si se pide
        regs_to_check = self.temp_registers if prefer_temp else self.saved_registers

        for reg_type in regs_to_check:
            if self.registers[reg_type].is_available:
                return reg_type

        # Si no encuentra en preferidos, buscar en otros
        other_regs = self.saved_registers if prefer_temp else self.temp_registers
        for reg_type in other_regs:
            if self.registers[reg_type].is_available:
                return reg_type

        return None

    def _find_lru_register(self, prefer_temp: bool) -> Optional[RegisterType]:
        """Encuentra el registro menos usado recientemente (LRU)"""
        candidates = self.temp_registers if prefer_temp else self.saved_registers

        # Filtrar registros asignados
        assigned_regs = [(rt, self.registers[rt]) for rt in candidates
                        if not self.registers[rt].is_available]

        if not assigned_regs:
            # Si no hay en preferidos, buscar en otros
            other_regs = self.saved_registers if prefer_temp else self.temp_registers
            assigned_regs = [(rt, self.registers[rt]) for rt in other_regs
                            if not self.registers[rt].is_available]

        if not assigned_regs:
            return None

        # Encontrar el con menor last_access
        return min(assigned_regs, key=lambda x: x[1].last_access)[0]

    def _spill_register(self, reg_type: RegisterType) -> str:
        """
        Spillea un registro a memoria (stack).

        Args:
            reg_type: Tipo de registro a spillear

        Returns:
            Nombre de la variable que fue spilleada
        """
        reg_state = self.registers[reg_type]

        if reg_state.is_available or not reg_state.allocated_to:
            raise RuntimeError(f"Cannot spill unallocated register {reg_type}")

        var_name = reg_state.allocated_to
        spill_offset = self.spill_base + self.stack_offset
        self.stack_offset -= 4  # Cada variable ocupa 4 bytes

        # Actualizar ubicación de la variable
        if var_name in self.variable_locations:
            var_location = self.variable_locations[var_name]
            var_location.location = AllocationLocation.STACK
            var_location.stack_offset = spill_offset
            var_location.register = None  # Ya no está en registro

        # Limpiar el registro
        reg_state.spill_offset = spill_offset
        reg_state.allocated_to = None
        reg_state.is_available = True

        self.allocation_history.append((var_name, reg_type, f"spilled(offset={spill_offset})"))

        return var_name

    def getRegisterState(self, reg_type: RegisterType) -> Optional[RegisterState]:
        """Obtiene el estado de un registro específico"""
        return self.registers.get(reg_type)

    def getVariableLocation(self, var_name: str) -> Optional[VariableLocation]:
        """Obtiene la ubicación actual de una variable"""
        return self.variable_locations.get(var_name)

    def getSpillOffset(self, var_name: str) -> Optional[int]:
        """Obtiene el offset de spillage de una variable si está spilleada"""
        if var_name in self.variable_locations:
            return self.variable_locations[var_name].stack_offset
        return None

    def getStatusTable(self) -> Dict[str, Dict]:
        """
        Retorna una tabla de estado de todos los registros.

        Returns:
            Dict con información de cada registro
        """
        status = {}
        for reg_type, reg_state in self.registers.items():
            status[str(reg_type.value)] = {
                'available': reg_state.is_available,
                'allocated_to': reg_state.allocated_to,
                'mips_number': f"${reg_state.mips_number}",
                'last_access': reg_state.last_access,
                'spill_offset': reg_state.spill_offset,
                'reg_class': reg_state.reg_class.value
            }
        return status

    def getVariableStatusTable(self) -> Dict[str, Dict]:
        """
        Retorna una tabla de estado de todas las variables.

        Returns:
            Dict con información de cada variable
        """
        status = {}
        for var_name, var_loc in self.variable_locations.items():
            if var_loc.location == AllocationLocation.REGISTER:
                status[var_name] = {
                    'location': var_loc.location.value,
                    'register': var_loc.register.reg_type.value if var_loc.register else None,
                    'access_count': var_loc.access_count,
                    'last_access': var_loc.last_access
                }
            else:
                status[var_name] = {
                    'location': var_loc.location.value,
                    'stack_offset': var_loc.stack_offset,
                    'access_count': var_loc.access_count,
                    'last_access': var_loc.last_access
                }
        return status

    def getAvailableRegisterCount(self) -> int:
        """Cuenta de registros disponibles"""
        return sum(1 for reg in self.registers.values() if reg.is_available)

    def getAllocatedRegisterCount(self) -> int:
        """Cuenta de registros asignados"""
        return sum(1 for reg in self.registers.values() if not reg.is_available)

    def getSpilledVariableCount(self) -> int:
        """Cuenta de variables spilleadas"""
        return sum(1 for var_loc in self.variable_locations.values()
                  if var_loc.location == AllocationLocation.STACK)

    def getSpillAreaSize(self) -> int:
        """Tamaño total del área de spillage en bytes"""
        return abs(self.stack_offset)

    def reset(self):
        """Reinicia el allocator"""
        for reg_state in self.registers.values():
            reg_state.is_available = True
            reg_state.allocated_to = None
            reg_state.last_access = -1
            reg_state.spill_offset = None

        self.variable_locations.clear()
        self.allocation_history.clear()
        self.access_counter = 0
        self.stack_offset = 0

    def getDebugInfo(self) -> str:
        """Retorna información de debugging"""
        lines = [
            "=== Register Allocator Status ===",
            f"Available registers: {self.getAvailableRegisterCount()}",
            f"Allocated registers: {self.getAllocatedRegisterCount()}",
            f"Spilled variables: {self.getSpilledVariableCount()}",
            f"Spill area size: {self.getSpillAreaSize()} bytes",
            "",
            "Register State:",
        ]

        for reg_type, reg_state in self.registers.items():
            lines.append(f"  {str(reg_state)}")

        lines.append("\nVariable Locations:")
        for var_name, var_loc in self.variable_locations.items():
            if var_loc.location == AllocationLocation.REGISTER:
                lines.append(f"  {var_name} -> {var_loc.register.reg_type.value}")
            else:
                lines.append(f"  {var_name} -> STACK[{var_loc.stack_offset}]")

        return "\n".join(lines)

    def __str__(self) -> str:
        return (f"RegisterPool(available={self.getAvailableRegisterCount()}, "
                f"allocated={self.getAllocatedRegisterCount()}, "
                f"spilled={self.getSpilledVariableCount()})")

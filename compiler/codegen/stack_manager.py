from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field


class RegisterType(Enum):
    """Tipos de registros MIPS"""
    ZERO = "zero"              # $0  - siempre cero
    AT = "at"                  # $1  - reservado para assembler
    V0 = "v0"                  # $2  - return value
    V1 = "v1"                  # $3  - return value
    A0 = "a0"                  # $4  - arg 0
    A1 = "a1"                  # $5  - arg 1
    A2 = "a2"                  # $6  - arg 2
    A3 = "a3"                  # $7  - arg 3
    T0 = "t0"                  # $8  - temporales (caller-saved)
    T1 = "t1"                  # $9
    T2 = "t2"                  # $10
    T3 = "t3"                  # $11
    T4 = "t4"                  # $12
    T5 = "t5"                  # $13
    T6 = "t6"                  # $14
    T7 = "t7"                  # $15
    S0 = "s0"                  # $16 - saved temporales (callee-saved)
    S1 = "s1"                  # $17
    S2 = "s2"                  # $18
    S3 = "s3"                  # $19
    S4 = "s4"                  # $20
    S5 = "s5"                  # $21
    S6 = "s6"                  # $22
    S7 = "s7"                  # $23
    T8 = "t8"                  # $24 - temporales (caller-saved)
    T9 = "t9"                  # $25
    K0 = "k0"                  # $26 - reservado para kernel
    K1 = "k1"                  # $27
    GP = "gp"                  # $28 - global pointer
    SP = "sp"                  # $29 - stack pointer
    FP = "fp"                  # $30 - frame pointer (s8)
    RA = "ra"                  # $31 - return address


class RegisterClass(Enum):
    """Clasificación de registros por su propósito"""
    ZERO = "zero"              # Registro cero
    RETURN = "return"          # v0, v1
    ARGUMENT = "argument"      # a0-a3
    TEMPORARY = "temporary"    # t0-t7, t8-t9 (caller-saved)
    SAVED = "saved"            # s0-s7 (callee-saved)
    RESERVED = "reserved"      # at, k0, k1, gp, sp, fp, ra
    SPECIAL = "special"        # SP, FP, RA


@dataclass(frozen=True)
class MipsRegister:
    """Representación de un registro MIPS"""
    reg_type: RegisterType
    reg_number: int
    reg_class: RegisterClass
    is_caller_saved: bool
    is_callee_saved: bool

    @property
    def name(self) -> str:
        """Nombre del registro con símbolo $"""
        return f"${self.reg_type.value}"

    @property
    def number_name(self) -> str:
        """Nombre del registro con número"""
        return f"${self.reg_number}"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        reg_type_upper = self.reg_type.value.upper()
        return f"MipsRegister({self.name}, class={self.reg_class.value}, type={reg_type_upper})"


class RegisterAllocator:
    """Asignador de registros temporales con tracking de uso"""

    def __init__(self):
        # Registros temporales disponibles (t0-t7, t8-t9)
        self.temp_registers: List[MipsRegister] = []
        self.available_temps: Set[MipsRegister] = set()
        self.allocated_temps: Dict[str, MipsRegister] = {}  # var -> register
        self._init_temp_registers()

    def _init_temp_registers(self):
        """Inicializa los registros temporales disponibles"""
        temp_types = [
            RegisterType.T0, RegisterType.T1, RegisterType.T2, RegisterType.T3,
            RegisterType.T4, RegisterType.T5, RegisterType.T6, RegisterType.T7,
            RegisterType.T8, RegisterType.T9
        ]

        temp_numbers = list(range(8, 16)) + list(range(24, 26))

        for reg_type, reg_num in zip(temp_types, temp_numbers):
            reg = MipsRegister(
                reg_type=reg_type,
                reg_number=reg_num,
                reg_class=RegisterClass.TEMPORARY,
                is_caller_saved=True,
                is_callee_saved=False
            )
            self.temp_registers.append(reg)
            self.available_temps.add(reg)

    def allocate(self, var_name: str) -> Optional[MipsRegister]:
        """Asigna un registro temporal disponible a una variable"""
        if not self.available_temps:
            return None

        reg = self.available_temps.pop()
        self.allocated_temps[var_name] = reg
        return reg

    def deallocate(self, var_name: str) -> bool:
        """Libera un registro temporal"""
        if var_name in self.allocated_temps:
            reg = self.allocated_temps.pop(var_name)
            self.available_temps.add(reg)
            return True
        return False

    def get_register(self, var_name: str) -> Optional[MipsRegister]:
        """Obtiene el registro asignado a una variable"""
        return self.allocated_temps.get(var_name)

    def is_allocated(self, var_name: str) -> bool:
        """Verifica si una variable tiene registro asignado"""
        return var_name in self.allocated_temps

    def free_count(self) -> int:
        """Cuenta de registros libres"""
        return len(self.available_temps)

    def reset(self):
        """Reinicia el asignador"""
        self.available_temps = set(self.temp_registers)
        self.allocated_temps.clear()


@dataclass
class StackFrameLayout:
    """
    Layout del stack frame en MIPS

    Estructura (crecer hacia direcciones más bajas):

    [FP + offset_params]        <- Parámetros 4-N (si los hay)
    [FP + 0]                    <- Frame Pointer
    [FP - 4]                    <- Return Address ($ra)
    [FP - 8]                    <- Saved FP (old $fp)
    [FP - 8 - offset_saved]     <- Registros saved (s0-s7)
    [FP - 8 - offset_saved - offset_locals]  <- Variables locales
    [SP]                        <- Stack Pointer (final)
    """

    frame_pointer_offset: int = 0       # Offset del FP relativo a FP
    return_address_offset: int = -4     # Offset del RA
    saved_fp_offset: int = -8           # Offset del FP guardado

    saved_regs_offset: int = -8         # Donde comienzan los registros saved
    saved_regs_size: int = 0            # Bytes usados por registros saved

    locals_offset: int = -8             # Donde comienzan las variables locales
    locals_size: int = 0                # Bytes usados por variables locales

    saved_reg_list: List[MipsRegister] = field(default_factory=list)  # Lista de saved regs

    total_frame_size: int = 0           # Tamaño total del frame

    def calculate_total_size(self) -> int:
        """Calcula el tamaño total del frame"""
        # Tamaño mínimo: RA + old FP
        min_size = 8
        # Agregar saved registers y locals
        self.total_frame_size = min_size + self.saved_regs_size + self.locals_size
        return self.total_frame_size

    def get_register_offset(self, reg: MipsRegister) -> int:
        """Obtiene el offset de un registro saved en el frame"""
        if reg not in self.saved_reg_list:
            return None
        index = self.saved_reg_list.index(reg)
        return self.saved_regs_offset - (index + 1) * 4

    def __repr__(self) -> str:
        return (f"StackFrameLayout(total={self.total_frame_size}, "
                f"saved={self.saved_regs_size}, locals={self.locals_size})")


class StackManager:
    """
    Gerenciador del stack frame y calling conventions para MIPS32.

    Implementa:
    - Stack frame allocation
    - Register saving/restoring
    - Calling convention (caller-saved, callee-saved)
    - Prologue/epilogue generation
    """

    def __init__(self):
        self.register_allocator = RegisterAllocator()
        self.current_frame: Optional[StackFrameLayout] = None
        self.function_stack: List[StackFrameLayout] = []
        self.callee_saved_regs: List[MipsRegister] = self._init_callee_saved()
        self.register_map: Dict[RegisterType, MipsRegister] = self._init_register_map()

    def _init_callee_saved(self) -> List[MipsRegister]:
        """Inicializa la lista de registros que deben ser salvados"""
        saved_types = [
            RegisterType.S0, RegisterType.S1, RegisterType.S2, RegisterType.S3,
            RegisterType.S4, RegisterType.S5, RegisterType.S6, RegisterType.S7
        ]

        saved_numbers = list(range(16, 24))

        regs = []
        for reg_type, reg_num in zip(saved_types, saved_numbers):
            reg = MipsRegister(
                reg_type=reg_type,
                reg_number=reg_num,
                reg_class=RegisterClass.SAVED,
                is_caller_saved=False,
                is_callee_saved=True
            )
            regs.append(reg)

        return regs

    def _init_register_map(self) -> Dict[RegisterType, MipsRegister]:
        """Crea un mapa de todos los registros MIPS"""
        reg_map = {}

        # Definir todos los registros MIPS
        register_definitions = [
            (RegisterType.ZERO, 0, RegisterClass.ZERO, False, False),
            (RegisterType.AT, 1, RegisterClass.RESERVED, False, False),
            (RegisterType.V0, 2, RegisterClass.RETURN, True, False),
            (RegisterType.V1, 3, RegisterClass.RETURN, True, False),
            (RegisterType.A0, 4, RegisterClass.ARGUMENT, True, False),
            (RegisterType.A1, 5, RegisterClass.ARGUMENT, True, False),
            (RegisterType.A2, 6, RegisterClass.ARGUMENT, True, False),
            (RegisterType.A3, 7, RegisterClass.ARGUMENT, True, False),
            (RegisterType.T0, 8, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T1, 9, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T2, 10, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T3, 11, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T4, 12, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T5, 13, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T6, 14, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T7, 15, RegisterClass.TEMPORARY, True, False),
            (RegisterType.S0, 16, RegisterClass.SAVED, False, True),
            (RegisterType.S1, 17, RegisterClass.SAVED, False, True),
            (RegisterType.S2, 18, RegisterClass.SAVED, False, True),
            (RegisterType.S3, 19, RegisterClass.SAVED, False, True),
            (RegisterType.S4, 20, RegisterClass.SAVED, False, True),
            (RegisterType.S5, 21, RegisterClass.SAVED, False, True),
            (RegisterType.S6, 22, RegisterClass.SAVED, False, True),
            (RegisterType.S7, 23, RegisterClass.SAVED, False, True),
            (RegisterType.T8, 24, RegisterClass.TEMPORARY, True, False),
            (RegisterType.T9, 25, RegisterClass.TEMPORARY, True, False),
            (RegisterType.K0, 26, RegisterClass.RESERVED, False, False),
            (RegisterType.K1, 27, RegisterClass.RESERVED, False, False),
            (RegisterType.GP, 28, RegisterClass.RESERVED, False, False),
            (RegisterType.SP, 29, RegisterClass.SPECIAL, False, False),
            (RegisterType.FP, 30, RegisterClass.SPECIAL, False, True),
            (RegisterType.RA, 31, RegisterClass.SPECIAL, False, False),
        ]

        for reg_type, reg_num, reg_class, caller_saved, callee_saved in register_definitions:
            reg = MipsRegister(
                reg_type=reg_type,
                reg_number=reg_num,
                reg_class=reg_class,
                is_caller_saved=caller_saved,
                is_callee_saved=callee_saved
            )
            reg_map[reg_type] = reg

        return reg_map

    def push_frame(self, param_count: int = 0, local_var_count: int = 0,
                   local_var_size: int = 4) -> StackFrameLayout:
        """
        Crea un nuevo frame en el stack para una función.

        Args:
            param_count: Número de parámetros (los primeros 4 van en registros)
            local_var_count: Número de variables locales
            local_var_size: Tamaño de cada variable local en bytes

        Returns:
            StackFrameLayout con la información del nuevo frame
        """
        frame = StackFrameLayout()

        # Calcular offset de saved registers
        frame.saved_regs_offset = -8  # Después del RA y old FP
        frame.saved_reg_list = self.callee_saved_regs.copy()
        frame.saved_regs_size = len(frame.saved_reg_list) * 4

        # Calcular offset de variables locales
        frame.locals_offset = frame.saved_regs_offset - frame.saved_regs_size
        frame.locals_size = local_var_count * local_var_size

        # Calcular tamaño total
        frame.calculate_total_size()

        self.function_stack.append(frame)
        self.current_frame = frame

        return frame

    def pop_frame(self) -> Optional[StackFrameLayout]:
        """Saca el frame actual del stack"""
        if self.function_stack:
            frame = self.function_stack.pop()
            self.current_frame = self.function_stack[-1] if self.function_stack else None
            return frame
        return None

    def get_current_frame(self) -> Optional[StackFrameLayout]:
        """Obtiene el frame actual"""
        return self.current_frame

    # ========== SECUENCIAS DE CÓDIGO MIPS ==========

    def generate_prologue(self) -> List[str]:
        """
        Genera el prólogo de una función MIPS.

        Secuencia:
        1. Restar SP para hacer espacio (subu $sp, $sp, frame_size)
        2. Guardar RA ($ra)
        3. Guardar FP anterior ($fp)
        4. Establecer FP nuevo
        5. Guardar registros callee-saved usados

        Returns:
            Lista de instrucciones MIPS
        """
        if not self.current_frame:
            raise RuntimeError("No hay frame activo para generar prólogo")

        instructions = []
        frame = self.current_frame
        frame_size = frame.total_frame_size

        # 1. Restar SP (crecer el stack)
        if frame_size > 0:
            instructions.append(f"subu $sp, $sp, {frame_size}  # Allocate frame")

        # 2. Guardar RA en offset -4 relativo a nuevo FP
        # En el nuevo espacio: [SP + frame_size - 4]
        ra_offset = frame_size - 4
        instructions.append(f"sw $ra, {ra_offset}($sp)  # Save return address")

        # 3. Guardar FP antiguo
        old_fp_offset = frame_size - 8
        instructions.append(f"sw $fp, {old_fp_offset}($sp)  # Save old frame pointer")

        # 4. Establecer FP nuevo
        instructions.append(f"addu $fp, $sp, {frame_size}  # Set new frame pointer")

        # 5. Guardar registros callee-saved
        for i, reg in enumerate(frame.saved_reg_list):
            offset = frame_size - 8 - (i + 1) * 4
            instructions.append(f"sw ${reg.reg_type.value}, {offset}($sp)  # Save {reg.name}")

        return instructions

    def generate_epilogue(self) -> List[str]:
        """
        Genera el epílogo de una función MIPS.

        Secuencia:
        1. Restaurar registros callee-saved
        2. Restaurar RA
        3. Restaurar FP antiguo
        4. Aumentar SP (deshacer frame)
        5. Retornar (jr $ra)

        Returns:
            Lista de instrucciones MIPS
        """
        if not self.current_frame:
            raise RuntimeError("No hay frame activo para generar epílogo")

        instructions = []
        frame = self.current_frame
        frame_size = frame.total_frame_size

        # 1. Restaurar registros callee-saved (en orden inverso)
        for i in range(len(frame.saved_reg_list) - 1, -1, -1):
            reg = frame.saved_reg_list[i]
            offset = frame_size - 8 - (i + 1) * 4
            instructions.append(f"lw ${reg.reg_type.value}, {offset}($sp)  # Restore {reg.name}")

        # 2. Restaurar RA
        ra_offset = frame_size - 4
        instructions.append(f"lw $ra, {ra_offset}($sp)  # Restore return address")

        # 3. Restaurar FP antiguo
        old_fp_offset = frame_size - 8
        instructions.append(f"lw $fp, {old_fp_offset}($sp)  # Restore old frame pointer")

        # 4. Aumentar SP (deshacer frame)
        if frame_size > 0:
            instructions.append(f"addu $sp, $sp, {frame_size}  # Deallocate frame")

        # 5. Retornar
        instructions.append("jr $ra  # Return to caller")

        return instructions

    def generate_caller_prologue(self, arg_count: int) -> List[str]:
        """
        Genera el prólogo en el caller (antes de call).

        Pasos:
        1. Guardar registros caller-saved si es necesario
        2. Pasar argumentos en a0-a3 (o stack si > 4 args)

        Args:
            arg_count: Número de argumentos

        Returns:
            Lista de instrucciones
        """
        instructions = []

        # Si hay más de 4 argumentos, los extras van al stack
        if arg_count > 4:
            extra_args = arg_count - 4
            stack_space = extra_args * 4
            instructions.append(f"subu $sp, $sp, {stack_space}  # Push extra args")

        return instructions

    def generate_caller_epilogue(self, arg_count: int) -> List[str]:
        """
        Genera el epílogo en el caller (después de call).

        Pasos:
        1. Limpiar argumentos del stack
        2. Restaurar registros caller-saved

        Args:
            arg_count: Número de argumentos

        Returns:
            Lista de instrucciones
        """
        instructions = []

        # Limpiar argumentos del stack
        if arg_count > 4:
            extra_args = arg_count - 4
            stack_space = extra_args * 4
            instructions.append(f"addu $sp, $sp, {stack_space}  # Pop extra args")

        return instructions

    def push_register(self, reg: MipsRegister, sp_offset: int) -> str:
        """
        Genera instrucción para guardar un registro en el stack.

        Args:
            reg: Registro a guardar
            sp_offset: Offset relativo a $sp

        Returns:
            Instrucción MIPS (sw)
        """
        if reg.reg_type == RegisterType.ZERO:
            return f"# Skipping save of $zero"
        return f"sw ${reg.reg_type.value}, {sp_offset}($sp)  # Push {reg.name}"

    def pop_register(self, reg: MipsRegister, sp_offset: int) -> str:
        """
        Genera instrucción para restaurar un registro desde el stack.

        Args:
            reg: Registro a restaurar
            sp_offset: Offset relativo a $sp

        Returns:
            Instrucción MIPS (lw)
        """
        if reg.reg_type == RegisterType.ZERO:
            return f"# Skipping load to $zero"
        return f"lw ${reg.reg_type.value}, {sp_offset}($sp)  # Pop {reg.name}"

    def push_temp_registers(self, registers: List[MipsRegister]) -> List[str]:
        """
        Genera instrucciones para guardar múltiples registros temporales.

        Args:
            registers: Lista de registros a guardar

        Returns:
            Lista de instrucciones MIPS
        """
        if not registers:
            return []

        instructions = []
        space_needed = len(registers) * 4

        # Hacer espacio en el stack
        instructions.append(f"subu $sp, $sp, {space_needed}  # Push {len(registers)} temps")

        # Guardar registros
        for i, reg in enumerate(registers):
            offset = i * 4
            instructions.append(self.push_register(reg, offset))

        return instructions

    def pop_temp_registers(self, registers: List[MipsRegister]) -> List[str]:
        """
        Genera instrucciones para restaurar múltiples registros temporales.

        Args:
            registers: Lista de registros a restaurar (en orden)

        Returns:
            Lista de instrucciones MIPS
        """
        if not registers:
            return []

        instructions = []

        # Restaurar registros en orden inverso
        for i in range(len(registers) - 1, -1, -1):
            reg = registers[i]
            offset = i * 4
            instructions.append(self.pop_register(reg, offset))

        # Liberar espacio del stack
        space_freed = len(registers) * 4
        instructions.append(f"addu $sp, $sp, {space_freed}  # Pop {len(registers)} temps")

        return instructions

    # ========== UTILIDADES ==========

    def get_register_by_type(self, reg_type: RegisterType) -> MipsRegister:
        """Obtiene un MipsRegister por su tipo"""
        return self.register_map.get(reg_type)

    def get_argument_registers(self) -> List[MipsRegister]:
        """Obtiene los registros de argumentos (a0-a3)"""
        return [self.register_map[rt] for rt in [
            RegisterType.A0, RegisterType.A1, RegisterType.A2, RegisterType.A3
        ]]

    def get_return_registers(self) -> List[MipsRegister]:
        """Obtiene los registros de retorno (v0-v1)"""
        return [self.register_map[rt] for rt in [
            RegisterType.V0, RegisterType.V1
        ]]

    def get_temporary_registers(self) -> List[MipsRegister]:
        """Obtiene todos los registros temporales (caller-saved)"""
        return [self.register_map[rt] for rt in [
            RegisterType.T0, RegisterType.T1, RegisterType.T2, RegisterType.T3,
            RegisterType.T4, RegisterType.T5, RegisterType.T6, RegisterType.T7,
            RegisterType.T8, RegisterType.T9
        ]]

    def get_saved_registers(self) -> List[MipsRegister]:
        """Obtiene todos los registros salvados (callee-saved)"""
        return self.callee_saved_regs

    def is_caller_saved(self, reg: MipsRegister) -> bool:
        """Verifica si un registro es caller-saved"""
        return reg.is_caller_saved

    def is_callee_saved(self, reg: MipsRegister) -> bool:
        """Verifica si un registro es callee-saved"""
        return reg.is_callee_saved

    def reset(self):
        """Reinicia el manager"""
        self.register_allocator.reset()
        self.current_frame = None
        self.function_stack.clear()

    def get_stack_depth(self) -> int:
        """Obtiene la profundidad del stack de frames"""
        return len(self.function_stack)

    def __repr__(self) -> str:
        if self.current_frame:
            return f"StackManager(depth={self.get_stack_depth()}, frame={self.current_frame})"
        return f"StackManager(depth={self.get_stack_depth()}, no_frame)"

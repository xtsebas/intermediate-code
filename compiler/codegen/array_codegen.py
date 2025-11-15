from typing import Optional, Union
from compiler.ir.triplet import OpCode, Operand
from compiler.ir.emitter import TripletEmitter
from compiler.ir.triplet import var_operand, const_operand, temp_operand
from compiler.symtab.memory_model import MemoryManager, MemoryAddress, DataType


class ArrayInfo:
    """Información de un arreglo para generación de código"""
    def __init__(self, name: str, element_type: str, size: int, base_address: MemoryAddress):
        self.name = name
        self.element_type = element_type
        self.size = size  # Número de elementos
        self.base_address = base_address  # Dirección base del arreglo
        self.element_size = DataType.get_size(element_type)

    def __repr__(self):
        return f"ArrayInfo({self.name}, {self.element_type}[{self.size}], base={self.base_address})"


class ArrayCodeGen:
    """
    Generador de código para arreglos con direcciones efectivas.

    Calcula direcciones efectivas de la forma:
    effective_address = base_address + (index * element_size)

    Incluye verificación de límites (bounds checking) opcional.
    """

    def __init__(self, emitter: TripletEmitter, memory_manager: MemoryManager):
        self.emitter = emitter
        self.memory_manager = memory_manager
        self.arrays = {}  # Diccionario de arreglos declarados
        self.bounds_checking = True  # Flag para activar/desactivar bounds checking

    def gen_array_allocation(self, array_name: str, element_type: str,
                            size: int, is_global: bool = False) -> ArrayInfo:
        """
        Genera código para declarar y asignar un arreglo.

        Emite:
        1. ARRAY_ALLOC para reservar memoria
        2. Almacena la dirección base

        Args:
            array_name: Nombre del arreglo
            element_type: Tipo de los elementos ("integer", "string", etc.)
            size: Número de elementos
            is_global: Si es variable global o local

        Returns:
            ArrayInfo con información del arreglo
        """
        # Asignar dirección en el segmento apropiado
        if is_global:
            base_address = self.memory_manager.allocate_global(
                array_name, element_type, array_size=size
            )
        else:
            base_address = self.memory_manager.allocate_local(
                array_name, element_type, array_size=size
            )

        # Crear información del arreglo
        array_info = ArrayInfo(array_name, element_type, size, base_address)
        self.arrays[array_name] = array_info

        # Generar triplet ARRAY_ALLOC
        # array_alloc size, element_size -> base_address
        element_size = DataType.get_size(element_type)
        total_bytes = size * element_size

        self.emitter.emit(
            OpCode.ARRAY_ALLOC,
            const_operand(size),           # arg1: número de elementos
            const_operand(element_size),   # arg2: tamaño de cada elemento
            var_operand(array_name),       # result: variable arreglo
            comment=f"Allocate {array_name}[{size}] at {base_address}, {total_bytes} bytes"
        )

        return array_info

    def gen_effective_address(self, array_name: str, index: Union[str, Operand]) -> str:
        """
        Calcula la dirección efectiva para acceso a arreglo.

        Fórmula: effective_addr = base_address + (index * element_size)

        Emite la secuencia de triplets:
        1. t1 = index * element_size     (cálculo del offset)
        2. t2 = base_address + t1        (dirección efectiva)

        Args:
            array_name: Nombre del arreglo
            index: Índice (puede ser constante, variable o temporal)

        Returns:
            Nombre del temporal con la dirección efectiva
        """
        array_info = self.arrays.get(array_name)
        if not array_info:
            raise ValueError(f"Arreglo '{array_name}' no ha sido declarado")

        # Convertir index a Operand si es necesario
        if isinstance(index, str):
            index = var_operand(index)

        # 1. Calcular offset: t_offset = index * element_size
        t_offset = self.emitter.new_temp()
        self.emitter.emit(
            OpCode.MUL,
            index,
            const_operand(array_info.element_size),
            temp_operand(t_offset),
            comment=f"Offset = index * {array_info.element_size}"
        )

        # 2. Calcular dirección efectiva: t_addr = base + offset
        t_addr = self.emitter.new_temp()

        # Crear operando con la dirección base formateada
        base_addr_str = str(array_info.base_address)  # Formato: G[offset] o L[offset]

        self.emitter.emit(
            OpCode.ADD,
            var_operand(base_addr_str),
            temp_operand(t_offset),
            temp_operand(t_addr),
            comment=f"Effective address = {base_addr_str} + offset"
        )

        return t_addr

    def gen_bounds_check(self, array_name: str, index: Union[str, Operand]) -> str:
        """
        Genera código para verificación de límites (bounds checking).

        Verifica que: 0 <= index < array_size

        Emite:
        1. Verificación index >= 0
        2. Verificación index < size
        3. Salto a error si está fuera de límites

        Args:
            array_name: Nombre del arreglo
            index: Índice a verificar

        Returns:
            Label de continuación (después del check)
        """
        if not self.bounds_checking:
            # Si bounds checking está desactivado, solo retornar label dummy
            return self.emitter.new_label('bounds_ok')

        array_info = self.arrays.get(array_name)
        if not array_info:
            raise ValueError(f"Arreglo '{array_name}' no ha sido declarado")

        # Convertir index a Operand
        if isinstance(index, str):
            index = var_operand(index)

        # Labels para control de flujo
        error_label = self.emitter.new_label('bounds_error')
        ok_label = self.emitter.new_label('bounds_ok')

        # 1. Verificar index >= 0
        # if index < 0 goto error_label
        self.emitter.emit(
            OpCode.BLT,
            index,
            const_operand(0),
            var_operand(error_label),
            comment=f"Check {array_name}[index] >= 0"
        )

        # 2. Verificar index < size
        # if index >= size goto error_label
        self.emitter.emit(
            OpCode.BGE,
            index,
            const_operand(array_info.size),
            var_operand(error_label),
            comment=f"Check {array_name}[index] < {array_info.size}"
        )

        # Si pasó las verificaciones, saltar a ok
        self.emitter.emit_jump(ok_label)

        # Label de error
        self.emitter.emit_label(error_label)

        # Emitir instrucción de error (puede ser print o trap)
        t_msg = self.emitter.new_temp()
        self.emitter.emit(
            OpCode.MOV,
            const_operand(f"Array index out of bounds"),
            None,
            temp_operand(t_msg),
            comment="Error message"
        )
        self.emitter.emit(OpCode.PRINT, temp_operand(t_msg))

        # Terminar programa (o lanzar excepción)
        # Para simplificar, usamos un jump infinito o RETURN
        halt_label = self.emitter.new_label('halt')
        self.emitter.emit_label(halt_label)
        self.emitter.emit_jump(halt_label)  # Loop infinito = halt

        # Label de continuación
        self.emitter.emit_label(ok_label)

        return ok_label

    def gen_array_access(self, array_name: str, index: Union[str, Operand],
                        result_var: Optional[str] = None,
                        check_bounds: bool = True) -> str:
        """
        Genera código completo para acceso de lectura a arreglo.

        Secuencia completa:
        1. (Opcional) Bounds checking
        2. Calcular dirección efectiva
        3. ARRAY_GET para leer el valor

        Args:
            array_name: Nombre del arreglo
            index: Índice
            result_var: Variable destino (opcional)
            check_bounds: Si debe hacer bounds checking

        Returns:
            Nombre del temporal con el valor leído
        """
        # 1. Bounds checking (si está habilitado)
        if check_bounds and self.bounds_checking:
            self.gen_bounds_check(array_name, index)

        # 2. Generar ARRAY_GET en forma clásica: ARRAY_GET array, index -> result
        if result_var is None:
            result_var = self.emitter.new_temp()

        # Normalizar índice a Operand
        idx_operand: Operand
        if isinstance(index, Operand):
            idx_operand = index
        elif isinstance(index, str):
            idx_operand = var_operand(index)
        else:
            idx_operand = const_operand(index)

        self.emitter.emit(
            OpCode.ARRAY_GET,
            var_operand(array_name),
            idx_operand,
            temp_operand(result_var),
            comment=f"Load {array_name}[index]"
        )

        return result_var

    def gen_array_assignment(self, array_name: str, index: Union[str, Operand],
                            value: Union[str, Operand],
                            check_bounds: bool = True) -> int:
        """
        Genera código completo para asignación a arreglo.

        Secuencia completa:
        1. (Opcional) Bounds checking
        2. Calcular dirección efectiva
        3. ARRAY_SET para escribir el valor

        Args:
            array_name: Nombre del arreglo
            index: Índice
            value: Valor a asignar
            check_bounds: Si debe hacer bounds checking

        Returns:
            Índice del triplet generado
        """
        # 1. Bounds checking (si está habilitado)
        if check_bounds and self.bounds_checking:
            self.gen_bounds_check(array_name, index)

        # 2. Normalizar índice y valor a Operand
        if isinstance(index, Operand):
            idx_operand = index
        elif isinstance(index, str):
            idx_operand = var_operand(index)
        else:
            idx_operand = const_operand(index)

        if isinstance(value, Operand):
            val_operand_ = value
        elif isinstance(value, str):
            val_operand_ = var_operand(value)
        else:
            val_operand_ = const_operand(value)

        # 3. Generar ARRAY_SET en forma clásica: ARRAY_SET array, index, value
        triplet_index = self.emitter.emit(
            OpCode.ARRAY_SET,
            var_operand(array_name),
            idx_operand,
            val_operand_,
            comment=f"Store to {array_name}[index]"
        )

        return triplet_index

    def get_array_info(self, array_name: str) -> Optional[ArrayInfo]:
        """Obtiene información de un arreglo declarado"""
        return self.arrays.get(array_name)

    def set_bounds_checking(self, enabled: bool):
        """Activa o desactiva bounds checking"""
        self.bounds_checking = enabled

    def get_all_arrays(self):
        """Retorna todos los arreglos declarados"""
        return self.arrays.copy()

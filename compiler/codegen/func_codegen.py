from typing import List, Optional, Dict
from compiler.ir.triplet import OpCode, Operand
from compiler.ir.emitter import TripletEmitter
from compiler.ir.triplet import func_operand, const_operand, var_operand, temp_operand


class FunctionInfo:
    """Informaci�n de una funci�n para generaci�n de c�digo"""
    def __init__(self, name: str, params: List[str], return_type: str = "void"):
        self.name = name
        self.params = params
        self.param_count = len(params)
        self.return_type = return_type
        self.local_vars: List[str] = []
        self.stack_size = 0

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local y actualiza el tama�o del stack"""
        self.local_vars.append(var_name)
        self.stack_size += size

    def get_param_offset(self, param_name: str) -> Optional[int]:
        """Obtiene el offset de un par�metro en el stack"""
        try:
            index = self.params.index(param_name)
            # Los par�metros se pasan en orden inverso (convenci�n)
            # Offset desde el frame pointer
            return 8 + (self.param_count - index - 1) * 4
        except ValueError:
            return None

    def __repr__(self):
        return f"FunctionInfo({self.name}, params={self.params}, stack={self.stack_size})"


class FuncCodeGen:
    """Generador de c�digo para funciones y llamadas"""

    def __init__(self, emitter: TripletEmitter):
        self.emitter = emitter
        self.functions: Dict[str, FunctionInfo] = {}
        self.current_function: Optional[FunctionInfo] = None

    def gen_function_prolog(self, func_name: str, params: List[str],
                           return_type: str = "void") -> None:
        """
        Genera el pr�logo de una funci�n.

        Pr�logo incluye:
        1. Etiqueta de inicio de funci�n
        2. ENTER con nombre de funci�n y cantidad de par�metros
        3. Reserva de espacio para variables locales (si es necesario)

        Args:
            func_name: Nombre de la funci�n
            params: Lista de nombres de par�metros
            return_type: Tipo de retorno de la funci�n
        """
        # Crear informaci�n de la funci�n
        func_info = FunctionInfo(func_name, params, return_type)
        self.functions[func_name] = func_info
        self.current_function = func_info

        # Generar etiqueta de inicio
        func_label = self.emitter.new_label('func_start')
        self.emitter.emit_label(func_label)

        # ENTER: Indica inicio de funci�n con nombre y cantidad de par�metros
        # enter func_name, param_count
        self.emitter.emit(
            OpCode.ENTER,
            func_operand(func_name),
            const_operand(len(params)),
            comment=f"Prolog: {func_name}({', '.join(params)})"
        )

        # Cargar par�metros a variables locales
        # Los par�metros vienen del stack/registros seg�n convenci�n de llamada
        for i, param in enumerate(params):
            # Emitir instrucci�n para mover par�metro a variable local
            self.emitter.emit(
                OpCode.MOV,
                var_operand(f"param_{i}"),  # Fuente: par�metro pasado
                None,
                var_operand(param),  # Destino: variable local
                comment=f"Load param {param}"
            )

    def gen_function_epilog(self, func_name: Optional[str] = None) -> None:
        """
        Genera el ep�logo de una funci�n.

        Ep�logo incluye:
        1. EXIT con nombre de funci�n
        2. Etiqueta de fin de funci�n
        3. Limpieza del stack frame

        Args:
            func_name: Nombre de la funci�n (opcional, usa current_function si no se provee)
        """
        if func_name is None and self.current_function:
            func_name = self.current_function.name

        if not func_name:
            raise ValueError("No hay funci�n activa para generar ep�logo")

        # EXIT: Indica fin de funci�n
        self.emitter.emit(
            OpCode.EXIT,
            func_operand(func_name),
            comment=f"Epilog: {func_name}"
        )

        # Generar etiqueta de fin
        end_label = self.emitter.new_label('func_end')
        self.emitter.emit_label(end_label)

        # Limpiar funci�n actual
        self.current_function = None

    def gen_return(self, value: Optional[Operand] = None) -> int:
        """
        Genera c�digo para retorno de funci�n.

        Args:
            value: Valor a retornar (opcional para void functions)

        Returns:
            �ndice del triplet generado
        """
        if value is not None:
            # return value
            return self.emitter.emit(
                OpCode.RETURN,
                value,
                comment=f"Return {value}"
            )
        else:
            # return (void)
            return self.emitter.emit(
                OpCode.RETURN,
                comment="Return void"
            )

    def gen_param_push(self, args: List[Operand]) -> List[int]:
        """
        Genera c�digo para pasar par�metros por valor.

        Los par�metros se pasan en el orden que se reciben.

        Args:
            args: Lista de argumentos/par�metros a pasar

        Returns:
            Lista de �ndices de triplets generados
        """
        triplet_indices = []

        for i, arg in enumerate(args):
            # param arg
            index = self.emitter.emit(
                OpCode.PARAM,
                arg,
                comment=f"Push param {i}: {arg}"
            )
            triplet_indices.append(index)

        return triplet_indices

    def gen_function_call(self, func_name: str, args: List[Operand],
                         result_var: Optional[str] = None) -> str:
        """
        Genera c�digo para llamada a funci�n.

        Secuencia:
        1. Pasar par�metros (PARAM para cada argumento)
        2. CALL con nombre de funci�n y cantidad de argumentos
        3. Almacenar resultado en temporal/variable

        Args:
            func_name: Nombre de la funci�n a llamar
            args: Lista de argumentos
            result_var: Variable donde almacenar resultado (opcional)

        Returns:
            Nombre del temporal/variable con el resultado
        """
        # 1. Pasar par�metros
        self.gen_param_push(args)

        # 2. Determinar donde guardar el resultado
        if result_var is None:
            result_var = self.emitter.new_temp()

        # 3. Generar CALL
        # call func_name, arg_count -> result
        self.emitter.emit(
            OpCode.CALL,
            func_operand(func_name),
            const_operand(len(args)),
            temp_operand(result_var) if not result_var.startswith('_') else var_operand(result_var),
            comment=f"Call {func_name}({len(args)} args)"
        )

        return result_var

    def get_function_info(self, func_name: str) -> Optional[FunctionInfo]:
        """Obtiene informaci�n de una funci�n definida"""
        return self.functions.get(func_name)

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local a la funci�n actual"""
        if self.current_function:
            self.current_function.add_local_var(var_name, size)

    def enter_function_scope(self, func_name: str) -> bool:
        """Entra al scope de una funci�n (para visitor)"""
        if func_name in self.functions:
            self.current_function = self.functions[func_name]
            return True
        return False

    def exit_function_scope(self):
        """Sale del scope de funci�n actual"""
        self.current_function = None

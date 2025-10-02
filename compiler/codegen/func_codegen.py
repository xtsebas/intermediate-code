from typing import List, Optional, Dict
from compiler.ir.triplet import OpCode, Operand
from compiler.ir.emitter import TripletEmitter
from compiler.ir.triplet import func_operand, const_operand, var_operand, temp_operand


class FunctionInfo:
    """Información de una función para generación de código"""
    def __init__(self, name: str, params: List[str], return_type: str = "void"):
        self.name = name
        self.params = params
        self.param_count = len(params)
        self.return_type = return_type
        self.local_vars: List[str] = []
        self.stack_size = 0

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local y actualiza el tamaño del stack"""
        self.local_vars.append(var_name)
        self.stack_size += size

    def get_param_offset(self, param_name: str) -> Optional[int]:
        """Obtiene el offset de un parámetro en el stack"""
        try:
            index = self.params.index(param_name)
            # Los parámetros se pasan en orden inverso (convención)
            # Offset desde el frame pointer
            return 8 + (self.param_count - index - 1) * 4
        except ValueError:
            return None

    def __repr__(self):
        return f"FunctionInfo({self.name}, params={self.params}, stack={self.stack_size})"


class FuncCodeGen:
    """Generador de código para funciones y llamadas"""

    def __init__(self, emitter: TripletEmitter):
        self.emitter = emitter
        self.functions: Dict[str, FunctionInfo] = {}
        self.current_function: Optional[FunctionInfo] = None

    def gen_function_prolog(self, func_name: str, params: List[str],
                           return_type: str = "void") -> None:
        """
        Genera el prólogo de una función.

        Prólogo incluye:
        1. Etiqueta de inicio de función
        2. ENTER con nombre de función y cantidad de parámetros
        3. Reserva de espacio para variables locales (si es necesario)

        Args:
            func_name: Nombre de la función
            params: Lista de nombres de parámetros
            return_type: Tipo de retorno de la función
        """
        # Crear información de la función
        func_info = FunctionInfo(func_name, params, return_type)
        self.functions[func_name] = func_info
        self.current_function = func_info

        # Generar etiqueta de inicio
        func_label = self.emitter.new_label('func_start')
        self.emitter.emit_label(func_label)

        # ENTER: Indica inicio de función con nombre y cantidad de parámetros
        # enter func_name, param_count
        self.emitter.emit(
            OpCode.ENTER,
            func_operand(func_name),
            const_operand(len(params)),
            comment=f"Prolog: {func_name}({', '.join(params)})"
        )

        # Cargar parámetros a variables locales
        # Los parámetros vienen del stack/registros según convención de llamada
        for i, param in enumerate(params):
            # Emitir instrucción para mover parámetro a variable local
            self.emitter.emit(
                OpCode.MOV,
                var_operand(f"param_{i}"),  # Fuente: parámetro pasado
                None,
                var_operand(param),  # Destino: variable local
                comment=f"Load param {param}"
            )

    def gen_function_epilog(self, func_name: Optional[str] = None) -> None:
        """
        Genera el epílogo de una función.

        Epílogo incluye:
        1. EXIT con nombre de función
        2. Etiqueta de fin de función
        3. Limpieza del stack frame

        Args:
            func_name: Nombre de la función (opcional, usa current_function si no se provee)
        """
        if func_name is None and self.current_function:
            func_name = self.current_function.name

        if not func_name:
            raise ValueError("No hay función activa para generar epílogo")

        # EXIT: Indica fin de función
        self.emitter.emit(
            OpCode.EXIT,
            func_operand(func_name),
            comment=f"Epilog: {func_name}"
        )

        # Generar etiqueta de fin
        end_label = self.emitter.new_label('func_end')
        self.emitter.emit_label(end_label)

        # Limpiar función actual
        self.current_function = None

    def gen_return(self, value: Optional[Operand] = None) -> int:
        """
        Genera código para retorno de función.

        Args:
            value: Valor a retornar (opcional para void functions)

        Returns:
            Índice del triplet generado
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
        Genera código para pasar parámetros por valor.

        Los parámetros se pasan en el orden que se reciben.

        Args:
            args: Lista de argumentos/parámetros a pasar

        Returns:
            Lista de índices de triplets generados
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
        Genera código para llamada a función.

        Secuencia:
        1. Pasar parámetros (PARAM para cada argumento)
        2. CALL con nombre de función y cantidad de argumentos
        3. Almacenar resultado en temporal/variable

        Args:
            func_name: Nombre de la función a llamar
            args: Lista de argumentos
            result_var: Variable donde almacenar resultado (opcional)

        Returns:
            Nombre del temporal/variable con el resultado
        """
        # 1. Pasar parámetros
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
        """Obtiene información de una función definida"""
        return self.functions.get(func_name)

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local a la función actual"""
        if self.current_function:
            self.current_function.add_local_var(var_name, size)

    def enter_function_scope(self, func_name: str) -> bool:
        """Entra al scope de una función (para visitor)"""
        if func_name in self.functions:
            self.current_function = self.functions[func_name]
            return True
        return False

    def exit_function_scope(self):
        """Sale del scope de función actual"""
        self.current_function = None

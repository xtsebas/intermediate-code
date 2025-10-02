# -*- coding: utf-8 -*-
from typing import List, Optional, Dict
from compiler.ir.triplet import OpCode, Operand
from compiler.ir.emitter import TripletEmitter
from compiler.ir.triplet import func_operand, const_operand, var_operand, temp_operand


class FunctionInfo:
    """Informacion de una funcion para generacion de codigo"""
    def __init__(self, name: str, params: List[str], return_type: str = "void"):
        self.name = name
        self.params = params
        self.param_count = len(params)
        self.return_type = return_type
        self.local_vars: List[str] = []
        self.stack_size = 0

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local y actualiza el tamano del stack"""
        self.local_vars.append(var_name)
        self.stack_size += size

    def get_param_offset(self, param_name: str) -> Optional[int]:
        """Obtiene el offset de un parametro en el stack"""
        try:
            index = self.params.index(param_name)
            # Los parametros se pasan en orden inverso (convencion)
            # Offset desde el frame pointer
            return 8 + (self.param_count - index - 1) * 4
        except ValueError:
            return None

    def __repr__(self):
        return f"FunctionInfo({self.name}, params={self.params}, stack={self.stack_size})"


class FuncCodeGen:
    """Generador de codigo para funciones y llamadas"""

    def __init__(self, emitter: TripletEmitter):
        self.emitter = emitter
        self.functions: Dict[str, FunctionInfo] = {}
        self.current_function: Optional[FunctionInfo] = None

    def gen_function_prolog(self, func_name: str, params: List[str],
                           return_type: str = "void") -> None:
        """
        Genera el prologo de una funcion.

        Prologo incluye:
        1. Etiqueta de inicio de funcion
        2. ENTER con nombre de funcion y cantidad de parametros
        3. Reserva de espacio para variables locales (si es necesario)

        Args:
            func_name: Nombre de la funcion
            params: Lista de nombres de parametros
            return_type: Tipo de retorno de la funcion
        """
        # Crear informacion de la funcion
        func_info = FunctionInfo(func_name, params, return_type)
        self.functions[func_name] = func_info
        self.current_function = func_info

        # Generar etiqueta de inicio
        func_label = self.emitter.new_label('func_start')
        self.emitter.emit_label(func_label)

        # ENTER: Indica inicio de funcion con nombre y cantidad de parametros
        # enter func_name, param_count
        self.emitter.emit(
            OpCode.ENTER,
            func_operand(func_name),
            const_operand(len(params)),
            comment=f"Prolog: {func_name}({', '.join(params)})"
        )

        # Cargar parametros a variables locales
        # Los parametros vienen del stack/registros segun convencion de llamada
        for i, param in enumerate(params):
            # Emitir instruccion para mover parametro a variable local
            self.emitter.emit(
                OpCode.MOV,
                var_operand(f"param_{i}"),  # Fuente: parametro pasado
                None,
                var_operand(param),  # Destino: variable local
                comment=f"Load param {param}"
            )

    def gen_function_epilog(self, func_name: Optional[str] = None) -> None:
        """
        Genera el epilogo de una funcion.

        Epilogo incluye:
        1. EXIT con nombre de funcion
        2. Etiqueta de fin de funcion
        3. Limpieza del stack frame

        Args:
            func_name: Nombre de la funcion (opcional, usa current_function si no se provee)
        """
        if func_name is None and self.current_function:
            func_name = self.current_function.name

        if not func_name:
            raise ValueError("No hay funcion activa para generar epilogo")

        # EXIT: Indica fin de funcion
        self.emitter.emit(
            OpCode.EXIT,
            func_operand(func_name),
            comment=f"Epilog: {func_name}"
        )

        # Generar etiqueta de fin
        end_label = self.emitter.new_label('func_end')
        self.emitter.emit_label(end_label)

        # Limpiar funcion actual
        self.current_function = None

    def gen_return(self, value: Optional[Operand] = None) -> int:
        """
        Genera codigo para retorno de funcion.

        Args:
            value: Valor a retornar (opcional para void functions)

        Returns:
            Indice del triplet generado
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
        Genera codigo para pasar parametros por valor.

        Los parametros se pasan en el orden que se reciben.

        Args:
            args: Lista de argumentos/parametros a pasar

        Returns:
            Lista de indices de triplets generados
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
        Genera codigo para llamada a funcion.

        Secuencia:
        1. Pasar parametros (PARAM para cada argumento)
        2. CALL con nombre de funcion y cantidad de argumentos
        3. Almacenar resultado en temporal/variable

        Args:
            func_name: Nombre de la funcion a llamar
            args: Lista de argumentos
            result_var: Variable donde almacenar resultado (opcional)

        Returns:
            Nombre del temporal/variable con el resultado
        """
        # 1. Pasar parametros
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
        """Obtiene informacion de una funcion definida"""
        return self.functions.get(func_name)

    def add_local_var(self, var_name: str, size: int = 4):
        """Agrega una variable local a la funcion actual"""
        if self.current_function:
            self.current_function.add_local_var(var_name, size)

    def enter_function_scope(self, func_name: str) -> bool:
        """Entra al scope de una funcion (para visitor)"""
        if func_name in self.functions:
            self.current_function = self.functions[func_name]
            return True
        return False

    def exit_function_scope(self):
        """Sale del scope de funcion actual"""
        self.current_function = None

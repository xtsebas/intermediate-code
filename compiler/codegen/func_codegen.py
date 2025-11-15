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
        # Detectar si ya existía una función con el mismo nombre
        already_defined = func_name in self.functions

        func_info = FunctionInfo(func_name, params, return_type)
        self.functions[func_name] = func_info
        self.current_function = func_info

        # Label interno único para control de flujo
        func_label = self.emitter.new_label('func_start')
        self.emitter.emit_label(func_label)

        # Label público con el nombre de la función, usado por CALL/jal.
        # Solo se emite la primera vez para evitar redefinir labels (p.ej. métodos con el mismo nombre).
        if not already_defined:
            self.emitter.emit_label(func_name)

        # BeginFunc con tamaño estimado del frame
        frame_size = len(params) * 4 + 32  # params + espacio para locales
        self.emitter.emit(
            OpCode.ENTER,
            const_operand(frame_size),
            None,
            None
        )

    def gen_function_epilog(self, func_name: Optional[str] = None) -> None:
        if func_name is None and self.current_function:
            func_name = self.current_function.name

        if not func_name:
            raise ValueError("No hay función activa para generar epilog")

        # EndFunc simple
        self.emitter.emit(
            OpCode.EXIT,
            None,
            None,
            None
        )

        end_label = self.emitter.new_label('func_end')
        self.emitter.emit_label(end_label)

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
        triplet_indices = []

        for i, arg in enumerate(args):
            index = self.emitter.emit(
                OpCode.PARAM,
                arg,
                None,
                None,
                comment=f"Push param {i}"
            )
            triplet_indices.append(index)

        return triplet_indices

    def gen_function_call(self, func_name: str, args: List[Operand],
                     result_var: Optional[str] = None) -> str:
        # Generar PARAM para cada argumento
        for i, arg in enumerate(args):
            if isinstance(arg, str):
                # Es un temporal o variable
                self.emitter.emit(
                    OpCode.PARAM,
                    arg,
                    None,
                    None
                )
            else:
                self.emitter.emit(
                    OpCode.PARAM,
                    str(arg),
                    None,
                    None
                )
        
        # Crear temporal para el resultado si no se proporciona
        if result_var is None:
            result_var = self.emitter.new_temp()
        
        # Generar CALL
        self.emitter.emit(
            OpCode.CALL,
            func_name,
            len(args),
            result_var
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

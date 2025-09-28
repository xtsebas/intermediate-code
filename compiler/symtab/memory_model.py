from typing import Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass


class MemorySegment(Enum):
    """Segmentos de memoria disponibles"""
    GLOBAL = "G"      
    LOCAL = "L"       
    TEMP = "T"        
    PARAM = "P"       
    CONST = "C"       
    HEAP = "H"        


@dataclass
class MemoryAddress:
    """
    Representa una dirección de memoria con segmento y offset.
    
    Formato: SEGMENTO[offset]
    Ejemplos: G[0], L[4], T[8], P[0]
    """
    segment: MemorySegment
    offset: int
    size: int = 4  
    
    def __str__(self) -> str:
        return f"{self.segment.value}[{self.offset}]"
    
    def __repr__(self) -> str:
        return f"MemoryAddress({self.segment}, {self.offset}, {self.size})"
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            "segment": self.segment.value,
            "offset": self.offset,
            "size": self.size,
            "address": str(self)
        }


class DataType(Enum):
    """Tipos de datos soportados y sus tamaños"""
    INTEGER = ("integer", 4)
    STRING = ("string", 8)    
    BOOLEAN = ("boolean", 1)
    NULL = ("null", 4)
    ARRAY = ("array", 8)      
    OBJECT = ("object", 8)    
    FUNCTION = ("function", 8) 
    
    def __init__(self, type_name: str, size: int):
        self.type_name = type_name
        self.size = size
    
    @classmethod
    def get_size(cls, type_name: str) -> int:
        """Obtiene el tamaño de un tipo"""
        for data_type in cls:
            if data_type.type_name == type_name:
                return data_type.size
        return 4  


class MemoryAllocator:
    """
    Asignador de direcciones de memoria para un segmento específico.
    Mantiene el offset actual y asigna direcciones secuenciales.
    """
    
    def __init__(self, segment: MemorySegment, start_offset: int = 0):
        self.segment = segment
        self.current_offset = start_offset
        self.allocated_vars: Dict[str, MemoryAddress] = {}
        self.max_offset = start_offset
    
    def allocate(self, var_name: str, type_name: str, 
                array_size: Optional[int] = None) -> MemoryAddress:
        """
        Asigna una dirección de memoria para una variable.
        
        Args:
            var_name: nombre de la variable
            type_name: tipo de la variable
            array_size: tamaño del array si es un array
            
        Returns:
            MemoryAddress: dirección asignada
        """
        
        if array_size is not None:
            
            element_size = DataType.get_size(type_name)
            size = 8 + (array_size * element_size)  
        else:
            size = DataType.get_size(type_name)
        
        
        aligned_size = ((size + 3) // 4) * 4
        
        
        address = MemoryAddress(self.segment, self.current_offset, aligned_size)
        
        
        self.allocated_vars[var_name] = address
        
        
        self.current_offset += aligned_size
        self.max_offset = max(self.max_offset, self.current_offset)
        
        return address
    
    def get_address(self, var_name: str) -> Optional[MemoryAddress]:
        """Obtiene la dirección de una variable"""
        return self.allocated_vars.get(var_name)
    
    def deallocate(self, var_name: str) -> bool:
        """
        Libera la dirección de una variable.
        Nota: No compacta memoria, solo marca como libre.
        """
        if var_name in self.allocated_vars:
            del self.allocated_vars[var_name]
            return True
        return False
    
    def get_size(self) -> int:
        """Retorna el tamaño total usado en este segmento"""
        return self.max_offset
    
    def reset(self, start_offset: int = 0):
        """Reinicia el asignador"""
        self.current_offset = start_offset
        self.allocated_vars.clear()
        self.max_offset = start_offset
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del asignador"""
        return {
            "segment": self.segment.value,
            "current_offset": self.current_offset,
            "max_offset": self.max_offset,
            "allocated_count": len(self.allocated_vars),
            "total_size": self.get_size()
        }


class ActivationRecord:
    """
    Registro de activación para una función.
    Contiene información sobre parámetros, variables locales y temporales.
    """
    
    def __init__(self, function_name: str, parameters: List[str] = None):
        self.function_name = function_name
        self.parameters = parameters or []
        
        
        self.param_allocator = MemoryAllocator(MemorySegment.PARAM, 0)
        self.local_allocator = MemoryAllocator(MemorySegment.LOCAL, 0)
        self.temp_allocator = MemoryAllocator(MemorySegment.TEMP, 0)
        
        
        self.frame_size = 0
        self.return_address_offset = -4  
        self.old_bp_offset = -8          
        
        
        for i, param in enumerate(self.parameters):
            self.param_allocator.allocate(param, "integer")  
    
    def allocate_local(self, var_name: str, type_name: str, 
                      array_size: Optional[int] = None) -> MemoryAddress:
        """Asigna una variable local"""
        return self.local_allocator.allocate(var_name, type_name, array_size)
    
    def allocate_temp(self, temp_name: str) -> MemoryAddress:
        """Asigna una variable temporal"""
        return self.temp_allocator.allocate(temp_name, "integer")
    
    def get_local_address(self, var_name: str) -> Optional[MemoryAddress]:
        """Obtiene dirección de variable local"""
        return self.local_allocator.get_address(var_name)
    
    def get_param_address(self, param_name: str) -> Optional[MemoryAddress]:
        """Obtiene dirección de parámetro"""
        return self.param_allocator.get_address(param_name)
    
    def get_temp_address(self, temp_name: str) -> Optional[MemoryAddress]:
        """Obtiene dirección de temporal"""
        return self.temp_allocator.get_address(temp_name)
    
    def calculate_frame_size(self) -> int:
        """
        Calcula el tamaño total del frame de activación.
        
        Layout del frame:
        [BP-8]  old BP
        [BP-4]  return address  
        [BP+0]  BP (base pointer)
        [BP+4]  param 0
        [BP+8]  param 1
        ...
        [BP+n]  local vars
        [BP+m]  temporales
        """
        param_size = self.param_allocator.get_size()
        local_size = self.local_allocator.get_size()
        temp_size = self.temp_allocator.get_size()
        
        
        self.frame_size = 8 + param_size + local_size + temp_size
        return self.frame_size
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del registro de activación"""
        return {
            "function_name": self.function_name,
            "parameters": self.parameters,
            "frame_size": self.calculate_frame_size(),
            "param_stats": self.param_allocator.get_stats(),
            "local_stats": self.local_allocator.get_stats(),
            "temp_stats": self.temp_allocator.get_stats()
        }


class MemoryManager:
    """
    Gestor principal de memoria que coordina todos los segmentos
    y registros de activación.
    """
    
    def __init__(self):
        
        self.global_allocator = MemoryAllocator(MemorySegment.GLOBAL, 0)
        
        
        self.activation_stack: List[ActivationRecord] = []
        
        
        self.current_activation: Optional[ActivationRecord] = None
        
        
        self.const_allocator = MemoryAllocator(MemorySegment.CONST, 0)
        
        
        self.string_literals: Dict[str, MemoryAddress] = {}
        
        
        self.next_label_id = 0
    
    def allocate_global(self, var_name: str, type_name: str, 
                       array_size: Optional[int] = None) -> MemoryAddress:
        """Asigna una variable global"""
        return self.global_allocator.allocate(var_name, type_name, array_size)
    
    def allocate_local(self, var_name: str, type_name: str,
                      array_size: Optional[int] = None) -> MemoryAddress:
        """Asigna una variable local en el frame actual"""
        if not self.current_activation:
            raise RuntimeError("No hay función activa para asignar variable local")
        return self.current_activation.allocate_local(var_name, type_name, array_size)
    
    def allocate_temp(self, temp_name: str) -> MemoryAddress:
        """Asigna una variable temporal en el frame actual"""
        if not self.current_activation:
            
            return self.global_allocator.allocate(temp_name, "integer")
        return self.current_activation.allocate_temp(temp_name)
    
    def allocate_constant(self, value: Union[str, int, float, bool]) -> MemoryAddress:
        """
        Asigna espacio para una constante.
        Para strings, evita duplicados.
        """
        if isinstance(value, str):
            
            if value in self.string_literals:
                return self.string_literals[value]
            
            
            label = f"STR_{self.next_label_id}"
            self.next_label_id += 1
            address = self.const_allocator.allocate(label, "string")
            self.string_literals[value] = address
            return address
        else:
            
            label = f"CONST_{self.next_label_id}"
            self.next_label_id += 1
            type_name = "integer" if isinstance(value, int) else "boolean"
            return self.const_allocator.allocate(label, type_name)
    
    def enter_function(self, function_name: str, parameters: List[str] = None):
        """Entra a una nueva función, creando su registro de activación"""
        activation = ActivationRecord(function_name, parameters)
        self.activation_stack.append(activation)
        self.current_activation = activation
    
    def exit_function(self) -> Optional[ActivationRecord]:
        """Sale de la función actual"""
        if self.activation_stack:
            old_activation = self.activation_stack.pop()
            self.current_activation = self.activation_stack[-1] if self.activation_stack else None
            return old_activation
        return None
    
    def get_variable_address(self, var_name: str) -> Optional[MemoryAddress]:
        """
        Busca la dirección de una variable en el orden:
        1. Variables locales del frame actual
        2. Parámetros del frame actual
        3. Variables globales
        """
        
        if self.current_activation:
            
            address = self.current_activation.get_local_address(var_name)
            if address:
                return address
            
            
            address = self.current_activation.get_param_address(var_name)
            if address:
                return address
        
        
        return self.global_allocator.get_address(var_name)
    
    def get_temp_address(self, temp_name: str) -> Optional[MemoryAddress]:
        """Obtiene dirección de una temporal"""
        if self.current_activation:
            return self.current_activation.get_temp_address(temp_name)
        return self.global_allocator.get_address(temp_name)
    
    def get_current_frame_size(self) -> int:
        """Obtiene el tamaño del frame actual"""
        if self.current_activation:
            return self.current_activation.calculate_frame_size()
        return 0
    
    def clear(self):
        """Reinicia el gestor de memoria"""
        self.global_allocator.reset()
        self.const_allocator.reset()
        self.activation_stack.clear()
        self.current_activation = None
        self.string_literals.clear()
        self.next_label_id = 0
    
    def get_memory_layout(self) -> dict:
        """
        Retorna el layout completo de memoria para debugging.
        """
        layout = {
            "global_segment": self.global_allocator.get_stats(),
            "const_segment": self.const_allocator.get_stats(),
            "string_literals": {literal: str(addr) for literal, addr in self.string_literals.items()},
            "activation_stack_depth": len(self.activation_stack),
            "current_function": self.current_activation.function_name if self.current_activation else None
        }
        
        
        layout["activation_frames"] = []
        for i, activation in enumerate(self.activation_stack):
            frame_info = activation.get_stats()
            frame_info["stack_level"] = i
            layout["activation_frames"].append(frame_info)
        
        return layout
    
    def print_memory_layout(self):
        """Imprime el layout de memoria de forma legible"""
        layout = self.get_memory_layout()
        
        print("=== LAYOUT DE MEMORIA ===")
        print(f"Segmento Global: {layout['global_segment']['total_size']} bytes")
        print(f"Segmento Constantes: {layout['const_segment']['total_size']} bytes")
        print(f"Función Actual: {layout['current_function']}")
        print(f"Profundidad Stack: {layout['activation_stack_depth']}")
        
        if layout['activation_frames']:
            print("\n--- FRAMES DE ACTIVACIÓN ---")
            for frame in layout['activation_frames']:
                print(f"  Nivel {frame['stack_level']}: {frame['function_name']}")
                print(f"    Tamaño: {frame['frame_size']} bytes")
                print(f"    Parámetros: {frame['param_stats']['allocated_count']}")
                print(f"    Locales: {frame['local_stats']['allocated_count']}")
                print(f"    Temporales: {frame['temp_stats']['allocated_count']}")
        
        if layout['string_literals']:
            print("\n--- LITERALES STRING ---")
            for literal, address in layout['string_literals'].items():
                print(f"  \"{literal}\" -> {address}")



memory_manager = MemoryManager()
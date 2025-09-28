from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from .memory_model import MemoryAddress, MemorySegment, memory_manager


class SymbolKind(Enum):
    """Tipos de símbolos"""
    VARIABLE = "variable"
    CONSTANT = "constant"
    FUNCTION = "function"
    PARAMETER = "parameter"
    CLASS = "class"
    TEMPORARY = "temporary"


class Scope(Enum):
    """Alcances de símbolos"""
    GLOBAL = "global"
    LOCAL = "local"
    PARAMETER = "parameter"
    CLASS = "class"


@dataclass
class Symbol:
    """
    Representa un símbolo en la tabla de símbolos.
    Incluye información de tipo, dirección de memoria y metadatos.
    """
    name: str
    symbol_type: str  
    kind: SymbolKind
    scope: Scope
    
    
    address: Optional[MemoryAddress] = None
    size: int = 4  
    
    
    is_initialized: bool = False
    is_array: bool = False
    array_dimensions: List[int] = field(default_factory=list)
    
    
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    local_vars: Set[str] = field(default_factory=set)
    
    
    fields: Dict[str, 'Symbol'] = field(default_factory=dict)
    methods: Dict[str, 'Symbol'] = field(default_factory=dict)
    parent_class: Optional[str] = None
    
    
    line_number: Optional[int] = None
    column: Optional[int] = None
    
    def __post_init__(self):
        """Validaciones post-inicialización"""
        if self.is_array and not self.array_dimensions:
            self.array_dimensions = [0]  
    
    def get_total_size(self) -> int:
        """Calcula el tamaño total del símbolo"""
        if self.is_array:
            element_size = 4  
            total_elements = 1
            for dim in self.array_dimensions:
                total_elements *= max(dim, 1)
            return 8 + (total_elements * element_size)  
        return self.size
    
    def is_function(self) -> bool:
        """Verifica si es una función"""
        return self.kind == SymbolKind.FUNCTION
    
    def is_variable(self) -> bool:
        """Verifica si es una variable"""
        return self.kind in [SymbolKind.VARIABLE, SymbolKind.PARAMETER, SymbolKind.TEMPORARY]
    
    def is_class(self) -> bool:
        """Verifica si es una clase"""
        return self.kind == SymbolKind.CLASS
    
    def to_dict(self) -> dict:
        """Convierte el símbolo a diccionario para serialización"""
        return {
            "name": self.name,
            "type": self.symbol_type,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "address": self.address.to_dict() if self.address else None,
            "size": self.size,
            "total_size": self.get_total_size(),
            "is_initialized": self.is_initialized,
            "is_array": self.is_array,
            "array_dimensions": self.array_dimensions,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "line_number": self.line_number,
            "column": self.column
        }


class SymbolTable:
    """
    Tabla de símbolos que mantiene información sobre variables, funciones y clases.
    Integrada con el gestor de memoria para asignación de direcciones.
    """
    
    def __init__(self):
        
        self.scopes: List[Dict[str, Symbol]] = [{}]  
        self.current_scope_level = 0
        
        
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        
        
        self.temp_counter = 0
        self.label_counter = 0
        
        
        self.global_symbols: Dict[str, Symbol] = {}
        self.all_functions: Dict[str, Symbol] = {}
        self.all_classes: Dict[str, Symbol] = {}
    
    def enter_scope(self, scope_type: str = "block"):
        """
        Entra a un nuevo scope (bloque, función, clase).
        
        Args:
            scope_type: tipo de scope ("block", "function", "class")
        """
        self.scopes.append({})
        self.current_scope_level += 1
        
        if scope_type == "function":
            
            pass
        elif scope_type == "class":
            
            pass
    
    def exit_scope(self) -> Dict[str, Symbol]:
        """
        Sale del scope actual.
        
        Returns:
            Dict con los símbolos del scope que se cierra
        """
        if len(self.scopes) <= 1:
            raise RuntimeError("No se puede salir del scope global")
        
        closed_scope = self.scopes.pop()
        self.current_scope_level -= 1
        
        return closed_scope
    
    def declare_variable(self, name: str, var_type: str, 
                        is_constant: bool = False,
                        is_array: bool = False,
                        array_dimensions: List[int] = None,
                        line_number: Optional[int] = None) -> Symbol:
        """
        Declara una nueva variable en el scope actual.
        
        Args:
            name: nombre de la variable
            var_type: tipo de la variable
            is_constant: si es constante
            is_array: si es un array
            array_dimensions: dimensiones del array
            line_number: línea de declaración
            
        Returns:
            Symbol: símbolo creado
        """
        
        if name in self.scopes[self.current_scope_level]:
            raise RuntimeError(f"Variable '{name}' ya declarada en este scope")
        
        
        scope = Scope.GLOBAL if self.current_scope_level == 0 else Scope.LOCAL
        kind = SymbolKind.CONSTANT if is_constant else SymbolKind.VARIABLE
        
        
        symbol = Symbol(
            name=name,
            symbol_type=var_type,
            kind=kind,
            scope=scope,
            is_array=is_array,
            array_dimensions=array_dimensions or [],
            line_number=line_number
        )
        
        
        if scope == Scope.GLOBAL:
            symbol.address = memory_manager.allocate_global(
                name, var_type, 
                array_dimensions[0] if is_array and array_dimensions else None
            )
            self.global_symbols[name] = symbol
        else:
            symbol.address = memory_manager.allocate_local(
                name, var_type,
                array_dimensions[0] if is_array and array_dimensions else None
            )
        
        
        self.scopes[self.current_scope_level][name] = symbol
        
        return symbol
    
    def declare_parameter(self, name: str, param_type: str, 
                         line_number: Optional[int] = None) -> Symbol:
        """
        Declara un parámetro de función.
        
        Args:
            name: nombre del parámetro
            param_type: tipo del parámetro
            line_number: línea de declaración
            
        Returns:
            Symbol: símbolo del parámetro
        """
        if name in self.scopes[self.current_scope_level]:
            raise RuntimeError(f"Parámetro '{name}' ya declarado")
        
        symbol = Symbol(
            name=name,
            symbol_type=param_type,
            kind=SymbolKind.PARAMETER,
            scope=Scope.PARAMETER,
            line_number=line_number
        )
        
        
        
        if memory_manager.current_activation:
            symbol.address = memory_manager.current_activation.get_param_address(name)
        
        self.scopes[self.current_scope_level][name] = symbol
        return symbol
    
    def declare_function(self, name: str, return_type: str,
                        parameters: List[tuple] = None,
                        line_number: Optional[int] = None) -> Symbol:
        """
        Declara una función.
        
        Args:
            name: nombre de la función
            return_type: tipo de retorno
            parameters: lista de (nombre, tipo) de parámetros
            line_number: línea de declaración
            
        Returns:
            Symbol: símbolo de la función
        """
        parameters = parameters or []
        param_names = [param[0] for param in parameters]
        
        symbol = Symbol(
            name=name,
            symbol_type="function",
            kind=SymbolKind.FUNCTION,
            scope=Scope.GLOBAL,
            parameters=param_names,
            return_type=return_type,
            line_number=line_number
        )
        
        
        self.scopes[0][name] = symbol
        self.all_functions[name] = symbol
        
        return symbol
    
    def declare_temporary(self, temp_name: str) -> Symbol:
        """
        Declara una variable temporal.
        
        Args:
            temp_name: nombre de la temporal (ej: t0, t1)
            
        Returns:
            Symbol: símbolo de la temporal
        """
        symbol = Symbol(
            name=temp_name,
            symbol_type="integer",  
            kind=SymbolKind.TEMPORARY,
            scope=Scope.LOCAL if self.current_scope_level > 0 else Scope.GLOBAL
        )
        
        
        symbol.address = memory_manager.allocate_temp(temp_name)
        
        
        return symbol
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Busca un símbolo en los scopes (del más interno al más externo).
        
        Args:
            name: nombre del símbolo
            
        Returns:
            Symbol o None si no se encuentra
        """
        
        for scope_level in range(self.current_scope_level, -1, -1):
            if name in self.scopes[scope_level]:
                return self.scopes[scope_level][name]
        
        return None
    
    def lookup_function(self, name: str) -> Optional[Symbol]:
        """Busca una función específicamente"""
        return self.all_functions.get(name)
    
    def lookup_class(self, name: str) -> Optional[Symbol]:
        """Busca una clase específicamente"""
        return self.all_classes.get(name)
    
    def get_current_scope_symbols(self) -> Dict[str, Symbol]:
        """Retorna los símbolos del scope actual"""
        return self.scopes[self.current_scope_level].copy()
    
    def get_all_symbols(self) -> List[Symbol]:
        """Retorna todos los símbolos de todos los scopes"""
        all_symbols = []
        for scope in self.scopes:
            all_symbols.extend(scope.values())
        return all_symbols
    
    def enter_function(self, func_name: str, parameters: List[tuple] = None):
        """
        Entra al contexto de una función.
        
        Args:
            func_name: nombre de la función
            parameters: lista de (nombre, tipo) de parámetros
        """
        self.current_function = func_name
        parameters = parameters or []
        param_names = [param[0] for param in parameters]
        
        
        memory_manager.enter_function(func_name, param_names)
        
        
        self.enter_scope("function")
        
        
        for param_name, param_type in parameters:
            self.declare_parameter(param_name, param_type)
    
    def exit_function(self):
        """Sale del contexto de función actual"""
        if self.current_function:
            
            self.exit_scope()
            
            
            memory_manager.exit_function()
            
            self.current_function = None
    
    def enter_class(self, class_name: str):
        """Entra al contexto de una clase"""
        self.current_class = class_name
        self.enter_scope("class")
    
    def exit_class(self):
        """Sale del contexto de clase actual"""
        if self.current_class:
            self.exit_scope()
            self.current_class = None
    
    def mark_initialized(self, name: str) -> bool:
        """
        Marca una variable como inicializada.
        
        Args:
            name: nombre de la variable
            
        Returns:
            bool: True si se marcó exitosamente
        """
        symbol = self.lookup(name)
        if symbol:
            symbol.is_initialized = True
            return True
        return False
    
    def is_variable_initialized(self, name: str) -> bool:
        """Verifica si una variable está inicializada"""
        symbol = self.lookup(name)
        return symbol.is_initialized if symbol else False
    
    def get_variable_address(self, name: str) -> Optional[MemoryAddress]:
        """
        Obtiene la dirección de memoria de una variable.
        
        Args:
            name: nombre de la variable
            
        Returns:
            MemoryAddress o None si no se encuentra
        """
        symbol = self.lookup(name)
        return symbol.address if symbol else None
    
    def generate_temp_name(self) -> str:
        """Genera un nombre único para temporal"""
        name = f"t{self.temp_counter}"
        self.temp_counter += 1
        return name
    
    def generate_label_name(self) -> str:
        """Genera un nombre único para etiqueta"""
        name = f"L{self.label_counter}"
        self.label_counter += 1
        return name
    
    def clear(self):
        """Reinicia la tabla de símbolos"""
        self.scopes = [{}]
        self.current_scope_level = 0
        self.current_function = None
        self.current_class = None
        self.temp_counter = 0
        self.label_counter = 0
        self.global_symbols.clear()
        self.all_functions.clear()
        self.all_classes.clear()
    
    def get_statistics(self) -> dict:
        """Retorna estadísticas de la tabla de símbolos"""
        total_symbols = len(self.get_all_symbols())
        
        stats = {
            "total_symbols": total_symbols,
            "scope_depth": self.current_scope_level + 1,
            "global_variables": len(self.global_symbols),
            "functions": len(self.all_functions),
            "classes": len(self.all_classes),
            "current_function": self.current_function,
            "current_class": self.current_class,
            "temp_counter": self.temp_counter,
            "label_counter": self.label_counter
        }
        
        
        stats["scopes"] = []
        for i, scope in enumerate(self.scopes):
            scope_stats = {
                "level": i,
                "symbols_count": len(scope),
                "symbols": list(scope.keys())
            }
            stats["scopes"].append(scope_stats)
        
        return stats
    
    def to_dict(self) -> dict:
        """
        Convierte la tabla de símbolos a diccionario para serialización.
        
        Returns:
            dict: representación serializable de la tabla
        """
        return {
            "statistics": self.get_statistics(),
            "symbols": [symbol.to_dict() for symbol in self.get_all_symbols()],
            "memory_layout": memory_manager.get_memory_layout()
        }
    
    def print_symbols(self):
        """Imprime la tabla de símbolos de forma legible"""
        print("=== TABLA DE SÍMBOLOS ===")
        
        
        for i, scope in enumerate(self.scopes):
            scope_name = "GLOBAL" if i == 0 else f"SCOPE {i}"
            print(f"\n--- {scope_name} ---")
            
            if not scope:
                print("  (vacío)")
                continue
                
            for name, symbol in scope.items():
                addr_str = str(symbol.address) if symbol.address else "sin dirección"
                init_str = "✓" if symbol.is_initialized else "✗"
                
                print(f"  {name:15} | {symbol.symbol_type:10} | {symbol.kind.value:10} | {addr_str:8} | init:{init_str}")
        
        
        stats = self.get_statistics()
        print(f"\nTotal símbolos: {stats['total_symbols']}")
        print(f"Profundidad: {stats['scope_depth']}")
        print(f"Función actual: {stats['current_function'] or 'ninguna'}")
    
    def validate_usage(self, name: str, line_number: Optional[int] = None) -> tuple[bool, str]:
        """
        Valida el uso de una variable (debe estar declarada e inicializada).
        
        Args:
            name: nombre de la variable
            line_number: línea donde se usa
            
        Returns:
            tuple: (es_válido, mensaje_error)
        """
        symbol = self.lookup(name)
        
        if not symbol:
            return False, f"Variable '{name}' no declarada"
        
        if symbol.kind == SymbolKind.VARIABLE and not symbol.is_initialized:
            return False, f"Variable '{name}' usada antes de ser inicializada"
        
        return True, ""
    
    def get_function_info(self, func_name: str) -> Optional[dict]:
        """
        Obtiene información completa de una función.
        
        Args:
            func_name: nombre de la función
            
        Returns:
            dict con información de la función o None
        """
        symbol = self.lookup_function(func_name)
        if not symbol:
            return None
        
        return {
            "name": symbol.name,
            "return_type": symbol.return_type,
            "parameters": symbol.parameters,
            "parameter_count": len(symbol.parameters),
            "local_vars": list(symbol.local_vars),
            "address": str(symbol.address) if symbol.address else None
        }



symbol_table = SymbolTable()


class SymbolTableManager:
    """
    Manager de alto nivel que coordina la tabla de símbolos con el gestor de memoria.
    Proporciona una interfaz simplificada para operaciones comunes.
    """
    
    def __init__(self):
        self.symbol_table = symbol_table
        self.memory_manager = memory_manager
    
    def declare_variable(self, name: str, var_type: str, 
                        initial_value: Any = None,
                        is_constant: bool = False,
                        is_array: bool = False,
                        array_size: Optional[int] = None) -> tuple[Symbol, MemoryAddress]:
        """
        Declara una variable y asigna su dirección de memoria.
        
        Returns:
            tuple: (símbolo, dirección)
        """
        dimensions = [array_size] if is_array and array_size else None
        
        symbol = self.symbol_table.declare_variable(
            name, var_type, is_constant, is_array, dimensions
        )
        
        
        if initial_value is not None:
            symbol.is_initialized = True
        
        return symbol, symbol.address
    
    def enter_function_context(self, func_name: str, return_type: str,
                             parameters: List[tuple]) -> Symbol:
        """
        Entra al contexto completo de una función (símbolo + memoria).
        
        Args:
            func_name: nombre de la función
            return_type: tipo de retorno
            parameters: lista de (nombre, tipo)
            
        Returns:
            Symbol: símbolo de la función
        """
        
        func_symbol = self.symbol_table.declare_function(
            func_name, return_type, parameters
        )
        
        
        self.symbol_table.enter_function(func_name, parameters)
        
        return func_symbol
    
    def exit_function_context(self):
        """Sale del contexto completo de función"""
        self.symbol_table.exit_function()
    
    def lookup_with_address(self, name: str) -> tuple[Optional[Symbol], Optional[MemoryAddress]]:
        """
        Busca un símbolo y retorna tanto el símbolo como su dirección.
        
        Returns:
            tuple: (símbolo, dirección)
        """
        symbol = self.symbol_table.lookup(name)
        address = symbol.address if symbol else None
        return symbol, address
    
    def get_complete_info(self) -> dict:
        """Retorna información completa del estado actual"""
        return {
            "symbol_table": self.symbol_table.to_dict(),
            "memory_layout": self.memory_manager.get_memory_layout()
        }
    
    def clear_all(self):
        """Reinicia completamente el estado"""
        self.symbol_table.clear()
        self.memory_manager.clear()



symbol_manager = SymbolTableManager()
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from .memory_model import MemoryAddress, MemorySegment, memory_manager
from .enviroment import environment_manager


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
    name: str
    symbol_type: str
    kind: SymbolKind
    scope: Scope
    
    # Información de memoria extendida
    address: Optional[MemoryAddress] = None
    offset: int = 0
    size: int = 4
    level: int = 0  # nivel de anidamiento
    
    # Enlaces para registros de activación
    activation_record: Optional[str] = None  # nombre del AR propietario
    access_link: Optional[str] = None        # enlace estático para variables no locales
    display_index: Optional[int] = None      # índice en display para acceso rápido
    
    # Información de alcance
    scope_id: str = ""
    enclosing_scope: Optional[str] = None
    nested_scopes: Set[str] = field(default_factory=set)
    
    # Metadatos adicionales
    is_initialized: bool = False
    is_array: bool = False
    array_dimensions: List[int] = field(default_factory=list)
    is_reference: bool = False  # parámetros por referencia
    
    # Para funciones
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    local_vars: Set[str] = field(default_factory=set)
    frame_size: int = 0
    
    # Para clases
    fields: Dict[str, 'Symbol'] = field(default_factory=dict)
    methods: Dict[str, 'Symbol'] = field(default_factory=dict)
    parent_class: Optional[str] = None
    
    # Información de línea
    line_number: Optional[int] = None
    column: Optional[int] = None
    
    def __post_init__(self):
        """Validaciones post-inicialización"""
        if self.is_array and not self.array_dimensions:
            self.array_dimensions = [0]  # array de tamaño desconocido
    
    def get_total_size(self) -> int:
        """Calcula el tamaño total del símbolo"""
        if self.is_array:
            element_size = 4  # tamaño base por elemento
            total_elements = 1
            for dim in self.array_dimensions:
                total_elements *= max(dim, 1)
            return 8 + (total_elements * element_size)  # 8 bytes metadata + elementos
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
        return {
            "name": self.name,
            "type": self.symbol_type,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "address": self.address.to_dict() if self.address else None,
            "offset": self.offset,
            "size": self.size,
            "total_size": self.get_total_size(),
            "level": self.level,
            "scope_id": self.scope_id,
            "activation_record": self.activation_record,
            "access_link": self.access_link,
            "display_index": self.display_index,
            "is_initialized": self.is_initialized,
            "is_array": self.is_array,
            "is_reference": self.is_reference,
            "array_dimensions": self.array_dimensions,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "frame_size": self.frame_size,
            "line_number": self.line_number,
            "column": self.column
        }


class SymbolTable:
    def __init__(self):
        self.env_manager = environment_manager
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.temp_counter = 0
        self.label_counter = 0
        
        # Cache para búsquedas rápidas
        self.global_symbols: Dict[str, Symbol] = {}
        self.all_functions: Dict[str, Symbol] = {}
        self.all_classes: Dict[str, Symbol] = {}
    
    def enter_scope(self, scope_type: str = "block") -> str:
        return self.env_manager.enter_scope(scope_type)
    
    def exit_scope(self) -> Optional[str]:
        return self.env_manager.exit_scope()
    
    def declare_variable(self, name: str, var_type: str, 
                        is_constant: bool = False,
                        is_array: bool = False,
                        array_dimensions: List[int] = None,
                        line_number: Optional[int] = None) -> Symbol:
        
        scope = Scope.GLOBAL if self.env_manager.current_env_id == "global" else Scope.LOCAL
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
        
        # Asignar dirección de memoria
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
        
        # Configurar offset desde la dirección
        if symbol.address:
            symbol.offset = symbol.address.offset
        
        return self.env_manager.declare_symbol(symbol)
    
    def declare_parameter(self, name: str, param_type: str, 
                         is_reference: bool = False,
                         line_number: Optional[int] = None) -> Symbol:
        
        symbol = Symbol(
            name=name,
            symbol_type=param_type,
            kind=SymbolKind.PARAMETER,
            scope=Scope.PARAMETER,
            is_reference=is_reference,
            line_number=line_number
        )
        
        if memory_manager.current_activation:
            symbol.address = memory_manager.current_activation.get_param_address(name)
            if symbol.address:
                symbol.offset = symbol.address.offset
        
        return self.env_manager.declare_symbol(symbol)
    
    def declare_function(self, name: str, return_type: str,
                        parameters: List[tuple] = None,
                        line_number: Optional[int] = None) -> Symbol:
        
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
        
        # Crear ambiente para la función
        current_env = self.env_manager.get_current_env()
        symbol.activation_record = f"func_{name}"
        
        self.all_functions[name] = symbol
        return self.env_manager.declare_symbol(symbol)
    
    def declare_temporary(self, temp_name: str) -> Symbol:
        symbol = Symbol(
            name=temp_name,
            symbol_type="integer",
            kind=SymbolKind.TEMPORARY,
            scope=Scope.LOCAL if self.env_manager.current_env_id != "global" else Scope.GLOBAL
        )
        
        symbol.address = memory_manager.allocate_temp(temp_name)
        if symbol.address:
            symbol.offset = symbol.address.offset
        
        return symbol
    
    def lookup(self, name: str) -> Optional[Symbol]:
        return self.env_manager.lookup_symbol(name)
    
    def lookup_function(self, name: str) -> Optional[Symbol]:
        return self.all_functions.get(name)
    
    def lookup_class(self, name: str) -> Optional[Symbol]:
        return self.all_classes.get(name)
    
    def get_current_scope_symbols(self) -> Dict[str, Symbol]:
        current_env = self.env_manager.get_current_env()
        return current_env.symbols.copy()
    
    def get_all_symbols(self) -> List[Symbol]:
        all_symbols = []
        for env in self.env_manager.environments.values():
            all_symbols.extend(env.symbols.values())
        return all_symbols
    
    def enter_function(self, func_name: str, parameters: List[tuple] = None):
        self.current_function = func_name
        parameters = parameters or []
        param_names = [param[0] for param in parameters]
        
        memory_manager.enter_function(func_name, param_names)
        self.enter_scope("function")
        
        for param_name, param_type in parameters:
            self.declare_parameter(param_name, param_type)
    
    def exit_function(self):
        if self.current_function:
            self.exit_scope()
            memory_manager.exit_function()
            self.current_function = None
    
    def enter_class(self, class_name: str):
        self.current_class = class_name
        self.enter_scope("class")
    
    def exit_class(self):
        if self.current_class:
            self.exit_scope()
            self.current_class = None
    
    def mark_initialized(self, name: str) -> bool:
        symbol = self.lookup(name)
        if symbol:
            symbol.is_initialized = True
            return True
        return False
    
    def is_variable_initialized(self, name: str) -> bool:
        symbol = self.lookup(name)
        return symbol.is_initialized if symbol else False
    
    def get_variable_address(self, name: str) -> Optional[MemoryAddress]:
        symbol = self.lookup(name)
        return symbol.address if symbol else None
    
    def get_access_info(self, name: str) -> dict:
        symbol = self.lookup(name)
        if not symbol:
            return {}
        
        return {
            "name": symbol.name,
            "level": symbol.level,
            "offset": symbol.offset,
            "access_link": symbol.access_link,
            "display_index": symbol.display_index,
            "activation_record": symbol.activation_record,
            "address": str(symbol.address) if symbol.address else None
        }
    
    def generate_temp_name(self) -> str:
        name = f"t{self.temp_counter}"
        self.temp_counter += 1
        return name
    
    def generate_label_name(self) -> str:
        name = f"L{self.label_counter}"
        self.label_counter += 1
        return name
    
    def clear(self):
        self.env_manager.clear()
        self.current_function = None
        self.current_class = None
        self.temp_counter = 0
        self.label_counter = 0
        self.global_symbols.clear()
        self.all_functions.clear()
        self.all_classes.clear()
    
    def get_statistics(self) -> dict:
        total_symbols = len(self.get_all_symbols())
        current_env = self.env_manager.get_current_env()
        
        return {
            "total_symbols": total_symbols,
            "current_environment": current_env.id,
            "environment_level": current_env.level,
            "global_variables": len(self.global_symbols),
            "functions": len(self.all_functions),
            "classes": len(self.all_classes),
            "current_function": self.current_function,
            "current_class": self.current_class,
            "environment_tree": self.env_manager.get_env_tree()
        }
    
    def to_dict(self) -> dict:
        return {
            "statistics": self.get_statistics(),
            "symbols": [symbol.to_dict() for symbol in self.get_all_symbols()],
            "memory_layout": memory_manager.get_memory_layout(),
            "environments": self.env_manager.get_env_tree()
        }
    
    def print_symbols(self):
        print("=== TABLA DE SÍMBOLOS EXTENDIDA ===")
        
        for env_id, env in self.env_manager.environments.items():
            print(f"\n--- AMBIENTE: {env_id} (nivel {env.level}) ---")
            
            if not env.symbols:
                print("  (vacío)")
                continue
                
            for name, symbol in env.symbols.items():
                addr_str = str(symbol.address) if symbol.address else "sin dirección"
                init_str = "✓" if symbol.is_initialized else "✗"
                access_info = f"offset:{symbol.offset}"
                if symbol.access_link:
                    access_info += f", link:{symbol.access_link}"
                
                print(f"  {name:15} | {symbol.symbol_type:10} | {symbol.kind.value:10} | {addr_str:8} | {access_info} | init:{init_str}")
    
    def validate_usage(self, name: str, line_number: Optional[int] = None) -> tuple[bool, str]:
        symbol = self.lookup(name)
        
        if not symbol:
            return False, f"Variable '{name}' no declarada"
        
        if symbol.kind == SymbolKind.VARIABLE and not symbol.is_initialized:
            return False, f"Variable '{name}' usada antes de ser inicializada"
        
        return True, ""
        # scope más interno hacia afuera
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
        
        # Crear frame de activación en el gestor de memoria
        memory_manager.enter_function(func_name, param_names)
        
        # Entrar al scope de la función
        self.enter_scope("function")
        
        # Declarar parámetros en el nuevo scope
        for param_name, param_type in parameters:
            self.declare_parameter(param_name, param_type)
    
    def exit_function(self):
        """Sale del contexto de función actual"""
        if self.current_function:
            # Salir del scope de función
            self.exit_scope()
            
            # Salir del frame de activación
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
        
        # Estadísticas por scope
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
        
        # Imprimir por scopes
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
        
        # Imprimir estadísticas
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
        symbol = self.lookup_function(func_name)
        if not symbol:
            return None
        
        return {
            "name": symbol.name,
            "return_type": symbol.return_type,
            "parameters": symbol.parameters,
            "parameter_count": len(symbol.parameters),
            "local_vars": list(symbol.local_vars),
            "frame_size": symbol.frame_size,
            "activation_record": symbol.activation_record,
            "address": str(symbol.address) if symbol.address else None
        }


symbol_table = SymbolTable()


class SymbolTableManager:
    def __init__(self):
        self.symbol_table = symbol_table
        self.memory_manager = memory_manager
    
    def declare_variable(self, name: str, var_type: str, 
                        initial_value: Any = None,
                        is_constant: bool = False,
                        is_array: bool = False,
                        array_size: Optional[int] = None) -> tuple[Symbol, MemoryAddress]:
        
        dimensions = [array_size] if is_array and array_size else None
        
        symbol = self.symbol_table.declare_variable(
            name, var_type, is_constant, is_array, dimensions
        )
        
        if initial_value is not None:
            symbol.is_initialized = True
        
        return symbol, symbol.address
    
    def enter_function_context(self, func_name: str, return_type: str,
                             parameters: List[tuple]) -> Symbol:
        
        func_symbol = self.symbol_table.declare_function(
            func_name, return_type, parameters
        )
        
        self.symbol_table.enter_function(func_name, parameters)
        
        return func_symbol
    
    def exit_function_context(self):
        self.symbol_table.exit_function()
    
    def lookup_with_address(self, name: str) -> tuple[Optional[Symbol], Optional[MemoryAddress]]:
        symbol = self.symbol_table.lookup(name)
        address = symbol.address if symbol else None
        return symbol, address
    
    def get_access_chain(self, name: str) -> List[dict]:
        symbol = self.symbol_table.lookup(name)
        if not symbol:
            return []
        
        access_chain = []
        current_env_id = self.symbol_table.env_manager.current_env_id
        target_env_id = symbol.scope_id
        
        # Construir cadena de acceso desde ambiente actual hasta ambiente del símbolo
        while current_env_id and current_env_id != target_env_id:
            env = self.symbol_table.env_manager.environments[current_env_id]
            access_chain.append({
                "env_id": current_env_id,
                "level": env.level,
                "parent": env.parent_id
            })
            current_env_id = env.parent_id
        
        return access_chain
    
    def get_complete_info(self) -> dict:
        return {
            "symbol_table": self.symbol_table.to_dict(),
            "memory_layout": self.memory_manager.get_memory_layout()
        }
    
    def clear_all(self):
        self.symbol_table.clear()
        self.memory_manager.clear()


symbol_manager = SymbolTableManager()
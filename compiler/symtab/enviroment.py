from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from .symbols import Symbol, SymbolKind
from .memory_model import MemoryAddress, MemorySegment


@dataclass
class Environment:
    id: str
    parent_id: Optional[str] = None
    level: int = 0
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    children: Set[str] = field(default_factory=set)
    is_function: bool = False
    is_class: bool = False
    frame_pointer: Optional[int] = None
    
    def add_symbol(self, symbol: Symbol):
        symbol.scope_id = self.id
        symbol.level = self.level
        self.symbols[symbol.name] = symbol
    
    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)


class DisplayTable:
    def __init__(self):
        self.display: List[Optional[str]] = []  # env_id por nivel
        self.max_level = -1
    
    def set_level(self, level: int, env_id: str):
        while len(self.display) <= level:
            self.display.append(None)
        self.display[level] = env_id
        self.max_level = max(self.max_level, level)
    
    def get_env_at_level(self, level: int) -> Optional[str]:
        if 0 <= level < len(self.display):
            return self.display[level]
        return None


class EnvironmentManager:
    def __init__(self):
        self.environments: Dict[str, Environment] = {}
        self.current_env_id: Optional[str] = None
        self.env_counter = 0
        self.display = DisplayTable()
        
        # Crear ambiente global
        self.create_global_env()
    
    def create_global_env(self):
        global_env = Environment("global", None, 0)
        self.environments["global"] = global_env
        self.current_env_id = "global"
        self.display.set_level(0, "global")
    
    def enter_scope(self, scope_type: str = "block") -> str:
        parent_env = self.environments[self.current_env_id]
        env_id = f"{scope_type}_{self.env_counter}"
        self.env_counter += 1
        
        new_env = Environment(
            id=env_id,
            parent_id=self.current_env_id,
            level=parent_env.level + 1,
            is_function=(scope_type == "function"),
            is_class=(scope_type == "class")
        )
        
        self.environments[env_id] = new_env
        parent_env.children.add(env_id)
        
        self.current_env_id = env_id
        self.display.set_level(new_env.level, env_id)
        
        return env_id
    
    def exit_scope(self) -> Optional[str]:
        if self.current_env_id == "global":
            return None
        
        current_env = self.environments[self.current_env_id]
        parent_id = current_env.parent_id
        self.current_env_id = parent_id
        
        if parent_id:
            parent_env = self.environments[parent_id]
            self.display.set_level(parent_env.level, parent_id)
        
        return current_env.id
    
    def declare_symbol(self, symbol: Symbol) -> Symbol:
        current_env = self.environments[self.current_env_id]
        
        if symbol.name in current_env.symbols:
            raise RuntimeError(f"Symbol '{symbol.name}' already declared in current scope")
        
        # Configurar información de ambiente
        symbol.scope_id = current_env.id
        symbol.level = current_env.level
        symbol.activation_record = current_env.id if current_env.is_function else None
        
        # Configurar offset basado en el tipo de símbolo
        if symbol.kind == SymbolKind.PARAMETER:
            symbol.offset = self._calculate_param_offset(current_env, symbol)
        elif symbol.kind in [SymbolKind.VARIABLE, SymbolKind.TEMPORARY]:
            symbol.offset = self._calculate_local_offset(current_env, symbol)
        
        # Configurar enlaces para acceso no local
        self._setup_access_links(symbol, current_env)
        
        current_env.add_symbol(symbol)
        return symbol
    
    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        env_id = self.current_env_id
        
        while env_id:
            env = self.environments[env_id]
            symbol = env.lookup_local(name)
            
            if symbol:
                # Configurar acceso si es variable no local
                if env_id != self.current_env_id:
                    self._setup_nonlocal_access(symbol, env_id)
                return symbol
            
            env_id = env.parent_id
        
        return None
    
    def _calculate_param_offset(self, env: Environment, symbol: Symbol) -> int:
        param_count = sum(1 for s in env.symbols.values() 
                         if s.kind == SymbolKind.PARAMETER)
        return 8 + (param_count * 4)  # después de BP y return addr
    
    def _calculate_local_offset(self, env: Environment, symbol: Symbol) -> int:
        local_size = sum(s.size for s in env.symbols.values() 
                        if s.kind in [SymbolKind.VARIABLE, SymbolKind.TEMPORARY])
        return -(local_size + symbol.size)  # negativo desde BP
    
    def _setup_access_links(self, symbol: Symbol, env: Environment):
        if env.level > 0:
            parent_env = self.environments[env.parent_id]
            symbol.access_link = parent_env.id
            symbol.display_index = env.level
    
    def _setup_nonlocal_access(self, symbol: Symbol, defining_env_id: str):
        current_env = self.environments[self.current_env_id]
        defining_env = self.environments[defining_env_id]
        
        # Calcular cadena de acceso estático
        level_diff = current_env.level - defining_env.level
        symbol.access_link = defining_env_id if level_diff > 0 else None
    
    def get_current_env(self) -> Environment:
        return self.environments[self.current_env_id]
    
    def get_env_tree(self) -> dict:
        def build_tree(env_id: str) -> dict:
            env = self.environments[env_id]
            return {
                "id": env_id,
                "level": env.level,
                "symbols": list(env.symbols.keys()),
                "children": [build_tree(child_id) for child_id in env.children]
            }
        
        return build_tree("global")
    
    def clear(self):
        self.environments.clear()
        self.env_counter = 0
        self.display = DisplayTable()
        self.create_global_env()


environment_manager = EnvironmentManager()
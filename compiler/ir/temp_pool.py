from typing import Set, List, Optional
from collections import deque

class TemporaryPool:
    def __init__(self):
        self.next_temp_id = 0
        self.available_temps = deque()
        self.in_use_temps = set()
        self.scope_stack = []
        self.global_max_temps = 0
    
    def allocate(self) -> str:
        # Siempre usar el siguiente ID secuencial, no reutilizar
        temp_name = f"t{self.next_temp_id}"
        self.next_temp_id += 1
        self.in_use_temps.add(temp_name)
        
        if self.get_in_use_count() > self.global_max_temps:
            self.global_max_temps = self.get_in_use_count()
        
        return temp_name
    
    def free(self, temp_name: str) -> bool:
        if temp_name in self.in_use_temps:
            self.in_use_temps.remove(temp_name)
            # No agregamos a available_temps para evitar reutilización
            return True
        return False
    
    def free_multiple(self, temp_names: List[str]) -> int:
        freed_count = 0
        for temp_name in temp_names:
            if self.free(temp_name):
                freed_count += 1
        return freed_count
    
    def is_temporary(self, name: str) -> bool:
        return name.startswith("t") and name[1:].isdigit()
    
    def is_in_use(self, temp_name: str) -> bool:
        return temp_name in self.in_use_temps
    
    def get_in_use_count(self) -> int:
        return len(self.in_use_temps)
    
    def get_available_count(self) -> int:
        return len(self.available_temps)
    
    def get_total_allocated(self) -> int:
        return self.next_temp_id
    
    def get_max_simultaneous(self) -> int:
        return self.global_max_temps
    
    def push_scope(self):
        self.scope_stack.append(set(self.in_use_temps))
    
    def pop_scope(self) -> int:
        if not self.scope_stack:
            return 0
        
        previous_temps = self.scope_stack.pop()
        current_temps = self.in_use_temps.copy()
        
        new_temps = current_temps - previous_temps
        freed_count = self.free_multiple(list(new_temps))
        
        return freed_count
    
    def clear(self):
        self.next_temp_id = 0
        self.available_temps.clear()
        self.in_use_temps.clear()
        self.scope_stack.clear()
        self.global_max_temps = 0
    
    def get_stats(self) -> dict:
        return {
            "total_allocated": self.get_total_allocated(),
            "in_use": self.get_in_use_count(),
            "available": self.get_available_count(),
            "max_simultaneous": self.get_max_simultaneous(),
            "scope_depth": len(self.scope_stack),
            "in_use_temps": sorted(list(self.in_use_temps)),
            "available_temps": list(self.available_temps)
        }
    
    def __str__(self) -> str:
        stats = self.get_stats()
        return (f"TemporaryPool(allocated={stats['total_allocated']}, "
                f"in_use={stats['in_use']}, available={stats['available']}, "
                f"max_simultaneous={stats['max_simultaneous']})")

class ScopedTemporaryManager:
    def __init__(self):
        self.pool = TemporaryPool()
        self.expression_temps = []
    
    def new_temp(self) -> str:
        temp = self.pool.allocate()
        self.expression_temps.append(temp)
        return temp
    
    def finish_expression(self, result_temp: Optional[str] = None) -> str:
        if not self.expression_temps:
            return ""
        
        if result_temp is None:
            result_temp = self.expression_temps[-1]
        
        for temp in self.expression_temps:
            if temp != result_temp:
                self.pool.free(temp)
        
        self.expression_temps.clear()
        return result_temp
    
    def with_scope(self):
        return TemporaryScopeContext(self.pool)
    
    def clear(self):
        self.pool.clear()
        self.expression_temps.clear()
    
    def get_stats(self) -> dict:
        return self.pool.get_stats()


class TemporaryScopeContext:
    def __init__(self, pool: TemporaryPool):
        self.pool = pool
    
    def __enter__(self):
        self.pool.push_scope()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.pop_scope()


default_temp_manager = ScopedTemporaryManager()

def new_temp() -> str:
    return default_temp_manager.new_temp()

def finish_expression(result_temp: Optional[str] = None) -> str:
    return default_temp_manager.finish_expression(result_temp)

def temp_scope():
    return default_temp_manager.with_scope()
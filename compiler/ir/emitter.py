from typing import List, Dict, Optional, Union, Set
from .triplet import Triplet, TripletTable, OpCode, Operand
from .triplet import temp_operand, var_operand, const_operand, label_operand, func_operand
from .temp_pool import ScopedTemporaryManager


class LabelGenerator:
    
    def __init__(self):
        self.next_label_id = 0
        self.label_types = {
            'general': 'L',
            'loop_start': 'LOOP_START_',
            'loop_end': 'LOOP_END_',
            'loop_continue': 'LOOP_CONT_',
            'if_true': 'IF_TRUE_',
            'if_false': 'IF_FALSE_',
            'if_end': 'IF_END_',
            'switch_case': 'CASE_',
            'switch_default': 'DEFAULT_',
            'switch_end': 'SWITCH_END_',
            'func_start': 'FUNC_',
            'func_end': 'FUNC_END_'
        }
    
    def new_label(self, label_type: str = 'general') -> str:
        prefix = self.label_types.get(label_type, 'L')
        label_name = f"{prefix}{self.next_label_id}"
        self.next_label_id += 1
        return label_name
    
    def reset(self):
        self.next_label_id = 0


class BackpatchList:
    
    def __init__(self):
        self.patches: List[int] = []
    
    def add(self, triplet_index: int):
        self.patches.append(triplet_index)
    
    def merge(self, other: 'BackpatchList') -> 'BackpatchList':
        result = BackpatchList()
        result.patches = self.patches + other.patches
        return result
    
    def get_patches(self) -> List[int]:
        return self.patches.copy()
    
    def clear(self):
        self.patches.clear()


class TripletEmitter:
    
    def __init__(self):
        self.table = TripletTable()
        self.label_gen = LabelGenerator()
        self.temp_manager = ScopedTemporaryManager()
        self.pending_patches: Dict[str, List[int]] = {}
        
        self.break_stack: List[BackpatchList] = []
        self.continue_stack: List[BackpatchList] = []
        
        self.current_function: Optional[str] = None
        self.function_params: Dict[str, List[str]] = {}
    
    def emit(self, op: OpCode, 
            arg1: Optional[Union[str, int, float, bool, Operand]] = None,
            arg2: Optional[Union[str, int, float, bool, Operand]] = None,
            result: Optional[Union[str, Operand]] = None,
            comment: Optional[str] = None) -> int:
        if arg1 is not None and not isinstance(arg1, Operand):
            if isinstance(arg1, (int, float, bool)):
                arg1 = const_operand(arg1)
            else:
                arg1 = var_operand(str(arg1))
        
        if arg2 is not None and not isinstance(arg2, Operand):
            if isinstance(arg2, (int, float, bool)):
                arg2 = const_operand(arg2)
            else:
                arg2 = var_operand(str(arg2))
        
        if result is not None and not isinstance(result, Operand):
            result = var_operand(str(result))
        
        triplet = Triplet(op, arg1, arg2, result, None)
        return self.table.add(triplet)
    
    def emit_label(self, label_name: str) -> int:
        return self.emit(OpCode.LABEL, label_operand(label_name))
    
    def emit_jump(self, label_name: str) -> int:
        return self.emit(OpCode.JMP, None, None, label_operand(label_name))
    
    def emit_conditional_jump(self, op: OpCode, arg1: Union[str, Operand], 
                            arg2: Optional[Union[str, Operand]] = None,
                            label_name: Optional[str] = None) -> int:
        result_arg = label_operand(label_name) if label_name else None
        return self.emit(op, arg1, arg2, result_arg)
    
    def emit_binary_op(self, op: OpCode, left: Union[str, Operand], 
                      right: Union[str, Operand], 
                      result: Optional[str] = None) -> str:
        if result is None:
            result = self.temp_manager.new_temp()
        
        self.emit(op, left, right, temp_operand(result))
        return result
    
    def emit_unary_op(self, op: OpCode, operand: Union[str, Operand],
                     result: Optional[str] = None) -> str:
        if result is None:
            result = self.temp_manager.new_temp()
        
        self.emit(op, operand, None, temp_operand(result))
        return result
    
    def emit_assignment(self, target: str, source: Union[str, Operand]) -> int:
        return self.emit(OpCode.MOV, source, None, var_operand(target))
    
    def new_label(self, label_type: str = 'general') -> str:
        return self.label_gen.new_label(label_type)
    
    def new_temp(self) -> str:
        return self.temp_manager.new_temp()
    
    def backpatch(self, patch_list: BackpatchList, label_name: str):
        for triplet_index in patch_list.get_patches():
            if 0 <= triplet_index < len(self.table.triplets):
                triplet = self.table.triplets[triplet_index]
                if triplet.is_jump() and triplet.result is None:
                    triplet.result = label_operand(label_name)
    
    def make_list(self, triplet_index: int) -> BackpatchList:
        bp_list = BackpatchList()
        bp_list.add(triplet_index)
        return bp_list
    
    def merge_lists(self, list1: BackpatchList, list2: BackpatchList) -> BackpatchList:
        return list1.merge(list2)
    
    
    def enter_loop(self) -> tuple[str, str]:
        continue_label = self.new_label('loop_continue')
        break_label = self.new_label('loop_end')
        
        self.break_stack.append(BackpatchList())
        self.continue_stack.append(BackpatchList())
        
        return continue_label, break_label
    
    def exit_loop(self, continue_label: str, break_label: str):
        if self.break_stack and self.continue_stack:
            break_list = self.break_stack.pop()
            continue_list = self.continue_stack.pop()
            
            self.backpatch(break_list, break_label)
            self.backpatch(continue_list, continue_label)
    
    def emit_break(self) -> int:
        jump_index = self.emit_jump("")
        if self.break_stack:
            self.break_stack[-1].add(jump_index)
        return jump_index
    
    def emit_continue(self) -> int:
        jump_index = self.emit_jump("")
        if self.continue_stack:
            self.continue_stack[-1].add(jump_index)
        return jump_index
    
    
    def enter_function(self, func_name: str, params: List[str]):
        self.current_function = func_name
        self.function_params[func_name] = params
        
        func_label = self.new_label('func_start')
        self.emit_label(func_label)
        self.emit(OpCode.ENTER, func_operand(func_name), const_operand(len(params)))
    
    def exit_function(self):
        if self.current_function:
            self.emit(OpCode.EXIT, func_operand(self.current_function))
            self.current_function = None
    
    def emit_return(self, value: Optional[Union[str, Operand]] = None) -> int:
        return self.emit(OpCode.RETURN, value)
    
    def emit_call(self, func_name: str, args: List[Union[str, Operand]], 
                  result: Optional[str] = None) -> str:
        for arg in args:
            self.emit(OpCode.PARAM, arg)
        
        if result is None:
            result = self.new_temp()
        
        self.emit(OpCode.CALL, func_operand(func_name), const_operand(len(args)), 
                 temp_operand(result))
        return result
    
    
    def emit_array_access(self, array: Union[str, Operand], 
                         index: Union[str, Operand],
                         result: Optional[str] = None) -> str:
        if result is None:
            result = self.new_temp()
        
        self.emit(OpCode.ARRAY_GET, array, index, temp_operand(result))
        return result
    
    def emit_array_assignment(self, array: Union[str, Operand],
                            index: Union[str, Operand],
                            value: Union[str, Operand]) -> int:
        return self.emit(OpCode.ARRAY_SET, array, index, value)
    
    def emit_field_access(self, obj: Union[str, Operand], 
                         field: str,
                         result: Optional[str] = None) -> str:
        if result is None:
            result = self.new_temp()
        
        self.emit(OpCode.GET_FIELD, obj, var_operand(field), temp_operand(result))
        return result
    
    def emit_field_assignment(self, obj: Union[str, Operand],
                            field: str,
                            value: Union[str, Operand]) -> int:
        return self.emit(OpCode.SET_FIELD, obj, var_operand(field), value)
    
    
    def get_current_index(self) -> int:
        return len(self.table.triplets)
    
    def finish_expression(self, result_temp: Optional[str] = None) -> str:
        return self.temp_manager.finish_expression(result_temp)
    
    def clear(self):
        self.table.clear()
        self.label_gen.reset()
        self.temp_manager.clear()
        self.temp_manager.pool.next_temp_id = 0  
        self.pending_patches.clear()
        self.break_stack.clear()
        self.continue_stack.clear()
        self.current_function = None
        self.function_params.clear()
    
    def get_triplets(self) -> List[dict]:
        return self.table.to_list()
    
    def get_stats(self) -> dict:
        return {
            "triplets_count": len(self.table.triplets),
            "labels_generated": self.label_gen.next_label_id,
            "temp_stats": self.temp_manager.get_stats(),
            "current_function": self.current_function,
            "functions_defined": list(self.function_params.keys())
        }
    
    def __str__(self) -> str:
        return str(self.table)
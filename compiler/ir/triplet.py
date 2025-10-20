from typing import Optional, Union, List
from enum import Enum


class OpCode(Enum):
    ADD = "add"          
    SUB = "sub"          
    MUL = "mul"          
    DIV = "div"          
    MOD = "mod"          
    NEG = "neg"          
    
    
    AND = "and"          
    OR = "or"            
    NOT = "not"          
    
    
    EQ = "eq"            
    NE = "ne"            
    LT = "lt"            
    LE = "le"            
    GT = "gt"            
    GE = "ge"            
    
    
    MOV = "mov"          
    LOAD = "load"        
    STORE = "store"      
    
    
    JMP = "jmp"          
    BEQ = "beq"          
    BNE = "bne"          
    BLT = "blt"          
    BLE = "ble"          
    BGT = "bgt"          
    BGE = "bge"          
    BZ = "bz"            
    BNZ = "bnz"          
    
    
    CALL = "call"        
    RETURN = "return"    
    PARAM = "param"      
    ENTER = "BeginFunc"      
    EXIT = "EndFunc"        
    
    
    ARRAY_GET = "array_get"  
    ARRAY_SET = "array_set"  
    ARRAY_ALLOC = "array_alloc"  
    
    
    GET_FIELD = "get_field"    
    SET_FIELD = "set_field"    
    NEW_OBJ = "new_obj"        
    
    
    LABEL = "label"      
    NOP = "nop"          
    PRINT = "print"      
    CAST = "cast"        


class Operand:
    def __init__(self, value: Union[str, int, float, bool, None], 
                 operand_type: str = "temp"):
        self.value = value
        self.type = operand_type  
    
    def __str__(self) -> str:
        if self.value is None:
            return "-"
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"Operand({self.value}, {self.type})"
    
    def is_temporary(self) -> bool:
        return self.type == "temp" and isinstance(self.value, str) and self.value.startswith("t")
    
    def is_constant(self) -> bool:
        return self.type == "const"
    
    def is_variable(self) -> bool:
        return self.type == "var"
    
    def is_label(self) -> bool:
        return self.type == "label"


class Triplet:
    def __init__(self, 
                 op: OpCode,
                 arg1: Optional[Operand] = None,
                 arg2: Optional[Operand] = None,
                 result: Optional[Operand] = None,
                 comment: Optional[str] = None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result
        self.comment = comment
        self.id = None  
    
    def __str__(self) -> str:
        if self.op == OpCode.LABEL:
            return f"{self.arg1}:"

        parts = []

        if self.op == OpCode.ENTER:
            return f"BeginFunc {self.arg1};"
        
        if self.op == OpCode.EXIT:
            return "EndFunc;"

        if self.result:
            parts.append(f"{self.result} = ")

        parts.append(self.op.value)

        args = []
        if self.arg1:
            args.append(str(self.arg1))
        if self.arg2:
            args.append(str(self.arg2))

        if args:
            parts.append(f" {', '.join(args)}")

        return "".join(parts)
    
    def __repr__(self) -> str:
        return f"Triplet({self.op}, {self.arg1}, {self.arg2}, {self.result})"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "op": self.op.value,
            "arg1": str(self.arg1) if self.arg1 else None,
            "arg2": str(self.arg2) if self.arg2 else None,
            "result": str(self.result) if self.result else None,
            "comment": self.comment
        }
    
    def is_jump(self) -> bool:
        return self.op in [OpCode.JMP, OpCode.BEQ, OpCode.BNE, OpCode.BLT, 
                          OpCode.BLE, OpCode.BGT, OpCode.BGE, OpCode.BZ, OpCode.BNZ]
    
    def is_label(self) -> bool:
        return self.op == OpCode.LABEL
    
    def is_arithmetic(self) -> bool:
        return self.op in [OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, 
                          OpCode.MOD, OpCode.NEG]
    
    def is_logical(self) -> bool:
        return self.op in [OpCode.AND, OpCode.OR, OpCode.NOT]
    
    def is_comparison(self) -> bool:
        return self.op in [OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, 
                          OpCode.GT, OpCode.GE]
    
    def uses_operand(self, operand: Operand) -> bool:
        return (self.arg1 and str(self.arg1) == str(operand)) or \
               (self.arg2 and str(self.arg2) == str(operand))
    
    def defines_operand(self, operand: Operand) -> bool:
        return self.result and str(self.result) == str(operand)


class TripletTable:
    def __init__(self):
        self.triplets: List[Triplet] = []
        self.next_id = 0
    
    def add(self, triplet: Triplet) -> int:
        triplet.id = self.next_id
        self.triplets.append(triplet)
        self.next_id += 1
        return triplet.id
    
    def get(self, index: int) -> Optional[Triplet]:
        if 0 <= index < len(self.triplets):
            return self.triplets[index]
        return None
    
    def size(self) -> int:
        return len(self.triplets)
    
    def clear(self):
        self.triplets.clear()
        self.next_id = 0
    
    def to_list(self) -> List[dict]:
        return [triplet.to_dict() for triplet in self.triplets]
    
    def __str__(self) -> str:
        if self.op == OpCode.LABEL:
            return f"{self.arg1}:"

        parts = []

        if self.result:
            parts.append(f"{self.result} = ")

        parts.append(self.op.value)

        args = []
        if self.arg1:
            args.append(str(self.arg1))
        if self.arg2:
            args.append(str(self.arg2))

        if args:
            parts.append(f" {', '.join(args)}")

        result = "".join(parts)

        return result
    
    def __len__(self) -> int:
        return len(self.triplets)
    
    def __iter__(self):
        return iter(self.triplets)
    
    def __getitem__(self, index):
        return self.triplets[index]


def temp_operand(name: str) -> Operand:
    """Crea un operando temporal"""
    return Operand(name, "temp")

def var_operand(name: str) -> Operand:
    """Crea un operando variable"""
    return Operand(name, "var")

def const_operand(value: Union[int, float, str, bool]) -> Operand:
    """Crea un operando constante"""
    return Operand(value, "const")

def label_operand(name: str) -> Operand:
    """Crea un operando etiqueta"""
    return Operand(name, "label")

def func_operand(name: str) -> Operand:
    """Crea un operando función"""
    return Operand(name, "func")
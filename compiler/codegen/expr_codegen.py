from typing import Optional
from compiler.ir.triplet import Triplet, OpCode, Operand, TripletTable
from compiler.ir.emitter import TripletEmitter


class ExprCodeGen:
    def __init__(self, emitter: TripletEmitter):
        self.emitter = emitter
    
    def gen_binary_expr(self, op: str, left: Operand, right: Operand) -> Operand:
        op_map = {
            '+': OpCode.ADD,
            '-': OpCode.SUB,
            '*': OpCode.MUL,
            '/': OpCode.DIV,
            '%': OpCode.MOD,
            '==': OpCode.EQ,
            '!=': OpCode.NE,
            '<': OpCode.LT,
            '<=': OpCode.LE,
            '>': OpCode.GT,
            '>=': OpCode.GE,
            '&&': OpCode.AND,
            '||': OpCode.OR
        }
        
        opcode = op_map.get(op)
        if not opcode:
            raise ValueError(f"Operador binario desconocido: {op}")
        
        result_temp = self.emitter.emit_binary_op(opcode, left, right)
        return Operand(result_temp, "temp")
    
    def gen_unary_expr(self, op: str, operand: Operand) -> Operand:
        op_map = {
            '-': OpCode.NEG,
            '!': OpCode.NOT
        }
        
        opcode = op_map.get(op)
        if not opcode:
            raise ValueError(f"Operador unario desconocido: {op}")
        
        result_temp = self.emitter.emit_unary_op(opcode, operand)
        return Operand(result_temp, "temp")
    
    def gen_literal(self, value) -> Operand:
        return Operand(value, "const")
    
    def gen_variable(self, name: str) -> Operand:
        return Operand(name, "var")
    
    def gen_assignment(self, target: str, value: Operand) -> None:
        self.emitter.emit_assignment(target, value)
from antlr4 import *
from typing import Optional, Any, Dict, List
import sys
import os

# Solo importamos los módulos del compilador
current_dir = os.path.dirname(__file__)
compiler_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, compiler_dir)

from compiler.ir.emitter import TripletEmitter, BackpatchList
from compiler.ir.triplet import OpCode


class SimpleSymbol:
    def __init__(self, name: str, sym_type: str, address: int):
        self.name = name
        self.sym_type = sym_type
        self.address = address
    
    def __repr__(self):
        return f"Symbol({self.name}, {self.sym_type}, addr={self.address})"


class SimpleSymbolTable:
    def __init__(self):
        self.scopes = [{}]
        self.current_level = 0
    
    def enter_scope(self):
        self.scopes.append({})
        self.current_level += 1
    
    def exit_scope(self):
        if self.current_level > 0:
            self.scopes.pop()
            self.current_level -= 1
    
    def insert(self, name: str, symbol: SimpleSymbol):
        self.scopes[self.current_level][name] = symbol
    
    def lookup(self, name: str) -> Optional[SimpleSymbol]:
        for i in range(self.current_level, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        return None
    
    def get_all_symbols(self) -> Dict[str, SimpleSymbol]:
        all_syms = {}
        for scope in self.scopes:
            all_syms.update(scope)
        return all_syms


class SimpleMemoryModel:
    def __init__(self):
        self.global_offset = 0
        self.local_offset = 0
    
    def allocate_global(self, size: int) -> int:
        addr = self.global_offset
        self.global_offset += size
        return addr
    
    def allocate_local(self, size: int) -> int:
        addr = self.local_offset
        self.local_offset += size
        return addr


class ExprResult:
    def __init__(self, temp: str, true_list: Optional[BackpatchList] = None, 
                 false_list: Optional[BackpatchList] = None):
        self.temp = temp
        self.true_list = true_list if true_list else BackpatchList()
        self.false_list = false_list if false_list else BackpatchList()


class CompiscriptTACVisitor:
    """
    Visitor para generar código intermedio TAC.
    Recibe las clases Parser y Visitor como parámetros en el constructor.
    """
    
    def __init__(self, parser_class, visitor_class):
        # Guardamos las clases para poder acceder a sus contextos
        self.ParserClass = parser_class
        self.VisitorClass = visitor_class
        
        # Inicializamos las estructuras de datos
        self.emitter = TripletEmitter()
        self.symbol_table = SimpleSymbolTable()
        self.memory_model = SimpleMemoryModel()
        self.current_scope = "global"
    
    def visit(self, ctx):
        """Método genérico de visita que delega al método específico"""
        if ctx is None:
            return None
        
        # Obtenemos el nombre de la clase del contexto
        class_name = ctx.__class__.__name__
        
        # Construimos el nombre del método visitor
        visitor_method_name = f'visit{class_name[:-7]}'  # Removemos 'Context'
        
        # Buscamos el método correspondiente
        visitor = getattr(self, visitor_method_name, None)
        if visitor:
            return visitor(ctx)
        else:
            # Si no hay método específico, visitamos los hijos
            return self.visitChildren(ctx)
    
    def visitChildren(self, ctx):
        """Visita todos los hijos de un nodo"""
        if ctx is None:
            return None
        
        # Check if this is a terminal node (no children)
        if not hasattr(ctx, 'children') or ctx.children is None:
            return None
        
        result = None
        for child in ctx.children:
            if hasattr(child, 'accept'):
                child_result = self.visit(child)
                if child_result is not None:
                    result = child_result
        return result
        
    def get_triplets(self):
        return self.emitter.table.triplets
    
    def get_symbols(self):
        return self.symbol_table.get_all_symbols()
    
    def visitProgram(self, ctx):
        for stmt in ctx.statement():
            self.visit(stmt)
        return None
    
    def visitStatement(self, ctx):
        return self.visitChildren(ctx)
    
    def visitBlock(self, ctx):
        self.symbol_table.enter_scope()
        for stmt in ctx.statement():
            self.visit(stmt)
        self.symbol_table.exit_scope()
        return None
    
    def visitVariableDeclaration(self, ctx):
        var_name = ctx.Identifier().getText()
        var_type = "integer"
        if ctx.typeAnnotation():
            type_ctx = ctx.typeAnnotation().type_()
            if type_ctx:
                var_type = type_ctx.getText()
        
        if self.current_scope == "global":
            address = self.memory_model.allocate_global(4)
        else:
            address = self.memory_model.allocate_local(4)
        
        symbol = SimpleSymbol(var_name, var_type, address)
        self.symbol_table.insert(var_name, symbol)
        
        if ctx.initializer():
            expr_result = self.visit(ctx.initializer().expression())
            if isinstance(expr_result, ExprResult):
                self.emitter.emit_assignment(var_name, expr_result.temp)
            elif expr_result is not None:
                self.emitter.emit_assignment(var_name, expr_result)
        
        return None
    
    def visitConstantDeclaration(self, ctx):
        var_name = ctx.Identifier().getText()
        var_type = "integer"
        if ctx.typeAnnotation():
            type_ctx = ctx.typeAnnotation().type_()
            if type_ctx:
                var_type = type_ctx.getText()
        
        address = self.memory_model.allocate_global(4)
        symbol = SimpleSymbol(var_name, var_type, address)
        self.symbol_table.insert(var_name, symbol)
        
        expr_result = self.visit(ctx.expression())
        if isinstance(expr_result, ExprResult):
            self.emitter.emit_assignment(var_name, expr_result.temp)
        elif expr_result is not None:
            self.emitter.emit_assignment(var_name, expr_result)
        
        return None
    
    def visitAssignment(self, ctx):
        if ctx.Identifier() and len(ctx.expression()) == 1:
            var_name = ctx.Identifier().getText()
            expr_result = self.visit(ctx.expression(0))
            if isinstance(expr_result, ExprResult):
                self.emitter.emit_assignment(var_name, expr_result.temp)
            elif expr_result is not None:
                self.emitter.emit_assignment(var_name, expr_result)
        elif len(ctx.expression()) == 2:
            obj_expr = self.visit(ctx.expression(0))
            value_expr = self.visit(ctx.expression(1))
            obj_temp = obj_expr.temp if isinstance(obj_expr, ExprResult) else obj_expr
            value_temp = value_expr.temp if isinstance(value_expr, ExprResult) else value_expr
            prop_name = ctx.Identifier().getText()
            self.emitter.emit(OpCode.SET_FIELD, obj_temp, prop_name, value_temp)
        
        return None
    
    def visitExpressionStatement(self, ctx):
        self.visit(ctx.expression())
        return None
    
    def visitPrintStatement(self, ctx):
        expr_result = self.visit(ctx.expression())
        if isinstance(expr_result, ExprResult):
            self.emitter.emit(OpCode.PRINT, expr_result.temp)
        elif expr_result is not None:
            self.emitter.emit(OpCode.PRINT, expr_result)
        return None
    
    def visitIfStatement(self, ctx):
        cond_result = self.visit(ctx.expression())
        
        if not isinstance(cond_result, ExprResult):
            temp = cond_result if cond_result else self.emitter.new_temp()
            cond_result = ExprResult(temp)
            true_jump = self.emitter.emit_conditional_jump(temp, "")
            false_jump = self.emitter.emit_jump("")
            cond_result.true_list.add(true_jump)
            cond_result.false_list.add(false_jump)
        
        true_label = self.emitter.new_label('if_true')
        self.emitter.backpatch(cond_result.true_list, true_label)
        self.emitter.emit_label(true_label)
        
        self.visit(ctx.block(0))
        
        if ctx.block(1):
            then_jump_list = self.emitter.make_list(self.emitter.emit_jump(""))
            
            false_label = self.emitter.new_label('if_false')
            self.emitter.backpatch(cond_result.false_list, false_label)
            self.emitter.emit_label(false_label)
            
            self.visit(ctx.block(1))
            
            end_label = self.emitter.new_label('if_end')
            self.emitter.backpatch(then_jump_list, end_label)
            self.emitter.emit_label(end_label)
        else:
            end_label = self.emitter.new_label('if_end')
            self.emitter.backpatch(cond_result.false_list, end_label)
            self.emitter.emit_label(end_label)
        
        return None
    
    def visitWhileStatement(self, ctx):
        begin_label = self.emitter.new_label('loop_start')
        self.emitter.emit_label(begin_label)
        
        continue_label, break_label = self.emitter.enter_loop()
        
        cond_result = self.visit(ctx.expression())
        
        if not isinstance(cond_result, ExprResult):
            temp = cond_result if cond_result else self.emitter.new_temp()
            cond_result = ExprResult(temp)
            true_jump = self.emitter.emit_conditional_jump(temp, "")
            false_jump = self.emitter.emit_jump("")
            cond_result.true_list.add(true_jump)
            cond_result.false_list.add(false_jump)
        
        body_label = self.emitter.new_label('loop_body')
        self.emitter.backpatch(cond_result.true_list, body_label)
        self.emitter.emit_label(body_label)
        
        self.visit(ctx.block())
        
        self.emitter.emit_label(continue_label)
        self.emitter.emit_jump(begin_label)
        
        self.emitter.emit_label(break_label)
        self.emitter.backpatch(cond_result.false_list, break_label)
        
        self.emitter.exit_loop(continue_label, break_label)
        
        return None
    
    def visitDoWhileStatement(self, ctx):
        begin_label = self.emitter.new_label('loop_start')
        self.emitter.emit_label(begin_label)
        
        continue_label, break_label = self.emitter.enter_loop()
        
        self.visit(ctx.block())
        
        self.emitter.emit_label(continue_label)
        
        cond_result = self.visit(ctx.expression())
        
        if isinstance(cond_result, ExprResult):
            self.emitter.backpatch(cond_result.true_list, begin_label)
            self.emitter.backpatch(cond_result.false_list, break_label)
        else:
            temp = cond_result if cond_result else self.emitter.new_temp()
            self.emitter.emit_conditional_jump(temp, begin_label)
        
        self.emitter.emit_label(break_label)
        
        self.emitter.exit_loop(continue_label, break_label)
        
        return None
    
    def visitForStatement(self, ctx):
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())
        
        begin_label = self.emitter.new_label('loop_start')
        self.emitter.emit_label(begin_label)
        
        continue_label, break_label = self.emitter.enter_loop()
        
        if ctx.expression(0):
            cond_result = self.visit(ctx.expression(0))
            
            if not isinstance(cond_result, ExprResult):
                temp = cond_result if cond_result else self.emitter.new_temp()
                cond_result = ExprResult(temp)
                true_jump = self.emitter.emit_conditional_jump(temp, "")
                false_jump = self.emitter.emit_jump("")
                cond_result.true_list.add(true_jump)
                cond_result.false_list.add(false_jump)
            
            body_label = self.emitter.new_label('loop_body')
            self.emitter.backpatch(cond_result.true_list, body_label)
            self.emitter.emit_label(body_label)
        
        self.visit(ctx.block())
        
        self.emitter.emit_label(continue_label)
        
        if ctx.expression(1):
            self.visit(ctx.expression(1))
        
        self.emitter.emit_jump(begin_label)
        
        self.emitter.emit_label(break_label)
        if ctx.expression(0):
            self.emitter.backpatch(cond_result.false_list, break_label)
        
        self.emitter.exit_loop(continue_label, break_label)
        
        return None
    
    def visitBreakStatement(self, ctx):
        self.emitter.emit_break()
        return None
    
    def visitContinueStatement(self, ctx):
        self.emitter.emit_continue()
        return None
    
    def visitExpression(self, ctx):
        # expression: assignmentExpr
        if ctx.assignmentExpr():
            return self.visit(ctx.assignmentExpr())
        return None
    
    def visitAssignmentExpr(self, ctx):
        return self.visitChildren(ctx)
    
    def visitAssignExpr(self, ctx):
        return self.visitChildren(ctx)
    
    def visitPropertyAssignExpr(self, ctx):
        return self.visitChildren(ctx)
    
    def visitExprNoAssign(self, ctx):
        if ctx.conditionalExpr():
            return self.visit(ctx.conditionalExpr())
        return None
    
    def visitConditionalExpr(self, ctx):
        return self.visitChildren(ctx)
    
    def visitTernaryExpr(self, ctx):
        if ctx.logicalOrExpr():
            return self.visit(ctx.logicalOrExpr())
        return None
    
    def visitAdditiveExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.multiplicativeExpr(0))
        
        left_result = self.visit(ctx.multiplicativeExpr(0))
        left_temp = left_result.temp if isinstance(left_result, ExprResult) else left_result
        
        for i in range(1, len(ctx.multiplicativeExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.multiplicativeExpr(i))
            right_temp = right_result.temp if isinstance(right_result, ExprResult) else right_result
            
            if op_text == '+':
                left_temp = self.emitter.emit_binary_op(OpCode.ADD, left_temp, right_temp)
            elif op_text == '-':
                left_temp = self.emitter.emit_binary_op(OpCode.SUB, left_temp, right_temp)
        
        return ExprResult(left_temp)
    
    def visitMultiplicativeExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.unaryExpr(0))
        
        left_result = self.visit(ctx.unaryExpr(0))
        left_temp = left_result.temp if isinstance(left_result, ExprResult) else left_result
        
        for i in range(1, len(ctx.unaryExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.unaryExpr(i))
            right_temp = right_result.temp if isinstance(right_result, ExprResult) else right_result
            
            if op_text == '*':
                left_temp = self.emitter.emit_binary_op(OpCode.MUL, left_temp, right_temp)
            elif op_text == '/':
                left_temp = self.emitter.emit_binary_op(OpCode.DIV, left_temp, right_temp)
            elif op_text == '%':
                left_temp = self.emitter.emit_binary_op(OpCode.MOD, left_temp, right_temp)
        
        return ExprResult(left_temp)
    
    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.getChild(0))
        
        op_text = ctx.getChild(0).getText()
        operand_result = self.visit(ctx.unaryExpr())
        operand_temp = operand_result.temp if isinstance(operand_result, ExprResult) else operand_result
        
        if op_text == '-':
            result_temp = self.emitter.emit_unary_op(OpCode.NEG, operand_temp)
        elif op_text == '!':
            result_temp = self.emitter.emit_unary_op(OpCode.NOT, operand_temp)
        else:
            result_temp = operand_temp
        
        return ExprResult(result_temp)
    
    def visitRelationalExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.additiveExpr(0))
        
        left_result = self.visit(ctx.additiveExpr(0))
        left_temp = left_result.temp if isinstance(left_result, ExprResult) else left_result
        
        for i in range(1, len(ctx.additiveExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.additiveExpr(i))
            right_temp = right_result.temp if isinstance(right_result, ExprResult) else right_result
            
            result = ExprResult(self.emitter.new_temp())
            
            if op_text == '<':
                true_jump = self.emitter.emit(OpCode.BLT, left_temp, right_temp, "")
            elif op_text == '<=':
                true_jump = self.emitter.emit(OpCode.BLE, left_temp, right_temp, "")
            elif op_text == '>':
                true_jump = self.emitter.emit(OpCode.BGT, left_temp, right_temp, "")
            elif op_text == '>=':
                true_jump = self.emitter.emit(OpCode.BGE, left_temp, right_temp, "")
            else:
                continue
            
            false_jump = self.emitter.emit_jump("")
            
            result.true_list.add(true_jump)
            result.false_list.add(false_jump)
            
            left_temp = result.temp
        
        return result if len(ctx.additiveExpr()) > 1 else left_result
    
    def visitEqualityExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.relationalExpr(0))
        
        left_result = self.visit(ctx.relationalExpr(0))
        left_temp = left_result.temp if isinstance(left_result, ExprResult) else left_result
        
        for i in range(1, len(ctx.relationalExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.relationalExpr(i))
            right_temp = right_result.temp if isinstance(right_result, ExprResult) else right_result
            
            result = ExprResult(self.emitter.new_temp())
            
            if op_text == '==':
                true_jump = self.emitter.emit(OpCode.BEQ, left_temp, right_temp, "")
            elif op_text == '!=':
                true_jump = self.emitter.emit(OpCode.BNE, left_temp, right_temp, "")
            else:
                continue
            
            false_jump = self.emitter.emit_jump("")
            
            result.true_list.add(true_jump)
            result.false_list.add(false_jump)
            
            left_temp = result.temp
        
        return result if len(ctx.relationalExpr()) > 1 else left_result
    
    def visitLogicalAndExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.equalityExpr(0))
        
        left_result = self.visit(ctx.equalityExpr(0))
        
        if not isinstance(left_result, ExprResult):
            temp = left_result if left_result else self.emitter.new_temp()
            left_result = ExprResult(temp)
            true_jump = self.emitter.emit_conditional_jump(temp, "")
            false_jump = self.emitter.emit_jump("")
            left_result.true_list.add(true_jump)
            left_result.false_list.add(false_jump)
        
        for i in range(1, len(ctx.equalityExpr())):
            m_label = self.emitter.new_label('and_next')
            self.emitter.backpatch(left_result.true_list, m_label)
            self.emitter.emit_label(m_label)
            
            right_result = self.visit(ctx.equalityExpr(i))
            
            if not isinstance(right_result, ExprResult):
                temp = right_result if right_result else self.emitter.new_temp()
                right_result = ExprResult(temp)
                true_jump = self.emitter.emit_conditional_jump(temp, "")
                false_jump = self.emitter.emit_jump("")
                right_result.true_list.add(true_jump)
                right_result.false_list.add(false_jump)
            
            left_result.true_list = right_result.true_list
            left_result.false_list = self.emitter.merge_lists(left_result.false_list, right_result.false_list)
        
        return left_result
    
    def visitLogicalOrExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.logicalAndExpr(0))
        
        left_result = self.visit(ctx.logicalAndExpr(0))
        
        if not isinstance(left_result, ExprResult):
            temp = left_result if left_result else self.emitter.new_temp()
            left_result = ExprResult(temp)
            true_jump = self.emitter.emit_conditional_jump(temp, "")
            false_jump = self.emitter.emit_jump("")
            left_result.true_list.add(true_jump)
            left_result.false_list.add(false_jump)
        
        for i in range(1, len(ctx.logicalAndExpr())):
            m_label = self.emitter.new_label('or_next')
            self.emitter.backpatch(left_result.false_list, m_label)
            self.emitter.emit_label(m_label)
            
            right_result = self.visit(ctx.logicalAndExpr(i))
            
            if not isinstance(right_result, ExprResult):
                temp = right_result if right_result else self.emitter.new_temp()
                right_result = ExprResult(temp)
                true_jump = self.emitter.emit_conditional_jump(temp, "")
                false_jump = self.emitter.emit_jump("")
                right_result.true_list.add(true_jump)
                right_result.false_list.add(false_jump)
            
            left_result.true_list = self.emitter.merge_lists(left_result.true_list, right_result.true_list)
            left_result.false_list = right_result.false_list
        
        return left_result
    
    def visitPrimaryAtom(self, ctx):
        if ctx.Integer():
            value = ctx.Integer().getText()
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, value, None, temp)
            return ExprResult(temp)
        elif ctx.String():
            value = ctx.String().getText()
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, value, None, temp)
            return ExprResult(temp)
        elif ctx.Identifier():
            var_name = ctx.Identifier().getText()
            return ExprResult(var_name)
        elif ctx.expression():
            return self.visit(ctx.expression())
        elif ctx.getText() == 'true':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, "true", None, temp)
            return ExprResult(temp)
        elif ctx.getText() == 'false':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, "false", None, temp)
            return ExprResult(temp)
        elif ctx.getText() == 'null':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, "null", None, temp)
            return ExprResult(temp)
        
        return ExprResult(self.emitter.new_temp())
from antlr4 import *
from typing import Optional, Any, Dict, List
import sys
import os

# Solo importamos los módulos del compilador
current_dir = os.path.dirname(__file__)
compiler_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, compiler_dir)

from compiler.ir.emitter import TripletEmitter, BackpatchList
from compiler.ir.triplet import OpCode, Operand, var_operand, const_operand, temp_operand
from compiler.codegen.func_codegen import FuncCodeGen
from compiler.codegen.array_codegen import ArrayCodeGen
from compiler.symtab.memory_model import MemoryManager


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

        # Generadores de código especializados
        self.func_codegen = FuncCodeGen(self.emitter)
        self.memory_manager = MemoryManager()
        self.array_codegen = ArrayCodeGen(self.emitter, self.memory_manager)
    
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

    def visitFunctionDeclaration(self, ctx):
        """
        Visitor para declaración de función
        Genera prolog, procesa el cuerpo y genera epilog
        """
        # Obtener nombre de función
        func_name = ctx.Identifier().getText()

        # Obtener parámetros
        params = []
        if ctx.parameters():
            param_list = ctx.parameters()
            if hasattr(param_list, 'Identifier'):
                # Obtener todos los identificadores de parámetros
                for identifier in param_list.Identifier():
                    params.append(identifier.getText())

        # Obtener tipo de retorno
        return_type = "void"
        if ctx.typeAnnotation():
            type_ctx = ctx.typeAnnotation().type_()
            if type_ctx:
                return_type = type_ctx.getText()

        # Guardar scope anterior y entrar a scope de función
        prev_scope = self.current_scope
        self.current_scope = func_name

        # Generar prólogo de función
        self.func_codegen.gen_function_prolog(func_name, params, return_type)

        # Entrar nuevo scope para variables locales
        self.symbol_table.enter_scope()

        # Registrar parámetros en tabla de símbolos
        for param in params:
            address = self.memory_model.allocate_local(4)
            symbol = SimpleSymbol(param, "parameter", address)
            self.symbol_table.insert(param, symbol)

        # Procesar cuerpo de la función
        if ctx.block():
            self.visit(ctx.block())

        # Salir del scope
        self.symbol_table.exit_scope()

        # Generar epílogo de función
        self.func_codegen.gen_function_epilog(func_name)

        # Restaurar scope anterior
        self.current_scope = prev_scope

        return None

    def visitReturnStatement(self, ctx):
        """
        Visitor para statement de return
        Genera código RETURN con valor opcional
        """
        if ctx.expression():
            # Return con valor
            expr_result = self.visit(ctx.expression())
            if isinstance(expr_result, ExprResult):
                self.func_codegen.gen_return(var_operand(expr_result.temp))
            elif expr_result is not None:
                self.func_codegen.gen_return(var_operand(str(expr_result)))
            else:
                self.func_codegen.gen_return()
        else:
            # Return void
            self.func_codegen.gen_return()

        return None

    def visitCallExpr(self, ctx):
        """
        Visitor para llamada a función (expresión)
        Genera código PARAM para argumentos y CALL
        """
        # Obtener nombre de función desde postfixExpr
        func_name = None
        if ctx.postfixExpr():
            postfix_ctx = ctx.postfixExpr()
            if hasattr(postfix_ctx, 'primaryAtom') and postfix_ctx.primaryAtom():
                primary = postfix_ctx.primaryAtom()
                if hasattr(primary, 'Identifier') and primary.Identifier():
                    func_name = primary.Identifier().getText()

        if not func_name:
            # Si no podemos obtener el nombre, retornar temporal vacío
            return ExprResult(self.emitter.new_temp())

        # Procesar argumentos
        args = []
        if ctx.arguments():
            arg_ctx = ctx.arguments()
            if hasattr(arg_ctx, 'expression'):
                # Puede ser una lista o un método
                expressions = arg_ctx.expression() if callable(arg_ctx.expression) else [arg_ctx.expression]
                for expr in expressions:
                    expr_result = self.visit(expr)
                    if isinstance(expr_result, ExprResult):
                        args.append(var_operand(expr_result.temp))
                    elif expr_result is not None:
                        args.append(var_operand(str(expr_result)))

        # Generar llamada a función
        result_temp = self.func_codegen.gen_function_call(func_name, args)

        return ExprResult(result_temp)

    def visitPostfixExpr(self, ctx):
        """
        Visitor para expresiones postfix
        Maneja llamadas a función y acceso a propiedades
        """
        # Si es una llamada (tiene paréntesis con argumentos)
        if ctx.arguments():
            return self.visitCallExpr(ctx)

        # Si no, visitar el átomo primario
        if ctx.primaryAtom():
            return self.visit(ctx.primaryAtom())

        # Visitar hijos por defecto
        return self.visitChildren(ctx)

    def visitIndexExpr(self, ctx):
        """
        Visitor para acceso por índice a arreglo: array[index]

        Genera código para:
        1. Evaluar el array (base)
        2. Evaluar el índice
        3. Calcular dirección efectiva
        4. Acceder al elemento

        Si está en lado izquierdo de asignación, solo retorna info para ARRAY_SET.
        Si está en expresión, genera ARRAY_GET.
        """
        # Obtener la expresión base (el arreglo)
        base_expr = self.visit(ctx.postfixExpr())

        # Obtener el nombre del arreglo
        array_name = None
        if isinstance(base_expr, ExprResult):
            array_name = base_expr.temp
        elif isinstance(base_expr, str):
            array_name = base_expr

        if not array_name:
            # Si no podemos determinar el arreglo, retornar temporal vacío
            return ExprResult(self.emitter.new_temp())

        # Evaluar el índice
        index_expr = self.visit(ctx.expression())
        index_temp = index_expr.temp if isinstance(index_expr, ExprResult) else str(index_expr)

        # Generar acceso al arreglo con direcciones efectivas
        # Verificar si el arreglo está registrado en array_codegen
        array_info = self.array_codegen.get_array_info(array_name)

        if array_info:
            # Si está registrado, usar el generador de código de arreglos
            result_temp = self.array_codegen.gen_array_access(
                array_name,
                index_temp,
                check_bounds=True
            )
        else:
            # Si no está registrado (puede ser un arreglo de parámetro o dinámico)
            # Usar las instrucciones básicas del emitter
            result_temp = self.emitter.new_temp()

            # Calcular dirección efectiva manualmente
            # Asumir tamaño de elemento = 4 (enteros)
            t_offset = self.emitter.new_temp()
            self.emitter.emit(
                OpCode.MUL,
                var_operand(index_temp),
                const_operand(4),  # element_size por defecto
                temp_operand(t_offset),
                comment=f"Offset for {array_name}[index]"
            )

            # Acceso básico
            self.emitter.emit(
                OpCode.ARRAY_GET,
                var_operand(array_name),
                temp_operand(t_offset),
                temp_operand(result_temp),
                comment=f"Load {array_name}[index]"
            )

        return ExprResult(result_temp)

    def visitArrayLiteral(self, ctx):
        """
        Visitor para literal de arreglo: [1, 2, 3, 4]

        Genera código para:
        1. Asignar memoria para el arreglo
        2. Inicializar cada elemento
        """
        # Obtener todas las expresiones del literal
        expressions = ctx.expression() if hasattr(ctx, 'expression') else []

        if not expressions:
            # Arreglo vacío
            array_size = 0
        elif callable(expressions):
            expressions = expressions()
            array_size = len(expressions) if isinstance(expressions, list) else 1
        else:
            array_size = len(expressions) if isinstance(expressions, list) else 1

        # Generar un nombre temporal para el arreglo literal
        array_temp = self.emitter.new_temp()

        # Asignar el arreglo (tipo integer por defecto)
        is_global = (self.current_scope == "global")

        if array_size > 0:
            array_info = self.array_codegen.gen_array_allocation(
                array_temp,
                "integer",
                array_size,
                is_global=is_global
            )

            # Inicializar cada elemento
            expr_list = expressions if isinstance(expressions, list) else [expressions]
            for i, expr_ctx in enumerate(expr_list):
                # Evaluar la expresión
                expr_result = self.visit(expr_ctx)
                expr_temp = expr_result.temp if isinstance(expr_result, ExprResult) else str(expr_result)

                # Asignar al índice i
                self.array_codegen.gen_array_assignment(
                    array_temp,
                    const_operand(i),
                    var_operand(expr_temp),
                    check_bounds=False  # No necesitamos bounds check en literales
                )
        else:
            # Arreglo vacío - solo asignar con tamaño 0
            self.emitter.emit(
                OpCode.ARRAY_ALLOC,
                const_operand(0),
                const_operand(4),
                temp_operand(array_temp),
                comment="Empty array literal"
            )

        return ExprResult(array_temp)

    def visitVariableDeclaration(self, ctx):
        """
        Visitor sobrescrito para manejar declaraciones de arreglos.

        Ejemplos:
        - var x: integer;
        - var arr: integer[10];
        """
        var_name = ctx.Identifier().getText()
        var_type = "integer"
        is_array = False
        array_size = 0

        # Obtener tipo y verificar si es arreglo
        if ctx.typeAnnotation():
            type_ctx = ctx.typeAnnotation().type_()
            if type_ctx:
                # Obtener el tipo base
                if hasattr(type_ctx, 'baseType') and type_ctx.baseType():
                    var_type = type_ctx.baseType().getText()
                else:
                    var_type = type_ctx.getText()

                # Verificar si tiene corchetes (es un arreglo)
                type_text = type_ctx.getText()
                if '[' in type_text and ']' in type_text:
                    is_array = True
                    # Intentar extraer el tamaño del arreglo
                    # Por ahora, asumiremos tamaño dinámico o de inicializador

        # Determinar si es global o local
        is_global = (self.current_scope == "global")

        # Si hay inicializador, procesarlo
        if ctx.initializer():
            expr_result = self.visit(ctx.initializer().expression())

            # Verificar si el inicializador es un array literal
            if isinstance(expr_result, ExprResult):
                init_temp = expr_result.temp

                # Si es un arreglo, copiar la información
                if is_array or self.array_codegen.get_array_info(init_temp):
                    # El inicializador es un arreglo
                    # Simplemente asignar la referencia
                    symbol = SimpleSymbol(var_name, "array", 0)
                    self.symbol_table.insert(var_name, symbol)

                    self.emitter.emit(
                        OpCode.MOV,
                        temp_operand(init_temp),
                        None,
                        var_operand(var_name),
                        comment=f"Assign array {init_temp} to {var_name}"
                    )
                else:
                    # Inicializador normal (no array)
                    if is_global:
                        address = self.memory_model.allocate_global(4)
                    else:
                        address = self.memory_model.allocate_local(4)

                    symbol = SimpleSymbol(var_name, var_type, address)
                    self.symbol_table.insert(var_name, symbol)
                    self.emitter.emit_assignment(var_name, init_temp)
        else:
            # Sin inicializador
            if is_array:
                # Declaración de arreglo sin inicializador
                # Necesitamos un tamaño (usar 0 por defecto o error)
                array_size = 10  # Tamaño por defecto

                self.array_codegen.gen_array_allocation(
                    var_name,
                    var_type,
                    array_size,
                    is_global=is_global
                )

                symbol = SimpleSymbol(var_name, "array", 0)
                self.symbol_table.insert(var_name, symbol)
            else:
                # Variable normal
                if is_global:
                    address = self.memory_model.allocate_global(4)
                else:
                    address = self.memory_model.allocate_local(4)

                symbol = SimpleSymbol(var_name, var_type, address)
                self.symbol_table.insert(var_name, symbol)

        return None
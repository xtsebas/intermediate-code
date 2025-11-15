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
        self.temp = None  # Agregar campo para temporal asociado
        self.array_dimensions = []  # Dimensiones de arreglo si aplica
        self.is_initialized = False  # Flag de inicialización

    def get_display_type(self) -> str:
        """Retorna el tipo con formato de arreglo si aplica"""
        if self.array_dimensions:
            dims = "".join([f"[]" for _ in self.array_dimensions])
            return f"{self.sym_type}{dims}"
        return self.sym_type

    def __repr__(self):
        display_type = self.get_display_type()
        return f"Symbol({self.name}, {display_type}, addr={self.address})"


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
        self.segment_map = {}  # Mapeo de nombres de variables a direcciones

    def allocate_global(self, size: int, var_name: str = None) -> int:
        addr = self.global_offset
        self.global_offset += size
        if var_name:
            self.segment_map[var_name] = f"G[{addr}]"
        return addr

    def allocate_local(self, size: int, var_name: str = None) -> int:
        addr = self.local_offset
        self.local_offset += size
        if var_name:
            self.segment_map[var_name] = f"L[{addr}]"
        return addr

    def get_address_str(self, var_name: str) -> str:
        """Retorna la dirección en formato string"""
        return self.segment_map.get(var_name, f"G[{var_name}]")


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
        
        # Agregar diccionario para mapeo de parámetros a temporales
        self.param_temps = {}

        # Generadores de código especializados
        self.func_codegen = FuncCodeGen(self.emitter)
        self.memory_manager = MemoryManager()
        self.array_codegen = ArrayCodeGen(self.emitter, self.memory_manager)
    
    def _get_default_value(self, var_type: str) -> str:
        """
        Retorna el valor por defecto para un tipo dado.
        Usado para inicializar variables sin inicializador explícito.
        """
        # Extraer el tipo base (sin corchetes de array)
        base_type = var_type.split('[')[0].strip()

        default_values = {
            'integer': '0',
            'string': '""',
            'boolean': 'undefined',
            'void': 'null',
            'number': '0',
            'any': 'null'
        }

        return default_values.get(base_type, 'undefined')

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

    def print_symbol_table(self):
        """Imprime la tabla de símbolos de forma legible"""
        all_symbols = self.get_symbols()

        if not all_symbols:
            print("Tabla de símbolos vacía")
            return

        print("\n=== TABLA DE SÍMBOLOS ===")
        print(f"{'Nombre':15} | {'Tipo':20} | {'Dirección':12} | {'Inicializado':12}")
        print("-" * 70)

        for name, symbol in all_symbols.items():
            display_type = symbol.get_display_type()
            init_str = "Sí" if symbol.is_initialized else "No"
            # Usar la dirección del segmento de memoria si está disponible
            addr_str = self.memory_model.get_address_str(name)
            print(f"{name:15} | {display_type:20} | {addr_str:12} | {init_str:12}")

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

        if ctx.expression():
            expr_result = self.visit(ctx.expression())
            if isinstance(expr_result, ExprResult):
                self.emitter.emit(OpCode.MOV, expr_result.temp, None, var_name)
            elif expr_result is not None:
                temp = self.emitter.new_temp()
                self.emitter.emit(OpCode.MOV, str(expr_result), None, temp)
                self.emitter.emit(OpCode.MOV, temp, None, var_name)

        return None
    
    def visitAssignment(self, ctx):
        if ctx.Identifier() and len(ctx.expression()) == 1:
            var_name = ctx.Identifier().getText()
            expr_result = self.visit(ctx.expression(0))
            
            if isinstance(expr_result, ExprResult):
                self.emitter.emit(OpCode.MOV, expr_result.temp, None, var_name)
            elif expr_result is not None:
                temp = self.emitter.new_temp()
                self.emitter.emit(OpCode.MOV, str(expr_result), None, temp)
                self.emitter.emit(OpCode.MOV, temp, None, var_name)
        elif len(ctx.expression()) == 2:
            obj_expr = self.visit(ctx.expression(0))
            value_expr = self.visit(ctx.expression(1))
            obj_temp = obj_expr.temp if isinstance(obj_expr, ExprResult) else obj_expr
            value_temp = value_expr.temp if isinstance(value_expr, ExprResult) else value_expr
            prop_name = ctx.Identifier().getText()
            self.emitter.emit(OpCode.SET_FIELD, obj_temp, prop_name, value_temp)
        
        return None
    
    def visitExpression(self, ctx):
        if ctx.assignmentExpr():
            result = self.visit(ctx.assignmentExpr())
            if result is None:
                temp = self.emitter.new_temp()
                return ExprResult(temp)
            return result
        temp = self.emitter.new_temp()
        return ExprResult(temp)
    
    def visitPrintStatement(self, ctx):
        expr_result = self.visit(ctx.expression())
        if isinstance(expr_result, ExprResult):
            self.emitter.emit(OpCode.PRINT, temp_operand(expr_result.temp))
        elif expr_result is not None:
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, var_operand(str(expr_result)), None, temp_operand(temp))
            self.emitter.emit(OpCode.PRINT, temp_operand(temp))
        return None
    
    def visitIfStatement(self, ctx):
        cond_result = self.visit(ctx.expression())
        
        if not isinstance(cond_result, ExprResult):
            temp = cond_result if cond_result else self.emitter.new_temp()
            cond_result = ExprResult(temp)
            # Salto condicional a rellenar: BNZ temp, <label_true>
            true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
            # Salto condicional a rellenar: BNZ temp, <label_true>
            true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
            # BNZ temp, begin_label
            self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, begin_label)
        
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
                # Salto condicional a rellenar: BNZ temp, <label_true>
                true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
        result = self.visitChildren(ctx)
        if result is None:
            temp = self.emitter.new_temp()
            return ExprResult(temp)
        return result

    def visitAssignExpr(self, ctx):
        result = self.visitChildren(ctx)
        if result is None:
            temp = self.emitter.new_temp()
            return ExprResult(temp)
        return result

    def visitPropertyAssignExpr(self, ctx):
        result = self.visitChildren(ctx)
        if result is None:
            temp = self.emitter.new_temp()
            return ExprResult(temp)
        return result

    def visitExprNoAssign(self, ctx):
        if ctx.conditionalExpr():
            result = self.visit(ctx.conditionalExpr())
            if result is None:
                temp = self.emitter.new_temp()
                return ExprResult(temp)
            return result
        temp = self.emitter.new_temp()
        return ExprResult(temp)

    def visitConditionalExpr(self, ctx):
        result = self.visitChildren(ctx)
        if result is None:
            temp = self.emitter.new_temp()
            return ExprResult(temp)
        return result

    def visitTernaryExpr(self, ctx):
        if ctx.logicalOrExpr():
            result = self.visit(ctx.logicalOrExpr())
            if result is None:
                temp = self.emitter.new_temp()
                return ExprResult(temp)
            return result
        temp = self.emitter.new_temp()
        return ExprResult(temp)
    
    def visitAdditiveExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.multiplicativeExpr(0))
        
        left_result = self.visit(ctx.multiplicativeExpr(0))
        
        # Asegurar que left_result es ExprResult
        if not isinstance(left_result, ExprResult):
            left_temp = self.emitter.new_temp()
            if left_result is None:
                self.emitter.emit(OpCode.MOV, const_operand(0), None, temp_operand(left_temp))
            elif isinstance(left_result, (int, float, str, bool)):
                self.emitter.emit(OpCode.MOV, const_operand(left_result), None, temp_operand(left_temp))
            else:
                self.emitter.emit(OpCode.MOV, var_operand(str(left_result)), None, temp_operand(left_temp))
            left_result = ExprResult(left_temp)
        
        left_temp = left_result.temp
        
        for i in range(1, len(ctx.multiplicativeExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.multiplicativeExpr(i))
            
            # Asegurar que right_result es ExprResult
            if not isinstance(right_result, ExprResult):
                right_temp = self.emitter.new_temp()
                if right_result is None:
                    self.emitter.emit(OpCode.MOV, const_operand(0), None, temp_operand(right_temp))
                elif isinstance(right_result, (int, float, str, bool)):
                    self.emitter.emit(OpCode.MOV, const_operand(right_result), None, temp_operand(right_temp))
                else:
                    self.emitter.emit(OpCode.MOV, var_operand(str(right_result)), None, temp_operand(right_temp))
                right_result = ExprResult(right_temp)
            
            right_temp = right_result.temp
            result_temp = self.emitter.new_temp()
            
            if op_text == '+':
                self.emitter.emit(OpCode.ADD, temp_operand(left_temp), temp_operand(right_temp), temp_operand(result_temp))
            elif op_text == '-':
                self.emitter.emit(OpCode.SUB, temp_operand(left_temp), temp_operand(right_temp), temp_operand(result_temp))
            
            left_temp = result_temp
        
        return ExprResult(left_temp)
    
    def visitMultiplicativeExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.unaryExpr(0))
        
        left_result = self.visit(ctx.unaryExpr(0))
        
        # CAMBIO AQUÍ: Asegurar ExprResult válido
        if not isinstance(left_result, ExprResult):
            if left_result is None:
                left_temp = self.emitter.new_temp()
                self.emitter.emit(OpCode.MOV, const_operand(0), None, temp_operand(left_temp))
            else:
                left_temp = self.emitter.new_temp()
                # CORRECCIÓN: usar const_operand para valores literales
                if isinstance(left_result, (int, float, str, bool)):
                    self.emitter.emit(OpCode.MOV, const_operand(left_result), None, temp_operand(left_temp))
                else:
                    self.emitter.emit(OpCode.MOV, var_operand(str(left_result)), None, temp_operand(left_temp))
            left_result = ExprResult(left_temp)
        
        left_temp = left_result.temp
        
        for i in range(1, len(ctx.unaryExpr())):
            op_text = ctx.getChild(2 * i - 1).getText()
            right_result = self.visit(ctx.unaryExpr(i))
            
            # CAMBIO AQUÍ: Asegurar ExprResult válido
            if not isinstance(right_result, ExprResult):
                if right_result is None:
                    right_temp = self.emitter.new_temp()
                    self.emitter.emit(OpCode.MOV, const_operand(0), None, temp_operand(right_temp))
                else:
                    right_temp = self.emitter.new_temp()
                    # CORRECCIÓN: usar const_operand para valores literales
                    if isinstance(right_result, (int, float, str, bool)):
                        self.emitter.emit(OpCode.MOV, const_operand(right_result), None, temp_operand(right_temp))
                    else:
                        self.emitter.emit(OpCode.MOV, var_operand(str(right_result)), None, temp_operand(right_temp))
                right_result = ExprResult(right_temp)
            
            right_temp = right_result.temp
            result_temp = self.emitter.new_temp()
            
            if op_text == '*':
                self.emitter.emit(OpCode.MUL, temp_operand(left_temp), temp_operand(right_temp), temp_operand(result_temp))
            elif op_text == '/':
                self.emitter.emit(OpCode.DIV, temp_operand(left_temp), temp_operand(right_temp), temp_operand(result_temp))
            elif op_text == '%':
                self.emitter.emit(OpCode.MOD, temp_operand(left_temp), temp_operand(right_temp), temp_operand(result_temp))
            
            left_temp = result_temp
        
        return ExprResult(left_temp)

    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 1:
            result = self.visit(ctx.getChild(0))
            # Asegurar que siempre retorna ExprResult
            if not isinstance(result, ExprResult):
                if result is None:
                    temp = self.emitter.new_temp()
                else:
                    temp = self.emitter.new_temp()
                    self.emitter.emit(OpCode.MOV, str(result), None, temp)
                return ExprResult(temp)
            return result
        
        op_text = ctx.getChild(0).getText()
        operand_result = self.visit(ctx.unaryExpr())
        
        # Si no es ExprResult, crear uno
        if not isinstance(operand_result, ExprResult):
            if operand_result is None:
                operand_temp = self.emitter.new_temp()
            else:
                operand_temp = self.emitter.new_temp()
                self.emitter.emit(OpCode.MOV, str(operand_result), None, operand_temp)
            operand_result = ExprResult(operand_temp)
        
        operand_temp = operand_result.temp
        result_temp = self.emitter.new_temp()
        
        if op_text == '-':
            self.emitter.emit(OpCode.NEG, operand_temp, None, result_temp)
        elif op_text == '!':
            self.emitter.emit(OpCode.NOT, operand_temp, None, result_temp)
        else:
            return operand_result
        
        return ExprResult(result_temp)

    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        elif ctx.expression():
            return self.visit(ctx.expression())
        
        temp = self.emitter.new_temp()
        return ExprResult(temp)
    
    def visitLiteralExpr(self, ctx):
        if ctx.Literal():
            value = ctx.Literal().getText()
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand(value), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
        elif ctx.getText() == 'null':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('null'), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.getText() == 'true':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('true'), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.getText() == 'false':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('false'), None, temp_operand(temp))
            return ExprResult(temp)
        
        temp = self.emitter.new_temp()
        return ExprResult(temp)

    def visitLeftHandSide(self, ctx):
        primary_result = self.visit(ctx.primaryAtom())
        
        # Verificar si hay suffixOp (llamadas, índices, propiedades)
        suffix_ops = list(ctx.suffixOp()) if ctx.suffixOp() else []
        
        if len(suffix_ops) == 0:
            return primary_result
        
        # Procesar cada suffixOp en orden
        current_result = primary_result
        for suffix in suffix_ops:
            # Determinar tipo de suffix con comprobaciones seguras por alternativa
            if hasattr(suffix, 'arguments') and suffix.arguments():  # Es una llamada: func()
                # Obtener nombre de función
                func_name = None
                if ctx.primaryAtom().Identifier():
                    func_name = ctx.primaryAtom().Identifier().getText()
                
                if func_name:
                    # Procesar argumentos
                    args = []
                    arg_ctx = suffix.arguments()
                    if hasattr(arg_ctx, 'expression'):
                        expressions = arg_ctx.expression() if callable(arg_ctx.expression) else [arg_ctx.expression]
                        if not isinstance(expressions, list):
                            expressions = [expressions]
                        
                        for expr in expressions:
                            expr_result = self.visit(expr)
                            
                            # Asegurar que tenemos un temporal
                            if isinstance(expr_result, ExprResult):
                                arg_temp = expr_result.temp
                            elif isinstance(expr_result, (int, str, float, bool)):
                                arg_temp = self.emitter.new_temp()
                                self.emitter.emit(OpCode.MOV, const_operand(expr_result), None, temp_operand(arg_temp))
                            else:
                                arg_temp = self.emitter.new_temp()
                                self.emitter.emit(OpCode.MOV, var_operand(str(expr_result)), None, temp_operand(arg_temp))
                            
                            args.append(arg_temp)
                    
                    # Emitir PARAM para cada argumento
                    for arg_temp in args:
                        self.emitter.emit(OpCode.PARAM, temp_operand(arg_temp), None, None)
                    
                    # Generar CALL con el nombre de la función
                    result_temp = self.emitter.new_temp()
                    self.emitter.emit(
                        OpCode.CALL,
                        var_operand(func_name),
                        const_operand(len(args)),
                        temp_operand(result_temp)
                    )
                    
                    current_result = ExprResult(result_temp)
            
            elif hasattr(suffix, 'expression') and suffix.expression():  # Es indexación: arr[index]
                suffix_result = self.visit(suffix)
                if isinstance(suffix_result, ExprResult):
                    current_result = suffix_result

            elif hasattr(suffix, 'Identifier') and suffix.Identifier():  # Es acceso a propiedad: obj.prop
                suffix_result = self.visit(suffix)
                if isinstance(suffix_result, ExprResult):
                    current_result = suffix_result
        
        return current_result
    
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
                true_jump = self.emitter.emit_conditional_jump(OpCode.BLT, left_temp, right_temp, "")
            elif op_text == '<=':
                true_jump = self.emitter.emit_conditional_jump(OpCode.BLE, left_temp, right_temp, "")
            elif op_text == '>':
                true_jump = self.emitter.emit_conditional_jump(OpCode.BGT, left_temp, right_temp, "")
            elif op_text == '>=':
                true_jump = self.emitter.emit_conditional_jump(OpCode.BGE, left_temp, right_temp, "")
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
                true_jump = self.emitter.emit_conditional_jump(OpCode.BEQ, left_temp, right_temp, "")
            elif op_text == '!=':
                true_jump = self.emitter.emit_conditional_jump(OpCode.BNE, left_temp, right_temp, "")
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
            true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
                true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
            true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
                true_jump = self.emitter.emit_conditional_jump(OpCode.BNZ, temp, None, "")
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
            self.emitter.emit(OpCode.MOV, const_operand(value), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.String():
            value = ctx.String().getText()
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand(value), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.Identifier():
            var_name = ctx.Identifier().getText()
            
            # Verificar si es parámetro
            if var_name in self.param_temps:
                return ExprResult(self.param_temps[var_name])
            
            # Para variables regulares, crear un temporal con MOV
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, var_operand(var_name), None, temp_operand(temp))
            return ExprResult(temp)
                
        elif ctx.expression():
            return self.visit(ctx.expression())
        elif ctx.getText() == 'true':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('true'), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.getText() == 'false':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('false'), None, temp_operand(temp))
            return ExprResult(temp)
        elif ctx.getText() == 'null':
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, const_operand('null'), None, temp_operand(temp))
            return ExprResult(temp)

        temp = self.emitter.new_temp()
        return ExprResult(temp)

    def visitFunctionDeclaration(self, ctx):
        func_name = ctx.Identifier().getText()

        params = []
        if ctx.parameters():
            param_list = ctx.parameters()
            if hasattr(param_list, 'parameter'):
                param_contexts = param_list.parameter()
                if not isinstance(param_contexts, list):
                    param_contexts = [param_contexts]
                for param_ctx in param_contexts:
                    if hasattr(param_ctx, 'Identifier'):
                        param_id = param_ctx.Identifier()
                        if param_id:
                            params.append(param_id.getText())

        return_type = "void"
        if ctx.type_():
            return_type = ctx.type_().getText()

        prev_scope = self.current_scope
        self.current_scope = func_name

        self.memory_manager.enter_function(func_name, params)
        self.func_codegen.gen_function_prolog(func_name, params, return_type)
        self.symbol_table.enter_scope()

        self.param_temps = {}
        
        # Generar temporal para cada parámetro
        for i, param in enumerate(params):
            address = self.memory_model.allocate_local(4)
            symbol = SimpleSymbol(param, "parameter", address)
            
            # Crear temporal y asignar el parámetro
            temp = self.emitter.new_temp()
            self.emitter.emit(OpCode.MOV, var_operand(param), None, temp_operand(temp))
            
            self.param_temps[param] = temp
            symbol.temp = temp
            self.symbol_table.insert(param, symbol)

        if ctx.block():
            self.visit(ctx.block())

        self.symbol_table.exit_scope()
        self.func_codegen.gen_function_epilog(func_name)
        self.memory_manager.exit_function()
        
        self.param_temps = {}
        
        self.current_scope = prev_scope
        return None

    def visitReturnStatement(self, ctx):
        if ctx.expression():
            expr_result = self.visit(ctx.expression())
            
            if isinstance(expr_result, ExprResult):
                return_value = expr_result.temp
            else:
                return_value = str(expr_result)
            
            self.func_codegen.gen_return(var_operand(return_value))
        else:
            self.func_codegen.gen_return()

        return None

    def visitCallExpr(self, ctx):
        func_name = None
        parent = ctx.parentCtx
        
        # Buscar el nombre de la función
        current = parent
        while current:
            if hasattr(current, 'primaryAtom') and callable(current.primaryAtom):
                atom = current.primaryAtom()
                if atom and hasattr(atom, 'Identifier') and callable(atom.Identifier):
                    identifier = atom.Identifier()
                    if identifier:
                        func_name = identifier.getText()
                        break
            
            if hasattr(current, 'leftHandSide') and callable(current.leftHandSide):
                lhs = current.leftHandSide()
                if lhs and hasattr(lhs, 'primaryAtom') and callable(lhs.primaryAtom):
                    atom = lhs.primaryAtom()
                    if atom and hasattr(atom, 'Identifier') and callable(atom.Identifier):
                        identifier = atom.Identifier()
                        if identifier:
                            func_name = identifier.getText()
                            break
            
            current = current.parentCtx if hasattr(current, 'parentCtx') else None

        if not func_name:
            return ExprResult(self.emitter.new_temp())

        # Procesar argumentos
        args = []
        if ctx.arguments():
            arg_ctx = ctx.arguments()
            if hasattr(arg_ctx, 'expression'):
                expressions = arg_ctx.expression() if callable(arg_ctx.expression) else [arg_ctx.expression]
                if not isinstance(expressions, list):
                    expressions = [expressions]
                
                for expr in expressions:
                    expr_result = self.visit(expr)
                    
                    # Asegurar que tenemos un temporal
                    if isinstance(expr_result, ExprResult):
                        arg_temp = expr_result.temp
                    elif isinstance(expr_result, (int, str, float, bool)):
                        arg_temp = self.emitter.new_temp()
                        self.emitter.emit(OpCode.MOV, const_operand(expr_result), None, temp_operand(arg_temp))
                    else:
                        arg_temp = self.emitter.new_temp()
                        self.emitter.emit(OpCode.MOV, var_operand(str(expr_result)), None, temp_operand(arg_temp))
                    
                    args.append(arg_temp)

        # Emitir PARAM para cada argumento
        for arg_temp in args:
            self.emitter.emit(OpCode.PARAM, temp_operand(arg_temp), None, None)

        # Generar CALL
        result_temp = self.emitter.new_temp()
        self.emitter.emit(
            OpCode.CALL,
            var_operand(func_name),
            const_operand(len(args)),
            temp_operand(result_temp)
        )

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
        # Obtener la expresión base (el arreglo) desde el padre
        array_name = None
        parent = ctx.parentCtx
        if parent and hasattr(parent, 'primaryAtom') and parent.primaryAtom():
            primary = parent.primaryAtom()
            if hasattr(primary, 'Identifier') and primary.Identifier():
                array_name = primary.Identifier().getText()

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
        var_name = ctx.Identifier().getText()
        var_type = "integer"
        is_array = False
        array_size = 0
        array_dimensions = []

        # Obtener tipo
        if ctx.typeAnnotation():
            type_ctx = ctx.typeAnnotation().type_()
            if type_ctx:
                if hasattr(type_ctx, 'baseType') and type_ctx.baseType():
                    var_type = type_ctx.baseType().getText()
                else:
                    var_type = type_ctx.getText()

                type_text = type_ctx.getText()
                if '[' in type_text and ']' in type_text:
                    is_array = True
                    # Extraer tipo base y dimensiones
                    # Ej: "integer[][]" -> base="integer", dimensions=[0, 0]
                    import re
                    base_match = re.match(r'(\w+)((?:\[\d*\])+)', type_text)
                    if base_match:
                        var_type = base_match.group(1)
                        brackets = base_match.group(2)
                        # Contar dimensiones
                        array_dimensions = [0] * brackets.count('[')

        is_global = (self.current_scope == "global")

        # Asignar memoria (para variables simples o arreglos)
        mem_size = 4
        if is_array and array_dimensions:
            # Para arreglos, asignar espacio basado en dimensiones
            # Nota: Los arreglos dinámicos se asignan en tiempo de ejecución
            mem_size = 4  # Pointer al arreglo

        if is_global:
            address = self.memory_model.allocate_global(mem_size, var_name)
        else:
            address = self.memory_model.allocate_local(mem_size, var_name)

        symbol = SimpleSymbol(var_name, var_type, address)
        # Guardar información de arreglo si aplica
        if is_array:
            symbol.array_dimensions = array_dimensions
        self.symbol_table.insert(var_name, symbol)

        # CAMBIO CRÍTICO: Procesar el inicializador O inicialización por defecto
        if ctx.initializer():
            expr_result = self.visit(ctx.initializer().expression())

            # CAMBIO AQUÍ: Asegurar que expr_result tiene un temporal válido
            if isinstance(expr_result, ExprResult):
                # Generar MOV desde el temporal al nombre de variable
                self.emitter.emit(OpCode.MOV, temp_operand(expr_result.temp), None, var_operand(var_name))
            elif expr_result is not None:
                # Si no es ExprResult, crear temporal primero
                temp = self.emitter.new_temp()
                self.emitter.emit(OpCode.MOV, const_operand(str(expr_result)), None, temp_operand(temp))
                self.emitter.emit(OpCode.MOV, temp_operand(temp), None, var_operand(var_name))

            # Marcar como inicializada
            symbol.is_initialized = True
        else:
            # Sin inicializador: Usar valor por defecto
            default_value = self._get_default_value(var_type)

            # Emitir inicialización con valor por defecto
            temp = self.emitter.new_temp()
            if default_value == 'undefined':
                # Para boolean sin inicializar, usar undefined (no inicializar)
                pass
            else:
                # Inicializar con valor por defecto
                self.emitter.emit(OpCode.MOV, const_operand(default_value), None, temp_operand(temp))
                self.emitter.emit(OpCode.MOV, temp_operand(temp), None, var_operand(var_name))
                # Marcar como inicializada con valor por defecto
                symbol.is_initialized = True

        return None

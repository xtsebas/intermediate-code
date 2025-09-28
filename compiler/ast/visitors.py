import sys
from typing import Optional, List, Any, Union
from antlr4 import *
from grammar.gen.CompiscriptParser import CompiscriptParser
from grammar.gen.CompiscriptVisitor import CompiscriptVisitor
from compiler.ir.emitter import TripletEmitter, BackpatchList
from compiler.ir.triplet import OpCode
from compiler.symtab.symbols import symbol_manager, SymbolKind
from compiler.errors import CompilerError


class ExprResult:
    def __init__(self, temp_name: str = None, is_constant: bool = False, 
                 value: Any = None, data_type: str = "integer"):
        self.temp_name = temp_name
        self.is_constant = is_constant
        self.value = value
        self.data_type = data_type
    
    def get_operand(self):
        if self.is_constant:
            return self.value
        return self.temp_name


class IRGeneratorVisitor(CompiscriptVisitor):
    def __init__(self):
        self.emitter = TripletEmitter()
        self.symbol_manager = symbol_manager
        self.errors = []
        self.in_function = False
        self.current_function = None
    
    def add_error(self, message: str, line: int = 0):
        self.errors.append(CompilerError(message, line))
    
    def get_line_number(self, ctx):
        return ctx.start.line if ctx and ctx.start else 0
    
    # Program
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext):
        try:
            self.symbol_manager.clear_all()
            self.emitter.clear()
            
            for stmt in ctx.statement():
                self.visit(stmt)
            
            return {
                "triplets": self.emitter.get_triplets(),
                "symbols": self.symbol_manager.get_complete_info(),
                "errors": [error.to_dict() for error in self.errors]
            }
        except Exception as e:
            self.add_error(f"Error interno: {str(e)}")
            return {"triplets": [], "symbols": {}, "errors": [error.to_dict() for error in self.errors]}
    
    # Variable declaration
    def visitVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        var_name = ctx.Identifier().getText()
        var_type = "integer"
        
        if ctx.typeAnnotation():
            var_type = self.visit(ctx.typeAnnotation())
        
        try:
            symbol, address = self.symbol_manager.declare_variable(var_name, var_type)
            
            if ctx.initializer():
                init_result = self.visit(ctx.initializer())
                if init_result:
                    self.emitter.emit_assignment(var_name, init_result.get_operand())
                    symbol.is_initialized = True
                    
        except Exception as e:
            self.add_error(f"Error declarando variable '{var_name}': {str(e)}", 
                          self.get_line_number(ctx))
    
    # Constant declaration
    def visitConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        const_name = ctx.Identifier().getText()
        const_type = "integer"
        
        if ctx.typeAnnotation():
            const_type = self.visit(ctx.typeAnnotation())
        
        try:
            init_result = self.visit(ctx.expression())
            symbol, address = self.symbol_manager.declare_variable(
                const_name, const_type, initial_value=init_result.value, is_constant=True
            )
            
            self.emitter.emit_assignment(const_name, init_result.get_operand())
            
        except Exception as e:
            self.add_error(f"Error declarando constante '{const_name}': {str(e)}", 
                          self.get_line_number(ctx))
    
    # Type annotation
    def visitTypeAnnotation(self, ctx: CompiscriptParser.TypeAnnotationContext):
        return self.visit(ctx.type())
    
    def visitType(self, ctx: CompiscriptParser.TypeContext):
        base_type = self.visit(ctx.baseType())
        array_dims = len([child for child in ctx.children if child.getText() == '[]'])
        
        if array_dims > 0:
            return f"{base_type}[]" * array_dims
        return base_type
    
    def visitBaseType(self, ctx: CompiscriptParser.BaseTypeContext):
        return ctx.getText()
    
    # Initializer
    def visitInitializer(self, ctx: CompiscriptParser.InitializerContext):
        return self.visit(ctx.expression())
    
    # Assignment
    def visitAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        if ctx.Identifier():
            var_name = ctx.Identifier().getText()
            expr_result = self.visit(ctx.expression())
            
            symbol, address = self.symbol_manager.lookup_with_address(var_name)
            if not symbol:
                self.add_error(f"Variable '{var_name}' no declarada", self.get_line_number(ctx))
                return
            
            if symbol.kind == SymbolKind.CONSTANT:
                self.add_error(f"No se puede asignar a constante '{var_name}'", self.get_line_number(ctx))
                return
            
            self.emitter.emit_assignment(var_name, expr_result.get_operand())
            symbol.is_initialized = True
        else:
            pass
    
    # Expressions
    def visitAdditiveExpr(self, ctx: CompiscriptParser.AdditiveExprContext):
        left_result = self.visit(ctx.multiplicativeExpr(0))
        
        for i in range(1, len(ctx.multiplicativeExpr())):
            right_result = self.visit(ctx.multiplicativeExpr(i))
            op_text = ctx.getChild(2*i-1).getText()
            
            op = OpCode.ADD if op_text == '+' else OpCode.SUB
            result_temp = self.emitter.emit_binary_op(
                op, left_result.get_operand(), right_result.get_operand()
            )
            
            left_result = ExprResult(result_temp)
        
        return left_result
    
    def visitMultiplicativeExpr(self, ctx: CompiscriptParser.MultiplicativeExprContext):
        left_result = self.visit(ctx.unaryExpr(0))
        
        for i in range(1, len(ctx.unaryExpr())):
            right_result = self.visit(ctx.unaryExpr(i))
            op_text = ctx.getChild(2*i-1).getText()
            
            if op_text == '*':
                op = OpCode.MUL
            elif op_text == '/':
                op = OpCode.DIV
            else:  # '%'
                op = OpCode.MOD
            
            result_temp = self.emitter.emit_binary_op(
                op, left_result.get_operand(), right_result.get_operand()
            )
            
            left_result = ExprResult(result_temp)
        
        return left_result
    
    def visitUnaryExpr(self, ctx: CompiscriptParser.UnaryExprContext):
        if ctx.getChildCount() == 2:  # unary operation
            op_text = ctx.getChild(0).getText()
            operand_result = self.visit(ctx.unaryExpr())
            
            op = OpCode.NEG if op_text == '-' else OpCode.NOT
            result_temp = self.emitter.emit_unary_op(op, operand_result.get_operand())
            
            return ExprResult(result_temp)
        else:
            return self.visit(ctx.primaryExpr())
    
    def visitLogicalOrExpr(self, ctx: CompiscriptParser.LogicalOrExprContext):
        left_result = self.visit(ctx.logicalAndExpr(0))
        
        for i in range(1, len(ctx.logicalAndExpr())):
            right_result = self.visit(ctx.logicalAndExpr(i))
            result_temp = self.emitter.emit_binary_op(
                OpCode.OR, left_result.get_operand(), right_result.get_operand()
            )
            left_result = ExprResult(result_temp)
        
        return left_result
    
    def visitLogicalAndExpr(self, ctx: CompiscriptParser.LogicalAndExprContext):
        left_result = self.visit(ctx.equalityExpr(0))
        
        for i in range(1, len(ctx.equalityExpr())):
            right_result = self.visit(ctx.equalityExpr(i))
            result_temp = self.emitter.emit_binary_op(
                OpCode.AND, left_result.get_operand(), right_result.get_operand()
            )
            left_result = ExprResult(result_temp)
        
        return left_result
    
    def visitEqualityExpr(self, ctx: CompiscriptParser.EqualityExprContext):
        left_result = self.visit(ctx.relationalExpr(0))
        
        for i in range(1, len(ctx.relationalExpr())):
            right_result = self.visit(ctx.relationalExpr(i))
            op_text = ctx.getChild(2*i-1).getText()
            
            op = OpCode.EQ if op_text == '==' else OpCode.NE
            result_temp = self.emitter.emit_binary_op(
                op, left_result.get_operand(), right_result.get_operand()
            )
            left_result = ExprResult(result_temp)
        
        return left_result
    
    def visitRelationalExpr(self, ctx: CompiscriptParser.RelationalExprContext):
        left_result = self.visit(ctx.additiveExpr(0))
        
        for i in range(1, len(ctx.additiveExpr())):
            right_result = self.visit(ctx.additiveExpr(i))
            op_text = ctx.getChild(2*i-1).getText()
            
            op_map = {'<': OpCode.LT, '<=': OpCode.LE, '>': OpCode.GT, '>=': OpCode.GE}
            op = op_map[op_text]
            
            result_temp = self.emitter.emit_binary_op(
                op, left_result.get_operand(), right_result.get_operand()
            )
            left_result = ExprResult(result_temp)
        
        return left_result
    
    # Primary expressions
    def visitPrimaryExpr(self, ctx: CompiscriptParser.PrimaryExprContext):
        if ctx.literalExpr():
            return self.visit(ctx.literalExpr())
        elif ctx.leftHandSide():
            return self.visit(ctx.leftHandSide())
        else:  # parenthesized expression
            return self.visit(ctx.expression())
    
    def visitLiteralExpr(self, ctx: CompiscriptParser.LiteralExprContext):
        if ctx.Literal():
            literal_text = ctx.Literal().getText()
            if literal_text.startswith('"') and literal_text.endswith('"'):
                # String literal
                value = literal_text[1:-1]  # remove quotes
                return ExprResult(value=value, is_constant=True, data_type="string")
            else:
                # Integer literal
                value = int(literal_text)
                return ExprResult(value=value, is_constant=True, data_type="integer")
        elif ctx.getText() == 'true':
            return ExprResult(value=True, is_constant=True, data_type="boolean")
        elif ctx.getText() == 'false':
            return ExprResult(value=False, is_constant=True, data_type="boolean")
        elif ctx.getText() == 'null':
            return ExprResult(value=None, is_constant=True, data_type="null")
        elif ctx.arrayLiteral():
            return self.visit(ctx.arrayLiteral())
    
    def visitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        var_name = ctx.Identifier().getText()
        symbol, address = self.symbol_manager.lookup_with_address(var_name)
        
        if not symbol:
            self.add_error(f"Variable '{var_name}' no declarada", self.get_line_number(ctx))
            return ExprResult("error")
        
        if not symbol.is_initialized and symbol.kind == SymbolKind.VARIABLE:
            self.add_error(f"Variable '{var_name}' usada antes de inicializar", self.get_line_number(ctx))
        
        result_temp = self.emitter.new_temp()
        self.emitter.emit_assignment(result_temp, var_name)
        
        return ExprResult(result_temp, data_type=symbol.symbol_type)
    
    # Left-hand side
    def visitLeftHandSide(self, ctx: CompiscriptParser.LeftHandSideContext):
        base_result = self.visit(ctx.primaryAtom())
        
        for suffix in ctx.suffixOp():
            if isinstance(suffix, CompiscriptParser.CallExprContext):
                args = []
                if suffix.arguments():
                    args = self.visit(suffix.arguments())
                
                result_temp = self.emitter.emit_call(base_result.get_operand(), args)
                base_result = ExprResult(result_temp)
                
            elif isinstance(suffix, CompiscriptParser.IndexExprContext):
                index_result = self.visit(suffix.expression())
                result_temp = self.emitter.emit_array_access(
                    base_result.get_operand(), index_result.get_operand()
                )
                base_result = ExprResult(result_temp)
                
            elif isinstance(suffix, CompiscriptParser.PropertyAccessExprContext):
                field_name = suffix.Identifier().getText()
                result_temp = self.emitter.emit_field_access(
                    base_result.get_operand(), field_name
                )
                base_result = ExprResult(result_temp)
        
        return base_result
    
    # Control flow
    def visitIfStatement(self, ctx: CompiscriptParser.IfStatementContext):
        condition_result = self.visit(ctx.expression())
        
        else_label = self.emitter.new_label('if_false')
        end_label = self.emitter.new_label('if_end')
        
        # if condition == false goto else_label
        self.emitter.emit_conditional_jump(OpCode.BZ, condition_result.get_operand(), None, else_label)
        
        # then block
        self.visit(ctx.block(0))
        
        if ctx.block(1):  # has else
            self.emitter.emit_jump(end_label)
            self.emitter.emit_label(else_label)
            self.visit(ctx.block(1))
            self.emitter.emit_label(end_label)
        else:
            self.emitter.emit_label(else_label)
    
    def visitWhileStatement(self, ctx: CompiscriptParser.WhileStatementContext):
        start_label = self.emitter.new_label('loop_start')
        end_label = self.emitter.new_label('loop_end')
        
        continue_label, break_label = self.emitter.enter_loop()
        
        self.emitter.emit_label(start_label)
        condition_result = self.visit(ctx.expression())
        
        # if condition == false goto end_label
        self.emitter.emit_conditional_jump(OpCode.BZ, condition_result.get_operand(), None, end_label)
        
        self.visit(ctx.block())
        
        self.emitter.emit_jump(start_label)
        self.emitter.emit_label(end_label)
        
        self.emitter.exit_loop(start_label, end_label)
    
    def visitBreakStatement(self, ctx: CompiscriptParser.BreakStatementContext):
        self.emitter.emit_break()
    
    def visitContinueStatement(self, ctx: CompiscriptParser.ContinueStatementContext):
        self.emitter.emit_continue()
    
    # Functions
    def visitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        func_name = ctx.Identifier().getText()
        return_type = "void"
        
        if ctx.type():
            return_type = self.visit(ctx.type())
        
        parameters = []
        if ctx.parameters():
            parameters = self.visit(ctx.parameters())
        
        try:
            func_symbol = self.symbol_manager.enter_function_context(func_name, return_type, parameters)
            
            self.in_function = True
            self.current_function = func_name
            
            self.emitter.enter_function(func_name, [p[0] for p in parameters])
            
            self.visit(ctx.block())
            
            if return_type == "void":
                self.emitter.emit_return()
            
            self.emitter.exit_function()
            self.symbol_manager.exit_function_context()
            
            self.in_function = False
            self.current_function = None
            
        except Exception as e:
            self.add_error(f"Error en función '{func_name}': {str(e)}", self.get_line_number(ctx))
    
    def visitParameters(self, ctx: CompiscriptParser.ParametersContext):
        params = []
        for param_ctx in ctx.parameter():
            param_info = self.visit(param_ctx)
            params.append(param_info)
        return params
    
    def visitParameter(self, ctx: CompiscriptParser.ParameterContext):
        param_name = ctx.Identifier().getText()
        param_type = "integer"
        
        if ctx.type():
            param_type = self.visit(ctx.type())
        
        return (param_name, param_type)
    
    def visitReturnStatement(self, ctx: CompiscriptParser.ReturnStatementContext):
        if not self.in_function:
            self.add_error("return fuera de función", self.get_line_number(ctx))
            return
        
        if ctx.expression():
            return_result = self.visit(ctx.expression())
            self.emitter.emit_return(return_result.get_operand())
        else:
            self.emitter.emit_return()
    
    # Statements
    def visitBlock(self, ctx: CompiscriptParser.BlockContext):
        self.symbol_manager.symbol_table.enter_scope("block")
        
        for stmt in ctx.statement():
            self.visit(stmt)
        
        self.symbol_manager.symbol_table.exit_scope()
    
    def visitExpressionStatement(self, ctx: CompiscriptParser.ExpressionStatementContext):
        self.visit(ctx.expression())
    
    def visitPrintStatement(self, ctx: CompiscriptParser.PrintStatementContext):
        expr_result = self.visit(ctx.expression())
        self.emitter.emit(OpCode.PRINT, expr_result.get_operand())
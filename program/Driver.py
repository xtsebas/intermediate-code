import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
compiler_path = os.path.join(parent_dir, 'compiler')

sys.path.insert(0, parent_dir)
sys.path.insert(0, compiler_path)

from antlr4 import FileStream, CommonTokenStream
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from ir.emitter import TripletEmitter
from ir.triplet import Operand
from codegen.expr_codegen import ExprCodeGen


def print_separator(title=""):
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}\n")


def main(argv):
    if len(argv) < 2:
        print("Uso: python3 Driver.py <archivo.cps>")
        return 1
    
    input_file = argv[1]
    
    print_separator("COMPILADOR COMPISCRIPT - TAC GENERATOR")
    print(f"Archivo de entrada: {input_file}\n")
    
    try:
        input_stream = FileStream(input_file, encoding='utf-8')
        
        print_separator("FASE 1: ANALISIS LEXICO")
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        stream.fill()
        
        token_count = len(stream.tokens)
        print(f"Tokens reconocidos: {token_count}")
        print("Analisis lexico completado exitosamente")
        
        print_separator("FASE 2: ANALISIS SINTACTICO")
        parser = CompiscriptParser(stream)
        tree = parser.program()
        
        if parser.getNumberOfSyntaxErrors() > 0:
            print(f"Errores de sintaxis: {parser.getNumberOfSyntaxErrors()}")
            return 1
        
        print("Arbol sintactico generado exitosamente")
        print("Analisis sintactico completado sin errores")
        
        print_separator("FASE 3: GENERACION DE CODIGO INTERMEDIO (TAC)")
        
        emitter = TripletEmitter()
        codegen = ExprCodeGen(emitter)
        
        print("Generando ejemplos de codigo intermedio...\n")
        
        print("Ejemplo 1: Expresion aritmetica")
        print("  Codigo: result = (5 + 3) * 2")
        
        const_5 = codegen.gen_literal(5)
        const_3 = codegen.gen_literal(3)
        const_2 = codegen.gen_literal(2)
        
        t1 = codegen.gen_binary_expr('+', const_5, const_3)
        t2 = codegen.gen_binary_expr('*', t1, const_2)
        codegen.gen_assignment('result', t2)
        
        print("\nTripletos generados:")
        print(emitter.table)
        print()
        
        emitter2 = TripletEmitter()
        codegen2 = ExprCodeGen(emitter2)
        
        print("\nEjemplo 2: Expresion con comparacion")
        print("  Codigo: flag = (x > 10) && (y < 20)")
        
        var_x = codegen2.gen_variable('x')
        const_10 = codegen2.gen_literal(10)
        var_y = codegen2.gen_variable('y')
        const_20 = codegen2.gen_literal(20)
        
        t1 = codegen2.gen_binary_expr('>', var_x, const_10)
        t2 = codegen2.gen_binary_expr('<', var_y, const_20)
        t3 = codegen2.gen_binary_expr('&&', t1, t2)
        codegen2.gen_assignment('flag', t3)
        
        print("\nTripletos generados:")
        print(emitter2.table)
        print()
        
        emitter3 = TripletEmitter()
        codegen3 = ExprCodeGen(emitter3)
        
        print("\nEjemplo 3: Operador unario")
        print("  Codigo: y = -(x + 5)")
        
        var_x = codegen3.gen_variable('x')
        const_5 = codegen3.gen_literal(5)
        
        t1 = codegen3.gen_binary_expr('+', var_x, const_5)
        t2 = codegen3.gen_unary_expr('-', t1)
        codegen3.gen_assignment('y', t2)
        
        print("\nTripletos generados:")
        print(emitter3.table)
        
        print_separator("ESTADISTICAS GENERALES")
        stats = emitter.get_stats()
        print(f"Total de tripletos (ej. 1): {stats['triplets_count']}")
        print(f"Etiquetas generadas: {stats['labels_generated']}")
        print(f"Temporales max simultaneos: {stats['temp_stats']['max_simultaneous']}")
        
        print_separator("COMPILACION COMPLETADA")
        print("NOTA: La integracion completa con el visitor del AST esta pendiente")
        print("      Este driver muestra la generacion de TAC para expresiones")
        
        return 0
        
    except Exception as e:
        print_separator("ERROR")
        print(f"Error: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main(sys.argv)
    sys.exit(exit_code)
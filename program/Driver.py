import sys
import os
from antlr4 import *

# Configurar rutas
current_dir = os.path.dirname(__file__)
grammar_dir = os.path.join(current_dir, 'grammar', 'gen')
parent_dir = os.path.dirname(current_dir)

# Añadir rutas al path
sys.path.insert(0, grammar_dir)
sys.path.insert(0, parent_dir)

# Imports de la gramática generada
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from grammar.CompiscriptVisitor import CompiscriptVisitor

# Import del visitor TAC
from compiler.syntax_tree.visitors import CompiscriptTACVisitor


def print_separator(title=""):
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"{'='*60}\n")


def main(argv):
    if len(argv) < 2:
        print("Usage: python Driver.py <source_file.cps>")
        sys.exit(1)
    
    input_file = argv[1]
    
    print_separator("COMPILADOR COMPISCRIPT - TAC GENERATOR")
    print(f"Archivo de entrada: {input_file}\n")
    
    try:
        # Fase 1: Análisis Léxico
        print_separator("FASE 1: ANALISIS LEXICO")
        input_stream = FileStream(input_file, encoding='utf-8')
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        stream.fill()
        
        token_count = len(stream.tokens)
        print(f"Tokens reconocidos: {token_count}")
        print("Análisis léxico completado exitosamente")
        
        # Fase 2: Análisis Sintáctico
        print_separator("FASE 2: ANALISIS SINTACTICO")
        parser = CompiscriptParser(stream)
        tree = parser.program()
        
        if parser.getNumberOfSyntaxErrors() > 0:
            print(f"Errores de sintaxis: {parser.getNumberOfSyntaxErrors()}")
            return 1
        
        print("Árbol sintáctico generado exitosamente")
        print("Análisis sintáctico completado sin errores")
        
        # Fase 3: Generación de TAC
        print_separator("FASE 3: GENERACION DE CODIGO INTERMEDIO (TAC)")
        
        # Pasamos las clases Parser y Visitor como parámetros
        visitor = CompiscriptTACVisitor(CompiscriptParser, CompiscriptVisitor)
        visitor.visit(tree)
        
        # Mostrar tripletos generados
        print("\n=== TRIPLETS GENERADOS ===")
        triplets = visitor.get_triplets()
        if triplets:
            for i, triplet in enumerate(triplets):
                print(f"{i:3}: {triplet}")
        else:
            print("No se generaron tripletos (archivo vacío o sin instrucciones)")
        
        # Mostrar tabla de símbolos
        print("\n=== TABLA DE SIMBOLOS ===")
        symbols = visitor.get_symbols()
        if symbols:
            for name, symbol in symbols.items():
                print(f"  {name}: {symbol}")
        else:
            print("Tabla de símbolos vacía")
        
        print_separator("COMPILACION COMPLETADA")
        print("Compilación completada exitosamente!")
        
        return 0
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo '{input_file}'")
        return 1
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
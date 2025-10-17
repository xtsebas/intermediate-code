#!/usr/bin/env python3
"""
Script de prueba para verificar la generación de tripletos
para variables con inicialización por defecto.
"""

import sys
import os

# Configurar rutas
current_dir = os.path.dirname(__file__)
program_dir = os.path.join(current_dir, 'program')
grammar_dir = os.path.join(program_dir, 'grammar', 'gen')

# Añadir rutas al path
sys.path.insert(0, grammar_dir)
sys.path.insert(0, current_dir)

try:
    from antlr4 import *
    from CompiscriptLexer import CompiscriptLexer
    from CompiscriptParser import CompiscriptParser
    from program.grammar.CompiscriptVisitor import CompiscriptVisitor
    from compiler.syntax_tree.visitors import CompiscriptTACVisitor

    DEPENDENCIES_OK = True
except ImportError as e:
    DEPENDENCIES_OK = False
    IMPORT_ERROR = str(e)


def test_default_initialization():
    """Test que las variables sin inicializador generen tripletos"""

    if not DEPENDENCIES_OK:
        print("ERROR: Faltan dependencias")
        print(f"Error de importación: {IMPORT_ERROR}")
        print("\nPor favor instale las dependencias:")
        print("  pip install -r requirements.txt")
        return False

    # Código de prueba
    test_code = """
const PI: integer = 314;
let greeting: string = "Hello, Compiscript!";
let flag: boolean;
let name: string;
let value: integer;
"""

    print("="*70)
    print("TEST: Generación de Tripletos para Inicialización por Defecto")
    print("="*70)
    print("\nCódigo de entrada:")
    print("-"*70)
    print(test_code)
    print("-"*70)

    try:
        # Compilar
        input_stream = InputStream(test_code)
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = CompiscriptParser(stream)
        tree = parser.program()

        if parser.getNumberOfSyntaxErrors() > 0:
            print(f"\n❌ Errores de sintaxis: {parser.getNumberOfSyntaxErrors()}")
            return False

        # Generar TAC
        visitor = CompiscriptTACVisitor(CompiscriptParser, CompiscriptVisitor)
        visitor.visit(tree)

        # Obtener resultados
        triplets = visitor.get_triplets()
        symbols = visitor.get_symbols()

        print("\n✅ COMPILACIÓN EXITOSA\n")

        # Mostrar tripletos
        print("="*70)
        print("TRIPLETS GENERADOS:")
        print("="*70)
        if triplets:
            for i, triplet in enumerate(triplets):
                print(f"{i:3}: {triplet}")
            print(f"\n📊 Total de tripletos: {len(triplets)}")
        else:
            print("⚠️  No se generaron tripletos")

        # Mostrar símbolos
        print("\n" + "="*70)
        print("TABLA DE SÍMBOLOS:")
        print("="*70)
        if symbols:
            for name, symbol in symbols.items():
                print(f"  {name:15} -> {symbol}")
            print(f"\n📊 Total de símbolos: {len(symbols)}")
        else:
            print("⚠️  Tabla de símbolos vacía")

        # Verificaciones
        print("\n" + "="*70)
        print("VERIFICACIONES:")
        print("="*70)

        expected_symbols = ['PI', 'greeting', 'flag', 'name', 'value']
        found_symbols = [name for name in expected_symbols if name in symbols]

        print(f"✓ Símbolos esperados: {len(expected_symbols)}")
        print(f"✓ Símbolos encontrados: {len(found_symbols)}")

        if len(found_symbols) == len(expected_symbols):
            print("✅ Todos los símbolos registrados correctamente")
        else:
            print(f"⚠️  Faltan símbolos: {set(expected_symbols) - set(found_symbols)}")

        # Verificar que se generaron tripletos de inicialización para variables sin valor
        print(f"\n✓ Se esperan al menos 5 tripletos (uno por cada declaración)")
        if len(triplets) >= 5:
            print(f"✅ Se generaron {len(triplets)} tripletos")
        else:
            print(f"⚠️  Solo se generaron {len(triplets)} tripletos")

        # Buscar asignaciones de valores por defecto
        default_assignments = []
        for triplet in triplets:
            triplet_str = str(triplet)
            if 'flag' in triplet_str and 'false' in triplet_str:
                default_assignments.append('flag = false')
            elif 'name' in triplet_str and '""' in triplet_str:
                default_assignments.append('name = ""')
            elif 'value' in triplet_str and '= 0' in triplet_str:
                default_assignments.append('value = 0')

        print(f"\n✓ Asignaciones por defecto encontradas: {len(default_assignments)}")
        for assignment in default_assignments:
            print(f"  ✓ {assignment}")

        if len(default_assignments) >= 3:
            print("\n🎉 ¡TEST EXITOSO! Variables sin inicializador generan tripletos correctamente")
            return True
        else:
            print("\n⚠️  Algunas variables sin inicializador no generaron tripletos")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n")
    success = test_default_initialization()
    print("\n" + "="*70)
    if success:
        print("RESULTADO: ✅ PASS")
        sys.exit(0)
    else:
        print("RESULTADO: ❌ FAIL")
        sys.exit(1)

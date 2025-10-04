import streamlit as st
from datetime import datetime
import io
import sys
import os
from antlr4 import *

# Configurar rutas para importar el compilador
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
program_dir = os.path.join(parent_dir, 'program')
grammar_dir = os.path.join(program_dir, 'grammar', 'gen')

# Añadir al path
if grammar_dir not in sys.path:
    sys.path.insert(0, grammar_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Imports de la gramática generada
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from program.grammar.CompiscriptVisitor import CompiscriptVisitor

# Import del visitor TAC
from compiler.syntax_tree.visitors import CompiscriptTACVisitor

def compile_code(source_code):
    """Compile Compiscript code and return results"""
    try:
        # Fase 1: Análisis Léxico
        input_stream = InputStream(source_code)
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        stream.fill()

        token_count = len(stream.tokens)

        # Fase 2: Análisis Sintáctico
        parser = CompiscriptParser(stream)
        tree = parser.program()

        if parser.getNumberOfSyntaxErrors() > 0:
            return {
                'success': False,
                'errors': [f'Errores de sintaxis: {parser.getNumberOfSyntaxErrors()}'],
                'triplets': [],
                'symbols': {},
                'memory': {},
                'arrays': {}
            }

        # Fase 3: Generación de TAC
        visitor = CompiscriptTACVisitor(CompiscriptParser, CompiscriptVisitor)
        visitor.visit(tree)

        # Recolectar resultados
        triplets = visitor.get_triplets()
        symbols = visitor.get_symbols()

        # Obtener información de memoria
        memory_layout = visitor.memory_manager.get_memory_layout()
        memory_info = {
            'global_size': memory_layout['global_segment']['total_size'],
            'constant_size': memory_layout['const_segment']['total_size'],
            'current_function': memory_layout['current_function'],
            'stack_depth': memory_layout['activation_stack_depth']
        }

        # Obtener información de arreglos
        arrays = visitor.array_codegen.get_all_arrays()

        return {
            'success': True,
            'errors': [],
            'token_count': token_count,
            'triplets': triplets,
            'symbols': symbols,
            'memory': memory_info,
            'arrays': arrays
        }

    except Exception as e:
        return {
            'success': False,
            'errors': [f'{type(e).__name__}: {str(e)}'],
            'triplets': [],
            'symbols': {},
            'memory': {},
            'arrays': {}
        }

def init_session_state():
    """Initialize session state variables"""
    if 'compiled' not in st.session_state:
        st.session_state.compiled = False
    if 'code_content' not in st.session_state:
        st.session_state.code_content = ""
    if 'filename' not in st.session_state:
        st.session_state.filename = None
    if 'compilation_result' not in st.session_state:
        st.session_state.compilation_result = None

def main():
    st.set_page_config(
        page_title="Compiscript IDE",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded"
    )


    init_session_state()

    # Header
    st.title("🔧 Compiscript IDE - Generador de Código Intermedio")
    st.markdown("**Compilador de Compiscript con generación de Three Address Code (TAC)**")

    # Sidebar for file upload and controls
    with st.sidebar:
        st.header("📁 Cargar Archivo")

        uploaded_file = st.file_uploader(
            "Seleccionar archivo .cps",
            type=['cps'],
            help="Seleccione un archivo Compiscript (.cps)"
        )

        if uploaded_file is not None:
            # Read file content
            file_content = uploaded_file.read().decode('utf-8')
            st.session_state.code_content = file_content
            st.session_state.filename = uploaded_file.name
            st.session_state.compiled = False
            st.success(f"✅ Archivo cargado: {uploaded_file.name}")

        st.markdown("---")

        st.header("🔧 Controles")
        compile_button = st.button("🚀 Compilar", type="primary", use_container_width=True)

        if st.button("🗑️ Limpiar", use_container_width=True):
            st.session_state.code_content = ""
            st.session_state.filename = None
            st.session_state.compiled = False
            st.rerun()

        st.markdown("---")
    # Main content area - Editor de Código
    st.header("📝 Editor de Código")

    # Code editor with enhanced styling
    code = st.text_area(
        "Código Compiscript:",
        value=st.session_state.code_content,
        height=500,
        key="code_editor",
        help="Contenido del archivo .cps cargado o escriba código manualmente",
        placeholder="""// Ejemplo de código Compiscript
var a = 5;
var b = 10;
var result = a + b * 2;
print result;

fun factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}"""
    )

    # Update session state when text changes
    if code != st.session_state.code_content:
        st.session_state.code_content = code
        st.session_state.compiled = False

    # Code statistics
    lines = len(code.split('\n'))
    chars = len(code)
    words = len(code.split())

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Líneas", lines)
    col_stat2.metric("Caracteres", chars)
    col_stat3.metric("Palabras", words)

    # Compilation trigger
    if compile_button and code.strip():
        with st.spinner("🔄 Compilando..."):
            result = compile_code(code)
            st.session_state.compilation_result = result
            st.session_state.compiled = True

        if result['success']:
            st.success(f"✅ Compilación exitosa - {result.get('token_count', 0)} tokens reconocidos")
        else:
            st.error("❌ Error de compilación")
            for error in result['errors']:
                st.error(error)

    elif compile_button and not code.strip():
        st.error("⚠️ No hay código para compilar. Cargue un archivo .cps o escriba código.")

    # Mostrar resultados de compilación
    if st.session_state.compilation_result and st.session_state.compiled:
        result = st.session_state.compilation_result

        st.markdown("---")
        st.header("📊 Resultados de Compilación")

        # Tabs para organizar resultados
        tab1, tab2, tab3, tab4 = st.tabs(["📝 Triplets TAC", "🔤 Tabla de Símbolos", "💾 Memoria", "📦 Arreglos"])

        with tab1:
            st.subheader("Triplets de Código Intermedio (TAC)")
            if result['triplets']:
                triplet_text = ""
                for i, triplet in enumerate(result['triplets']):
                    triplet_text += f"{i:3}: {triplet}\n"
                st.code(triplet_text, language="asm")
                st.info(f"Total de triplets: {len(result['triplets'])}")
            else:
                st.warning("No se generaron triplets")

        with tab2:
            st.subheader("Tabla de Símbolos")
            if result['symbols']:
                for name, symbol in result['symbols'].items():
                    st.text(f"{name}: {symbol}")
                st.info(f"Total de símbolos: {len(result['symbols'])}")
            else:
                st.warning("Tabla de símbolos vacía")

        with tab3:
            st.subheader("Layout de Memoria")
            if result['memory']:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Segmento Global", f"{result['memory'].get('global_size', 0)} bytes")
                    st.metric("Segmento Constantes", f"{result['memory'].get('constant_size', 0)} bytes")
                with col2:
                    st.metric("Función Actual", result['memory'].get('current_function', 'None'))
                    st.metric("Profundidad Stack", result['memory'].get('stack_depth', 0))
            else:
                st.warning("Sin información de memoria")

        with tab4:
            st.subheader("Arreglos Declarados")
            if result['arrays']:
                for name, array_info in result['arrays'].items():
                    st.text(f"{name}: {array_info}")
                st.info(f"Total de arreglos: {len(result['arrays'])}")
            else:
                st.warning("No hay arreglos declarados")

if __name__ == "__main__":
    main()
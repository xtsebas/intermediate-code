import streamlit as st
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

from compiler.backend_new.frontend import IRBuilder
from compiler.backend_new.ir_lowering import lower_program
from compiler.backend_new.optimizer import TACOptimizer
from compiler.backend_new.mips_generator import MIPSBackend
from compiler.backend_new.ir_nodes import IntLiteral, StringLiteral, BoolLiteral, ArrayLiteral

def _describe_expression(expr):
    if expr is None:
        return "-"
    if isinstance(expr, IntLiteral):
        return str(expr.value)
    if isinstance(expr, StringLiteral):
        return f"\"{expr.value}\""
    if isinstance(expr, BoolLiteral):
        return "true" if expr.value else "false"
    if isinstance(expr, ArrayLiteral):
        return f"array[{len(expr.elements)}]"
    return expr.__class__.__name__


def _summarize_symbols(program_ir):
    globals_info = []
    for glob in program_ir.globals:
        globals_info.append({
            "Nombre": glob.name,
            "Tipo": glob.var_type,
            "Mutable": "sí" if glob.mutable else "no",
            "Inicializador": _describe_expression(glob.initializer),
        })

    functions_info = []
    for fn in program_ir.functions:
        params = ", ".join(param.name for param in fn.params) or "—"
        functions_info.append({
            "Función": fn.name,
            "Parámetros": params,
            "Retorna": fn.return_type,
        })

    return {"globals": globals_info, "functions": functions_info}


def compile_code(source_code):
    """Compile Compiscript code with new backend and return results"""
    try:
        input_stream = InputStream(source_code)
        lexer = CompiscriptLexer(input_stream)
        stream = CommonTokenStream(lexer)
        stream.fill()

        token_count = len(stream.tokens)

        parser = CompiscriptParser(stream)
        tree = parser.program()

        if parser.getNumberOfSyntaxErrors() > 0:
            return {
                'success': False,
                'errors': [f'Errores de sintaxis: {parser.getNumberOfSyntaxErrors()}'],
            }

        builder = IRBuilder()
        program_ir = builder.visitProgram(tree)
        symbol_table = _summarize_symbols(program_ir)

        tac_program = lower_program(program_ir)
        optimizer = TACOptimizer()
        tac_program = optimizer.optimize_program(tac_program)
        tac_dump = tac_program.dump()

        backend = MIPSBackend()
        asm_code = backend.generate(tac_program)

        return {
            'success': True,
            'errors': [],
            'token_count': token_count,
            'symbols': symbol_table,
            'tac': tac_dump,
            'asm': asm_code,
        }

    except Exception as e:
        return {
            'success': False,
            'errors': [f'{type(e).__name__}: {str(e)}'],
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
    st.title("⚙️ Compiscript IDE")
    st.markdown("Compila código Compiscript directamente a TAC y MIPS")

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
    st.header("📝 Editor de Código")
    editor_col, preview_col = st.columns(2)

    with editor_col:
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
}""",
        )

    with preview_col:
        st.markdown("**Vista con números de línea**")
        preview_text = code if code.strip() else "// Sin código"
        st.code(preview_text, language="javascript", line_numbers=True)

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
        if not result.get('success'):
            st.error("No se pudo generar TAC/ASM.")
            for error in result.get('errors', []):
                st.error(error)
        else:
            tab_symbols, tab_tac, tab_asm = st.tabs(["🔤 Tabla de Símbolos", "🧮 TAC", "🛠️ Código MIPS"])

            with tab_symbols:
                st.subheader("Símbolos detectados")
                symbols = result.get('symbols', {})
                globals_info = symbols.get('globals', [])
                functions_info = symbols.get('functions', [])

                st.markdown("**Variables Globales**")
                if globals_info:
                    st.table(globals_info)
                else:
                    st.info("No se detectaron variables globales.")

                st.markdown("**Funciones**")
                if functions_info:
                    st.table(functions_info)
                else:
                    st.info("No hay funciones definidas.")

            with tab_tac:
                st.subheader("Three Address Code (TAC)")
                tac_text = result.get('tac', '').strip()
                if tac_text:
                    st.code(tac_text, language="asm", line_numbers=True)
                else:
                    st.info("No se generó TAC.")

            with tab_asm:
                st.subheader("Código ensamblador MIPS")
                asm_text = result.get('asm', '').strip()
                if asm_text:
                    st.code(asm_text, language="asm", line_numbers=True)
                    st.download_button(
                        "💾 Descargar ASM",
                        data=asm_text,
                        file_name="program.asm",
                        mime="text/plain",
                        use_container_width=True,
                    )
                else:
                    st.info("No se generó código ensamblador.")

if __name__ == "__main__":
    main()

import streamlit as st
from datetime import datetime
import io

def init_session_state():
    """Initialize session state variables"""
    if 'compiled' not in st.session_state:
        st.session_state.compiled = False
    if 'code_content' not in st.session_state:
        st.session_state.code_content = ""
    if 'filename' not in st.session_state:
        st.session_state.filename = None
    if 'compilation_errors' not in st.session_state:
        st.session_state.compilation_errors = []
    if 'compilation_warnings' not in st.session_state:
        st.session_state.compilation_warnings = []

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

        st.header(" Estado de Compilación")
        if st.session_state.filename:
            st.info(f"📄 Archivo: {st.session_state.filename}")

        if st.session_state.compiled:
            st.success("✅ Listo para compilar")
            st.info(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        else:
            st.warning("⏳ Sin compilar")

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header(" Editor de Código")

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

    with col2:
        st.header(" Información del Código")

        # Code statistics
        lines = len(code.split('\n'))
        chars = len(code)
        words = len(code.split())

        col2a, col2b, col2c = st.columns(3)
        col2a.metric("Líneas", lines)
        col2b.metric("Caracteres", chars)
        col2c.metric("Palabras", words)

        st.markdown("###  Vista Previa")
        if code.strip():
            st.code(code, language="c")  # C-like syntax highlighting for Compiscript
        else:
            st.info("El editor está vacío. Cargue un archivo .cps o escriba código.")

    # Compilation trigger
    if compile_button and code.strip():
        with st.spinner(" Compilando..."):
            # TODO: Aquí se integrará con el compilador real
            st.session_state.compiled = True
        st.success(" Listo para compilar - Integración pendiente")
        st.info("El botón de compilar está preparado para conectarse con el compilador.")
    elif compile_button and not code.strip():
        st.error(" No hay código para compilar. Cargue un archivo .cps o escriba código.")

if __name__ == "__main__":
    main()
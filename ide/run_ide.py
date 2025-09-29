#!/usr/bin/env python3
"""
Script para ejecutar el IDE de Compiscript
Uso: python ide/run_ide.py
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Cambiar al directorio del IDE
    ide_dir = Path(__file__).parent
    os.chdir(ide_dir)

    print(" Iniciando Compiscript IDE...")
    print(" Directorio:", ide_dir.absolute())
    print(" El IDE se abrirá en: http://localhost:8501")
    print(" Para detener: Ctrl+C")
    print("-" * 50)

    try:
        # Ejecutar Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 IDE cerrado correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al iniciar el IDE: {e}")
        return 1
    except FileNotFoundError:
        print("❌ Streamlit no está instalado. Ejecute: pip install streamlit")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
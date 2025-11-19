# Código Intermedio — Compiscript (Python)

Generador de **código intermedio (TAC con tripletos)** para el lenguaje **Compiscript** (subset de TypeScript) usando **ANTLR4** y **Python**. El objetivo es producir tripletos y asignar **direcciones de memoria** (globales, locales y temporales) para facilitar el siguiente proyecto (ensamblador/ejecutor). Incluye un **IDE mínimo** (frontend estático) para editar código, compilar vía API y visualizar tripletos y tabla de símbolos.

---

## Objetivos del proyecto

- Definir la **representación intermedia** en **tripletos**: `(op, arg1, arg2, res)`.
- Generar TAC para **expresiones** y **control de flujo** (etiquetas y saltos).
- Implementar un **modelo de memoria** con direcciones y offsets por ámbito.
- Ampliar la **tabla de símbolos** para registrar dirección, tipo, alcance y tamaño.
- Disponer de una **API** (FastAPI) y un **IDE** (HTML/JS) para probar y visualizar.
- Cubrir funcionalidades con **tests** (pytest) y ejecutar **CI** en GitHub Actions.

---

## Estructura del repositorio

```text
.
├─ README.md
├─ LICENSE
├─ Makefile
├─ requirements.txt
├─ .github/workflows/ci.yml
├─ docs/
│  ├─ lenguaje_intermedio.md
│  ├─ arquitectura.md
│  └─ uso.md
├─ grammar/
│  ├─ Compiscript.g4
│  └─ gen/                    # salida ANTLR (Python)
├─ program/
│  ├─ Driver.py
│  └─ program.cps             # ejemplos de entrada
├─ compiler/
│  ├─ ast/
│  │  └─ visitors.py          # Listener/Visitor → emite TAC
│  ├─ ir/
│  │  ├─ triplet.py           # clase Triplet
│  │  ├─ emitter.py           # emisor de tripletos y etiquetas
│  │  └─ temp_pool.py         # gestor de temporales t0, t1, ...
│  ├─ symtab/
│  │  ├─ symbols.py
│  │  └─ memory_model.py      # direcciones: global/local/temp
│  ├─ codegen/
│  │  ├─ expr_codegen.py
│  │  ├─ stmt_codegen.py
│  │  └─ func_codegen.py
│  └─ errors.py
├─ api/
│  ├─ main.py                 # FastAPI /compile
│  └─ schemas.py
├─ ide/
│  └─ static/                 # index.html, app.js, styles.css
└─ tests/
   ├─ test_expr.py
   ├─ test_control_flow.py
   ├─ test_functions.py
   ├─ test_arrays.py
   └─ test_errors.py
```

---

## Requisitos

- Python 3.11+
- ANTLR4 (runtime + tool)
- Dependencias Python (ver `requirements.txt`):
  - `antlr4-python3-runtime`
  - `fastapi` `uvicorn`
  - `pytest` `pytest-cov`
  - `rich`
  - `ruff` y/o `black` (opcional)

Instalación rápida:

```bash
python -m venv .venv
source .venv/bin/activate               # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Gramática y generación (ANTLR4)

1. Colocar la gramática en `grammar/Compiscript.g4`.
2. Generar el lexer/parser en Python:

```bash
antlr4 -Dlanguage=Python3 grammar/Compiscript.g4 -o grammar/gen
```

3. El `Visitor`/`Listener` en `compiler/ast/visitors.py` conectará con `codegen/*` para emitir tripletos y con `symtab/*` para registrar símbolos y direcciones.

---

## Representación intermedia (TAC — Tripletos)

- Forma canónica: `Triplet(op, arg1, arg2, res)`.
- **Temporales**: `t0, t1, ...` gestionados por `ir/temp_pool.py` (reciclaje).
- **Etiquetas**: `L0, L1, ...` para saltos condicionales e incondicionales.
- **Convenciones**:
  - Expresiones aritméticas/lógicas se descomponen en tripletos con temporales.
  - Comparaciones generan evaluaciones y saltos al flujo correspondiente.
  - Control de flujo (`if/else`, `while`, `for`, `break/continue`) usa etiquetas y backpatch.
  - Llamadas/retornos: prolog/epilog y paso de parámetros (básico por valor).

Ejemplo (esquemático):

```text
t0 = a + b          → (add, a, b, t0)
t1 = t0 * c         → (mul, t0, c, t1)
if t1 < 10 goto L1  → (blt, t1, 10, L1)
goto L2             → (jmp, -, -, L2)
L1: x = t1          → (mov, t1, -, x)
L2: ...
```

---

## Modelo de memoria y tabla de símbolos

- **Ámbitos**: global y pila de activación por función/bloque.
- **Direcciones**:
  - **Globales**: segmento base `G` con offsets crecientes.
  - **Locales**: segmento `L` relativo a cada activación (stack frame).
  - **Temporales**: segmento `T` por activación, reciclados por uso.
- **Símbolos**: `{ nombre, tipo, tamaño, alcance, dirección, offset, flags }`.
- **Arreglos**: dirección base + cálculo de índice (y opcionalmente bounds check).

El objetivo es que la salida de esta etapa sea apta para un ejecutor/ensamblador en la siguiente fase.

---

## API y IDE

- **API** (`api/main.py`): `POST /compile` con `{ source }` devuelve `{ triplets, symbols, errors }`.
- **IDE** (`ide/static`): `index.html` con editor (Monaco/CodeMirror), botón **Compilar**, panel de **errores**, tabla de **tripletos** y **símbolos**, y opción de exportar CSV.

Levantar API:

```bash
uvicorn api.main:app --reload
```

Servir el IDE (estático) desde cualquier servidor simple o abrir `ide/static/index.html` en el navegador y configurar la URL de la API.

---

## Ejecución rápida (playground)

En `program/` hay ejemplos (`program.cps`) y `Driver.py` para probar la gramática y el pipeline sin el IDE.

```bash
python program/Driver.py program/program.cps
o
docker run --rm -ti -v "$(pwd)/program":/program -v "$(pwd)/compiler":/compiler csp-image
```

---

## Pruebas

Ejecutar toda la suite:

```bash
pytest -q
```

Cobertura:

```bash
pytest --cov=compiler --cov-report=term-missing
```

### TAC -> MIPS
```bash
python program/compile_to_mips.py program/program2.cps program/program2_mips.asm
```

### run IDE
```bash
streamlit run ide/app.py
```
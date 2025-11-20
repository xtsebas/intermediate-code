#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROGRAM_DIR="${PROJECT_ROOT}/program"
FEATURE_DIR="${PROGRAM_DIR}/feature_tests"
OUTPUT_DIR="${FEATURE_DIR}/asm"
COMPILE_SCRIPT="${PROGRAM_DIR}/compile_to_mips.py"

if [ ! -d "$FEATURE_DIR" ]; then
  echo "Feature tests directory not found: $FEATURE_DIR" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

for src in "$FEATURE_DIR"/*.cps; do
  [ -e "$src" ] || continue
  base=$(basename "$src" .cps)
  out="$OUTPUT_DIR/${base}_mips.asm"
  echo "Compiling $src -> $out"
  python3 "$COMPILE_SCRIPT" "$src" "$out"
done

echo "Feature test assemblies available in $OUTPUT_DIR"

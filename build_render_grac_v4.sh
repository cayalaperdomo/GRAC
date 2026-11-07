#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[GRAC BUILD] Directorio: $(pwd)"
if [ ! -f "Programasgsi2.py" ] || [ ! -f "grac_parts/part_001.py" ]; then
  echo "ERROR: los archivos de GRAC deben estar descomprimidos EN LA RAIZ del repositorio." >&2
  exit 1
fi

# Conservar las dependencias preexistentes del repositorio.
if [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
elif [ -f pyproject.toml ] && command -v poetry >/dev/null 2>&1; then
  echo "[GRAC BUILD] Instalando dependencias con Poetry."
  poetry config virtualenvs.create false --local
  poetry install --only main --no-root
elif [ -f pyproject.toml ]; then
  python -m pip install .
else
  echo "ERROR: Falta requirements.txt o pyproject.toml. Conserve el original del repositorio GRAC." >&2
  exit 1
fi
if [ -f requirements-render.txt ]; then
  python -m pip install -r requirements-render.txt
fi
python -m pip install 'gunicorn>=22,<24'

# Se compila bloque a bloque, evitando un pico de ~400 MB al arrancar.
python -m compileall -q -f grac_parts
python -m py_compile Programasgsi2.py
printf '[GRAC BUILD] %s bloques compilados\n' "$(find grac_parts -maxdepth 1 -name 'part_*.py' | wc -l | tr -d ' ')"

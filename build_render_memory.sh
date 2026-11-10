#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f requirements.txt ]; then
  echo "Falta requirements.txt original. Este ZIP actualiza el repositorio existente." >&2
  exit 1
fi
python -m pip install --no-cache-dir -r requirements.txt -r requirements-render-memory.txt
python -m py_compile Programasgsi2.py gunicorn_render_memory.conf.py

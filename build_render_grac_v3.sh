#!/usr/bin/env bash
set -euo pipefail
# Configurar en Render > Settings > Build Command: bash build_render_grac_v3.sh
pip install -r requirements.txt
# CLAVE: compilar todos los bloques en BUILD, no en runtime (memoria muy restringida).
python -m compileall -q -f grac_parts Programasgsi2.py
printf 'GRAC-RAM-V3 build: archivos compilados: '
find grac_parts/__pycache__ -name '*.pyc' | wc -l

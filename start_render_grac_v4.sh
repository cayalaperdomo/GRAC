#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Perfil para instancias Render con 512 MB; solo aplica a este servicio.
export GRAC_RENDER_LOW_MEMORY="${GRAC_RENDER_LOW_MEMORY:-1}"
export GRAC_ALERTS_BACKGROUND="${GRAC_ALERTS_BACKGROUND:-0}"
export GRAC_RAM_LOG="${GRAC_RAM_LOG:-1}"
export GRAC_RAM_EVERY="${GRAC_RAM_EVERY:-10}"
export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export MALLOC_ARENA_MAX=2

# No --preload: evita duplicar compilacion/inicializacion antes del worker.
exec gunicorn \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 \
  --threads 1 \
  --worker-class sync \
  --timeout 180 \
  --graceful-timeout 25 \
  --max-requests 70 \
  --max-requests-jitter 10 \
  --access-logfile - \
  --error-logfile - \
  'Programasgsi2:app'

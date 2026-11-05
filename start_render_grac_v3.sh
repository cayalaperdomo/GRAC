#!/usr/bin/env bash
set -euo pipefail
# Configurar en Render > Settings > Start Command: bash start_render_grac_v3.sh
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export GRAC_RENDER_LOW_MEMORY=1
export GRAC_SYNC_GOVERNANCE_ON_START=0
export GRAC_ALERTS_BACKGROUND=0
export GRAC_LOW_MEMORY_CLEANUP=1
export GRAC_RAM_TRACE_STARTUP=1
export GRAC_RAM_LOG_EVERY=1
export GRAC_RAM_TRACE_REQUESTS=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_MAX_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export MALLOC_ARENA_MAX=2
export MALLOC_TRIM_THRESHOLD_=65536
export MPLBACKEND=Agg
# No compilar ni instalar dependencias durante Start Command.
if [ ! -d grac_parts ] || [ ! -f Programasgsi2.py ]; then
  echo 'GRAC-RAM-V3 ERROR: archivos del paquete incompletos.' >&2; exit 1
fi
exec gunicorn 'Programasgsi2:app' \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 --threads 1 --worker-class sync \
  --timeout 120 --graceful-timeout 30 \
  --max-requests 20 --max-requests-jitter 0 \
  --access-logfile - --error-logfile - --log-level info

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export GRAC_RENDER_LOW_MEMORY=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MALLOC_ARENA_MAX=2
export MPLBACKEND=Agg
export WEB_CONCURRENCY=1
# Evitar opciones antiguas de preload/reload o más workers.
unset GUNICORN_CMD_ARGS
exec gunicorn -c gunicorn_render_memory.conf.py --workers 1 --threads 1 --worker-class sync Programasgsi2:app

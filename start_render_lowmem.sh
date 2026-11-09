#!/usr/bin/env bash
set -euo pipefail
# These defaults only affect this service. Environment values on Render win.
export GRAC_RENDER_LOW_MEMORY="${GRAC_RENDER_LOW_MEMORY:-1}"
export GRAC_RENDER_STARTUP_GOV_SYNC="${GRAC_RENDER_STARTUP_GOV_SYNC:-0}"
export GRAC_RENDER_ALERT_SCHEDULER="${GRAC_RENDER_ALERT_SCHEDULER:-0}"
export GRAC_ALERTS_BACKGROUND="${GRAC_ALERTS_BACKGROUND:-0}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export MPLBACKEND="Agg"
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
exec gunicorn --config gunicorn_render_lowmem.py Programasgsi2:app

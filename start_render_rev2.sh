#!/usr/bin/env bash
set -euo pipefail
# Current repo must contain Programasgsi2.py, this script and gunicorn_render_rev2.py
export GRAC_RENDER_LOW_MEMORY=1
export GRAC_RENDER_STARTUP_GOV_SYNC=0
export GRAC_RENDER_ALERT_SCHEDULER=0
export GRAC_ALERTS_BACKGROUND=0
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MPLBACKEND=Agg
export MALLOC_ARENA_MAX=2
export MALLOC_TRIM_THRESHOLD_=131072
export GRAC_MEMORY_LOG_EVERY="${GRAC_MEMORY_LOG_EVERY:-1}"
export GRAC_GC_EVERY="${GRAC_GC_EVERY:-5}"
export GRAC_HIGH_MEMORY_MB="${GRAC_HIGH_MEMORY_MB:-280}"
export GRAC_RENDER_CHART_DPI="${GRAC_RENDER_CHART_DPI:-100}"
export GRAC_MAX_REQUESTS="${GRAC_MAX_REQUESTS:-25}"
export GRAC_WORKER_RECYCLE_MB="${GRAC_WORKER_RECYCLE_MB:-365}"
export GRAC_CGROUP_RECYCLE_MB="${GRAC_CGROUP_RECYCLE_MB:-455}"
export GRAC_RENDER_MAX_UPLOAD_MB="${GRAC_RENDER_MAX_UPLOAD_MB:-24}"
echo '[GRAC Render REV2] low-memory startup; gunicorn workers=1; env ready'
exec gunicorn --config gunicorn_render_rev2.py Programasgsi2:app

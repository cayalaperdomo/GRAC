#!/usr/bin/env bash
# GRAC Web - Render: single gthread worker, avoid frequent forced recycling.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export GRAC_RENDER_LOW_MEMORY="${GRAC_RENDER_LOW_MEMORY:-1}"
export WEB_CONCURRENCY=1
export PYTHONUNBUFFERED=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
# 0 disables automatic recycling for the diagnostic phase; monitor total RSS.
MAX_REQUESTS="${GRAC_RENDER_MAX_REQUESTS:-0}"
THREADS="${GRAC_RENDER_THREADS:-2}"
PORT="${PORT:-10000}"
if [[ ! "$MAX_REQUESTS" =~ ^[0-9]+$ || ! "$THREADS" =~ ^[1-9][0-9]*$ ]]; then
    echo 'ERROR: invalid GRAC_RENDER_MAX_REQUESTS or GRAC_RENDER_THREADS' >&2
    exit 1
fi
printf 'GRAC Gunicorn: workers=1 threads=%s max_requests=%s port=%s\n' "$THREADS" "$MAX_REQUESTS" "$PORT"
exec python -m gunicorn \
    --bind "0.0.0.0:$PORT" \
    --workers 1 --worker-class gthread --threads "$THREADS" \
    --timeout 180 --graceful-timeout 30 \
    --max-requests "$MAX_REQUESTS" --max-requests-jitter 0 \
    --access-logfile - --error-logfile - \
    Programasgsi2:app

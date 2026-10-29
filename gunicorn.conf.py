"""Gunicorn de bajo consumo para Arkyntech GRAC en Render."""
import os

os.environ.setdefault('GRAC_RENDER_LOW_MEMORY', '1')
os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ.setdefault('MALLOC_ARENA_MAX', '2')
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name] = os.getenv('GRAC_RENDER_BLAS_THREADS', '1')

bind = '0.0.0.0:' + os.getenv('PORT', '10000')
workers = 1
worker_class = 'gthread'
threads = max(1, min(3, int(os.getenv('GRAC_RENDER_THREADS', '1'))))
preload_app = False
max_requests = max(20, int(os.getenv('GRAC_RENDER_MAX_REQUESTS', '60')))
max_requests_jitter = 10
timeout = int(os.getenv('GRAC_RENDER_TIMEOUT', '180'))
graceful_timeout = 30
keepalive = 5
accesslog = '-'
errorlog = '-'
capture_output = True
loglevel = 'info'

_grac_count = 0
def post_request(worker, req, environ, resp):
    global _grac_count
    try:
        every = int(os.getenv('GRAC_RENDER_MEMORY_LOG_EVERY', '10'))
        if every <= 0:
            return
        _grac_count += 1
        if _grac_count % every:
            return
        with open('/proc/self/status', encoding='ascii') as f:
            rss = next((line.strip() for line in f if line.startswith('VmRSS:')), '')
        if rss:
            worker.log.info('GRAC Render RAM %s (solicitudes=%d)', rss, _grac_count)
    except (OSError, ValueError):
        pass

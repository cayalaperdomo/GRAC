"""Arkyntech GRAC / Render FREE low-memory profile -- REV2.

This is a conservative single-worker deployment. The RSS guard recycles a
worker after an expensive response, without interrupting the response itself.
It cannot prevent an OOM that happens during a single request.
"""
import os
import logging

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
threads = 1
worker_class = "sync"
preload_app = False
max_requests = max(1, int(os.getenv("GRAC_MAX_REQUESTS", "25")))
max_requests_jitter = 0
timeout = int(os.getenv("GRAC_GUNICORN_TIMEOUT", "120"))
graceful_timeout = 20
keepalive = 2
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GRAC_LOG_LEVEL", "info")
capture_output = True


def _linux_rss_mb():
    try:
        with open('/proc/self/status', encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        pass
    return None


def _cgroup_mb():
    for path in ('/sys/fs/cgroup/memory.current',
                 '/sys/fs/cgroup/memory/memory.usage_in_bytes'):
        try:
            with open(path, encoding='utf-8') as handle:
                return int(handle.read().strip()) / (1024 * 1024)
        except (OSError, ValueError):
            continue
    return None


def post_worker_init(worker):
    worker.log.warning('[GRAC REV2] worker ready pid=%d rss_mb=%s',
                       os.getpid(), _linux_rss_mb())


def post_request(worker, req, environ, resp):
    rss = _linux_rss_mb()
    cgroup = _cgroup_mb()
    rss_limit = int(os.getenv('GRAC_WORKER_RECYCLE_MB', '365'))
    cgroup_limit = int(os.getenv('GRAC_CGROUP_RECYCLE_MB', '455'))
    if rss is not None or cgroup is not None:
        worker.log.info('[GRAC REV2 memory] pid=%d rss_mb=%s cgroup_mb=%s route=%s',
                        os.getpid(), round(rss, 1) if rss is not None else '?',
                        round(cgroup, 1) if cgroup is not None else '?',
                        (getattr(req, 'path', '') or '')[:130])
    if ((rss is not None and rss >= rss_limit) or
            (cgroup is not None and cgroup >= cgroup_limit)):
        worker.log.warning('[GRAC REV2] recycling worker after request for RAM headroom')
        worker.alive = False

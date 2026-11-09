"""Gunicorn profile for GRAC on Render's 512-MB instances.

Configuration can be overridden with environment variables; runs one process
without preload to avoid multiple independent SQLite access pools.
"""
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
threads = 1
worker_class = "sync"
preload_app = False
max_requests = int(os.getenv("GRAC_MAX_REQUESTS", "100"))
max_requests_jitter = 15
timeout = int(os.getenv("GRAC_GUNICORN_TIMEOUT", "180"))
graceful_timeout = 30
keepalive = 2
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GRAC_LOG_LEVEL", "info")
capture_output = True

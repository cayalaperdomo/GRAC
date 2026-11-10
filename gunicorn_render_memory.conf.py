import os
bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
threads = 1
worker_class = "sync"
preload_app = False
reload = False
# Background jobs are in-process: do not cancel them by request-count recycling.
max_requests = 0
timeout = 180
graceful_timeout = 180
keepalive = 2
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

"""Gunicorn settings for running the whole app in one small container."""

import logging
import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"

# Exactly one worker, deliberately. Task state lives in process memory
# (tasks.py), so a task queued by one worker would be invisible to another and
# the browser would poll a PENDING id forever. One process is also the whole
# point: threads are enough because every task just waits on a slow remote site.
workers = 1
worker_class = "gthread"
threads = int(os.getenv("THREADS", "8"))

# Import the app in the master and let the worker inherit it copy-on-write,
# rather than paying for a second full import. tasks.py creates its thread
# pool lazily and resets at fork, so it is safe to load before forking.
preload_app = True

# Sidestep the tmpfs-less container case for the heartbeat file.
worker_tmp_dir = "/dev/shm" if os.path.isdir("/dev/shm") else None

# Long enough for a slow scrape to finish; the real bound on task runtime is the
# per-request HTTP timeout in crawler/core.py.
timeout = int(os.getenv("TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'

# The frontend polls /tasks/<id> once a second per open tab. Logging every one
# buries anything useful and is pointless disk chatter on a NAS, so drop them
# unless someone asks for them.
LOG_POLLS = os.getenv("LOG_POLLS", "False") == "True"


class _DropPolls(logging.Filter):
    def filter(self, record):
        return "/tasks/" not in record.getMessage()


def post_fork(server, worker):
    if not LOG_POLLS:
        logging.getLogger("gunicorn.access").addFilter(_DropPolls())


def on_starting(server):
    server.log.info(
        "epos starting: 1 worker, %s threads, %s cores visible",
        threads,
        multiprocessing.cpu_count(),
    )


def worker_exit(server, worker):
    import tasks

    tasks.shutdown()

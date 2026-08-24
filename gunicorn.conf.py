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

# gunicorn 26 opens a control socket under $HOME by default. This image has no
# writable home (and a read-only root filesystem), so that only produces an
# error on every boot. Nothing here uses the control interface.
control_socket_disable = True

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
    # A command line --workers overrides the value set above, and more than one
    # worker silently breaks the UI: task state lives in process memory, so a
    # poll that lands on the other worker reports PENDING for a task that has
    # already finished and the spinner never stops. Clamp it rather than let
    # that reach anyone, and say so loudly enough to get the flag removed.
    if server.cfg.workers != 1:
        server.log.warning(
            "ignoring --workers %s and running 1 worker: task state is "
            "in-process, so extra workers strand polls at PENDING. Remove the "
            "flag and raise THREADS instead.",
            server.cfg.workers,
        )
        server.cfg.set("workers", 1)
        # Arbiter.setup() has already copied cfg.workers into num_workers by the
        # time this hook runs, so the live value has to be corrected too.
        server.num_workers = 1
    server.log.info(
        "epos starting: 1 worker, %s threads, %s cores visible",
        server.cfg.threads,
        multiprocessing.cpu_count(),
    )


def worker_exit(server, worker):
    import tasks

    tasks.shutdown()

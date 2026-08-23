"""In-process task queue.

The API is job based: an endpoint hands back a task id and the browser polls
/tasks/<id> until it is done. That used to mean Celery + Redis + a separate
worker container. Every task here is pure network I/O against
epos.bihar.gov.in, so a small thread pool inside the web process does the same
work with one interpreter, no broker and no second container.

Only the surface the app actually used is reproduced: @task(name=...) giving a
callable that also has .delay() and .run(), plus status lookup by id.

Because results live in process memory, this assumes a single web worker (see
gunicorn.conf.py) -- a task submitted by one process is not visible to another.
"""

import functools
import logging
import os
import threading
import traceback
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from uuid import uuid4

log = logging.getLogger(__name__)

PENDING = "PENDING"
STARTED = "STARTED"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"

# Threads, not processes: the work is all waiting on a slow government site,
# so the GIL is never the bottleneck and we pay for one interpreter only.
MAX_WORKERS = int(os.getenv("TASK_WORKERS", "4"))
# A finished result only has to survive until the browser polls for it.
RESULT_TTL = int(os.getenv("TASK_RESULT_TTL", "600"))
MAX_RESULTS = int(os.getenv("TASK_MAX_RESULTS", "64"))
# Backstop so a hammered box cannot queue work faster than it drains.
MAX_QUEUED = int(os.getenv("TASK_MAX_QUEUED", str(MAX_WORKERS * 8)))


class TaskQueueFull(Exception):
    """Raised when too many tasks are already waiting to run."""


class _Entry:
    __slots__ = ("id", "name", "status", "result", "traceback", "ts", "key")

    def __init__(self, task_id, name, key):
        self.id = task_id
        self.name = name
        self.key = key
        self.status = PENDING
        self.result = None
        self.traceback = None
        self.ts = monotonic()

    def done(self):
        return self.status in (SUCCESS, FAILURE)


class _Registry:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries = OrderedDict()  # task id -> _Entry, oldest first
        self._inflight = {}  # dedupe key -> task id
        self._pool = None

    def _get_pool(self):
        # Created on first use so it survives gunicorn's preload fork: threads
        # are not inherited by the child, only already-spawned ones are lost.
        if self._pool is None:
            self._pool = ThreadPoolExecutor(
                max_workers=MAX_WORKERS, thread_name_prefix="task"
            )
        return self._pool

    def reset_after_fork(self):
        self._lock = threading.Lock()
        self._entries.clear()
        self._inflight.clear()
        self._pool = None

    def _prune(self):
        """Drop finished results that are old or over the cap. Caller holds the lock."""
        now = monotonic()
        for task_id, entry in list(self._entries.items()):
            if entry.done() and now - entry.ts > RESULT_TTL:
                del self._entries[task_id]
        overflow = len(self._entries) - MAX_RESULTS
        for task_id, entry in list(self._entries.items()):
            if overflow <= 0:
                break
            if entry.done():  # never evict something still running
                del self._entries[task_id]
                overflow -= 1

    def submit(self, task, args, kwargs):
        key = (task.name, args, tuple(sorted(kwargs.items())))
        with self._lock:
            self._prune()
            running = self._inflight.get(key)
            if running is not None:
                # Same call already in flight (impatient refreshes, two users
                # asking the same thing): share the answer instead of scraping
                # the same page twice.
                log.info("reusing in-flight task %s for %s", running, task.name)
                return running
            if len(self._inflight) >= MAX_QUEUED:
                raise TaskQueueFull(f"{len(self._inflight)} tasks already queued")
            entry = _Entry(uuid4().hex, task.name, key)
            self._entries[entry.id] = entry
            self._inflight[key] = entry.id
            pool = self._get_pool()
        pool.submit(self._run, entry, task, args, kwargs)
        return entry.id

    def _run(self, entry, task, args, kwargs):
        entry.status = STARTED
        try:
            result = task.run(*args, **kwargs)
        except Exception as ex:
            log.exception("task %s (%s) failed", entry.name, entry.id)
            entry.result = str(ex)
            entry.traceback = traceback.format_exc()
            entry.status = FAILURE
        else:
            entry.result = result
            entry.status = SUCCESS
        finally:
            entry.ts = monotonic()
            with self._lock:
                if self._inflight.get(entry.key) == entry.id:
                    del self._inflight[entry.key]

    def status(self, task_id):
        with self._lock:
            entry = self._entries.get(task_id)
        if entry is None:
            # Unknown ids read as PENDING so a poller that outlived a restart
            # gives up on its own timeout instead of erroring.
            return {"id": task_id, "status": PENDING, "result": None}
        if entry.status == FAILURE:
            result = {"error": entry.result, "traceback": entry.traceback}
        else:
            result = entry.result
        return {"id": task_id, "status": entry.status, "result": result}

    def shutdown(self):
        pool, self._pool = self._pool, None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)


_registry = _Registry()

if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_registry.reset_after_fork)


class Task:
    """A plain function that can also be run in the background via .delay()."""

    def __init__(self, fn, name):
        self.fn = fn
        self.name = name
        functools.update_wrapper(self, fn)

    def run(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    # Calling a task directly still just calls the function, which is what the
    # crawlers do when one task reuses another.
    __call__ = run

    def delay(self, *args, **kwargs):
        return _registry.submit(self, args, kwargs)


def task(name=None):
    def decorate(fn):
        return Task(fn, name or fn.__name__)

    return decorate


def get_status(task_id):
    return _registry.status(task_id)


def shutdown():
    _registry.shutdown()

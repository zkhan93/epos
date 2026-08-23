import logging
import os
import threading

from diskcache import Cache

# Despite the old name this was always 12 hours (60 * 24 * 30 seconds), and the
# frontend depends on data going stale that quickly, so the value stays put.
DEFAULT_CACHE_TTL = int(os.getenv("CACHE_TTL", str(60 * 24 * 30)))
WEEK_IN_SECONDS = DEFAULT_CACHE_TTL  # kept for callers that still use it

_cache = None
_cache_lock = threading.Lock()


def get_cache():
    """One shared, thread safe disk cache for the whole process.

    diskcache keeps a per-thread sqlite connection internally, so a single
    Cache object is both correct and much cheaper than opening a new one on
    every task the way this used to.
    """
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = Cache(
                    directory=os.getenv("CACHE_DIR", "/tmp/cache"),
                    # Bound the cache so it cannot fill a NAS volume.
                    size_limit=int(os.getenv("CACHE_SIZE_LIMIT", str(128 * 1024**2))),
                    statistics=0,
                )
                if os.getenv("CLEAR_CACHE", "False") == "True":
                    logging.info("Clearing Cache...")
                    _cache.clear()
                    logging.info("Cache cleared")
    return _cache

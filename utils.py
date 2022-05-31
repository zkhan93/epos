import logging
import os
from diskcache import Cache

WEEK_IN_SECONDS = 60 * 24 * 30


def get_cache():
    clear_cache = os.getenv("CLEAR_CACHE", False)
    cache = Cache(directory=os.getenv("CACHE_DIR", "/tmp/cache"))
    if clear_cache:
        logging.info("Clearing Cache...")
        cache.clear()
        logging.info("Cache cleared")
    return cache

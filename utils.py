import os
from diskcache import Cache

WEEK_IN_SECONDS = 60 * 24 * 30


def get_cache():
    return Cache(directory=os.getenv("CACHE_DIR", "/tmp/cache"))

import logging
import os
from diskcache import Cache
from celery import Celery

logging.basicConfig(level=logging.INFO)

WEEK_IN_SECONDS = 60 * 24 * 30


def get_cache():
    clear_cache = os.getenv("CLEAR_CACHE", "False") == "True"
    cache = Cache(directory=os.getenv("CACHE_DIR", "/tmp/cache"))
    if clear_cache:
        logging.info("Clearing Cache...")
        cache.clear()
        logging.info("Cache cleared")
    return cache


def init_celery(celery, app):
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

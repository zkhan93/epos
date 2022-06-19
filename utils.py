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


def create_celery():
    celery = Celery("celery app")
    config_from_env = {
        k.split("CELERY_", 1)[1].lower(): v
        if v not in ("True", "False")
        else v == "True"
        for k, v in os.environ.items()
        if k.startswith("CELERY_")
    }
    config = {
        "broker_url": os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
        "task_time_limit": int(os.getenv("TASK_TIME_LIMIT", "6")),
        "task_ignore_result": False,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
    }
    config.update(config_from_env)
    celery.conf.update(config)
    logging.info(f"Celery configured with {config}")

    return celery


def init_celery(celery, app):
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

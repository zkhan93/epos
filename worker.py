import os
import logging
from celery import Celery

logger = logging.getLogger("worker")
celery = Celery(__name__)
config_from_env = {
    k.split("CELERY_", 1)[1].lower(): v if v not in ("True", "False") else v == "True"
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
logger.info(f"Celery configured with {config}")

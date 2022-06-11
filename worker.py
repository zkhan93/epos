import os
import logging
from celery import Celery

logger = logging.getLogger("worker")
celery = Celery(__name__)
values = {
    "broker_url": os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    "task_time_limit": int(os.getenv("TASK_TIME_LIMIT", "6")),
}
celery.conf.update(values)
logger.info(str(values))

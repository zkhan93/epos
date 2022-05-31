import os

from celery import Celery

celery = Celery(__name__)
celery.conf.update(
    {
        "broker_url": os.getenv("CELERY_BROKER_URL", "redis://redis:6379"),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379"),
    }
)

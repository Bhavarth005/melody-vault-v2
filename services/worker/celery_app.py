from celery import Celery

REDIS_URL = "redis://redis:6379/0"

celery_app = Celery(
    "melody_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

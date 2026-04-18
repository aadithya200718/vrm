from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from backend.core.config import get_settings


settings = get_settings()
TASK_MODULES = (
    "backend.tasks.verification",
    "backend.tasks.healthcare",
    "backend.tasks.ml",
    "backend.tasks.notifications",
    "backend.tasks.scheduler",
)

celery_app = Celery(
    "vendor_onboarding",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=list(TASK_MODULES),
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    imports=TASK_MODULES,
    result_serializer="json",
    task_always_eager=settings.celery_task_always_eager,
    task_default_queue="verification_queue",
    task_default_exchange="vendor_onboarding",
    task_default_exchange_type="direct",
    task_default_routing_key="verification_queue",
    task_routes={
        "backend.tasks.verification.*": {"queue": "verification_queue"},
        "backend.tasks.healthcare.*": {"queue": "hipaa_check_queue"},
        "backend.tasks.notifications.*": {"queue": "notification_queue"},
        "backend.tasks.ml.*": {"queue": "rl_training_queue"},
        "backend.tasks.scheduler.*": {"queue": "scheduler_queue"},
    },
    task_send_sent_event=True,
    task_serializer="json",
    task_soft_time_limit=240,
    task_time_limit=300,
    task_track_started=True,
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    worker_send_task_events=True,
    beat_schedule={
        "check-baa-expiry-daily": {
            "task": "backend.tasks.scheduler.check_baa_expiry",
            "schedule": crontab(hour=2, minute=0),
        },
        "schedule-hipaa-reassessments-daily": {
            "task": "backend.tasks.scheduler.schedule_hipaa_reassessments",
            "schedule": crontab(hour=3, minute=0),
        },
        "cleanup-expired-tokens-hourly": {
            "task": "backend.tasks.scheduler.cleanup_expired_tokens",
            "schedule": crontab(minute=0),
        },
    },
)
celery_app.autodiscover_tasks(["backend.tasks"])

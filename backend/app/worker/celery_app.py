"""Celery приложение и график на автоматичните задачи.

Данните се обновяват сами; ръчното пускане на скриптове остава само за
първоначално зареждане и за отстраняване на проблеми.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "lihvomer",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Sofia",
    enable_utc=True,
    task_time_limit=1800,
    task_soft_time_limit=1500,
    worker_max_tasks_per_child=50,
    result_expires=60 * 60 * 24,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    # ЕЦБ публикува дневните редове около 16:00 CET, Bundesbank малко по-рано.
    # Пускаме сутрин за нощните ревизии и вечер за днешните стойности.
    "ingest-macro-morning": {
        "task": "app.worker.tasks.ingest_macro",
        "schedule": crontab(hour=7, minute=15),
    },
    "ingest-macro-evening": {
        "task": "app.worker.tasks.ingest_macro",
        "schedule": crontab(hour=18, minute=30),
    },
    # Новините се обновяват често, но фийдовете са малки.
    "ingest-news": {
        "task": "app.worker.tasks.ingest_news",
        "schedule": crontab(minute=5, hour="*/3"),
    },
    # Преоценка на моделите след вечерното зареждане.
    "refresh-analytics": {
        "task": "app.worker.tasks.refresh_analytics",
        "schedule": crontab(hour=19, minute=0),
    },
    # Известията се оценяват веднъж дневно, след като данните са обновени.
    # По-често би било спам — пазарните лихви се движат бавно.
    "dispatch-notifications": {
        "task": "app.worker.tasks.dispatch_notifications",
        "schedule": crontab(hour=19, minute=30),
    },
    # Веднъж седмично проверяваме дали източниците не са преместили
    # страниците си. Линковете за показване не се ползват от кода, затова
    # иначе биха гнили незабелязано.
    "check-external-links": {
        "task": "app.worker.tasks.check_external_links",
        "schedule": crontab(hour=4, minute=15, day_of_week=1),
    },
    # Чистене на историята, за да не расте безкрайно.
    "prune-job-history": {
        "task": "app.worker.tasks.prune_job_history",
        "schedule": crontab(hour=3, minute=30, day_of_week=1),
    },
}

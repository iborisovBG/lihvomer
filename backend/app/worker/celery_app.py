"""Celery приложение и график на автоматичните задачи.

Данните се обновяват сами; ръчното пускане на скриптове остава само за
първоначално зареждане и за отстраняване на проблеми.
"""

from __future__ import annotations

from dataclasses import dataclass

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

@dataclass(frozen=True)
class ScheduledJob:
    """Една задача от графика заедно с описанието ѝ на български.

    Описанието стои до самия crontab нарочно: приложението го показва в
    раздел „Автоматизация". Докато двете бяха на различни места, графикът
    можеше да се смени, без текстът да го последва — и сайтът щеше да
    твърди пред потребителя нещо, което не се случва.
    """

    key: str
    task: str
    schedule: crontab
    description_bg: str

    @property
    def short_name(self) -> str:
        """Името, под което JobRun записва задачата."""
        return self.task.rsplit(".", 1)[-1]


JOBS: tuple[ScheduledJob, ...] = (
    # ЕЦБ публикува дневните редове около 16:00 CET, Bundesbank малко по-рано,
    # а Евростат пуска месечните серии по свой календар. Вместо да гадаем кога
    # точно, обхождаме на всеки 3 часа. Зареждането е инкрементално — за всеки
    # ред се тегли само липсващото от последното наблюдение нататък, — така че
    # едно пускане са десетина секунди и по една заявка на ред.
    ScheduledJob(
        key="ingest-macro",
        task="app.worker.tasks.ingest_macro",
        schedule=crontab(minute=15, hour="*/3"),
        description_bg="на всеки 3 часа (00:15, 03:15, … 21:15)",
    ),
    # Новините се обновяват често, но фийдовете са малки. Пускат се 10 минути
    # преди макроданните, за да не се борят за същата минута.
    ScheduledJob(
        key="ingest-news",
        task="app.worker.tasks.ingest_news",
        schedule=crontab(minute=5, hour="*/3"),
        description_bg="на всеки 3 часа (00:05, 03:05, … 21:05)",
    ),
    # Моделите се преоценяват веднага щом зареждането донесе наблюдение с
    # по-нова дата — ingest_macro сам пуска задачата. Вечерното пускане е
    # застраховка: скорът зависи и от настроението в новините, което се движи
    # и в дните, когато нито един макроред не е мръднал.
    ScheduledJob(
        key="refresh-analytics",
        task="app.worker.tasks.refresh_analytics",
        schedule=crontab(hour=19, minute=0),
        description_bg="след всяко ново наблюдение и всеки ден в 19:00",
    ),
    # Известията се оценяват веднъж дневно, след като данните са обновени.
    # По-често би било спам — пазарните лихви се движат бавно.
    ScheduledJob(
        key="dispatch-notifications",
        task="app.worker.tasks.dispatch_notifications",
        schedule=crontab(hour=19, minute=30),
        description_bg="всеки ден в 19:30",
    ),
    # Веднъж седмично проверяваме дали източниците не са преместили
    # страниците си. Линковете за показване не се ползват от кода, затова
    # иначе биха гнили незабелязано.
    ScheduledJob(
        key="check-external-links",
        task="app.worker.tasks.check_external_links",
        schedule=crontab(hour=4, minute=15, day_of_week=1),
        description_bg="всеки понеделник в 04:15",
    ),
    # Чистене на историята, за да не расте безкрайно.
    ScheduledJob(
        key="prune-job-history",
        task="app.worker.tasks.prune_job_history",
        schedule=crontab(hour=3, minute=30, day_of_week=1),
        description_bg="всеки понеделник в 03:30",
    ),
)

celery_app.conf.beat_schedule = {
    job.key: {"task": job.task, "schedule": job.schedule} for job in JOBS
}

# Това показва приложението в раздел „Автоматизация".
SCHEDULE_BG: dict[str, str] = {job.short_name: job.description_bg for job in JOBS}

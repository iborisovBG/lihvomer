from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import JobRun, JobStatus
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

JOB_HISTORY_DAYS = 60


@contextmanager
def _tracked(job_name: str):
    """Записва началото, края и изхода на всяка задача."""
    with SessionLocal() as db:
        run = JobRun(job_name=job_name, status=JobStatus.RUNNING, detail={})
        db.add(run)
        db.commit()
        db.refresh(run)
        started = datetime.now(timezone.utc)
        outcome: dict = {"ok": 0, "failed": 0, "detail": {}}

        try:
            yield outcome
            run.status = (
                JobStatus.SUCCESS if outcome["failed"] == 0 else JobStatus.PARTIAL
            )
        except Exception as exc:
            logger.exception("Задачата %s пропадна", job_name)
            run.status = JobStatus.FAILED
            outcome["detail"]["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            run.finished_at = datetime.now(timezone.utc)
            run.duration_seconds = round(
                (run.finished_at - started).total_seconds(), 3
            )
            run.items_ok = outcome["ok"]
            run.items_failed = outcome["failed"]
            run.detail = outcome["detail"]
            db.commit()


def _with_session(work: Callable[[Session, dict], None], job_name: str) -> dict:
    with _tracked(job_name) as outcome:
        with SessionLocal() as db:
            work(db, outcome)
    return outcome


@celery_app.task(name="app.worker.tasks.ingest_macro")
def ingest_macro() -> dict:
    """Тегли всички макроикономически редове от публичните API-та."""
    from app.ingestion.runner import ingest_all
    from app.services.analytics_cache import invalidate

    def work(db: Session, outcome: dict) -> None:
        results = ingest_all(db)
        outcome["ok"] = sum(1 for r in results if r.ok)
        outcome["failed"] = sum(1 for r in results if not r.ok)
        outcome["detail"] = {
            "series": {
                r.code: (
                    {"latest": str(r.latest_date), "value": r.latest_value}
                    if r.ok
                    else {"error": r.error}
                )
                for r in results
            }
        }
        invalidate()

    return _with_session(work, "ingest_macro")


@celery_app.task(name="app.worker.tasks.ingest_news")
def ingest_news() -> dict:
    """Тегли, превежда и оценява новините."""
    from app.news.ingest import ingest_all_news
    from app.services.analytics_cache import invalidate

    def work(db: Session, outcome: dict) -> None:
        results = ingest_all_news(db)
        outcome["ok"] = sum(1 for r in results if r.error is None)
        outcome["failed"] = sum(1 for r in results if r.error is not None)
        outcome["detail"] = {
            "feeds": {
                r.source_code: (
                    {"seen": r.seen, "kept": r.kept, "written": r.written}
                    if r.error is None
                    else {"error": r.error}
                )
                for r in results
            }
        }
        invalidate()

    return _with_session(work, "ingest_news")


@celery_app.task(name="app.worker.tasks.refresh_analytics")
def refresh_analytics() -> dict:
    """Преоценява моделите и записва нова прогноза и нов скор."""
    from app.analytics.forecast import (
        InsufficientData,
        fit_pass_through_model,
        persist_forecast,
    )
    from app.analytics.score import ScoreUnavailable, compute_score, persist_score
    from app.ingestion import registry
    from app.news.ingest import aggregate_sentiment
    from app.services.analytics_cache import invalidate

    targets = (
        registry.BG_MORTGAGE_EUR,
        registry.EURIBOR_3M,
        registry.EURIBOR_6M,
        registry.EURIBOR_12M,
    )

    def work(db: Session, outcome: dict) -> None:
        detail: dict = {}
        mortgage_result = None

        for code in targets:
            try:
                result = fit_pass_through_model(db, target_code=code)
            except InsufficientData as exc:
                outcome["failed"] += 1
                detail[code] = {"error": str(exc)}
                continue

            persist_forecast(db, result)
            outcome["ok"] += 1
            detail[code] = {
                "r_squared": result.r_squared,
                "lag_days": result.best_lag_days,
            }
            if code == registry.BG_MORTGAGE_EUR:
                mortgage_result = result

        if mortgage_result is not None:
            try:
                score = compute_score(
                    db, mortgage_result, aggregate_sentiment(db)
                )
                persist_score(db, score)
                detail["score"] = {
                    "value": score.score,
                    "signal": score.signal.value,
                }
                outcome["ok"] += 1
            except ScoreUnavailable as exc:
                outcome["failed"] += 1
                detail["score"] = {"error": str(exc)}

        outcome["detail"] = detail
        invalidate()

    return _with_session(work, "refresh_analytics")


@celery_app.task(name="app.worker.tasks.prune_job_history")
def prune_job_history() -> dict:
    def work(db: Session, outcome: dict) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=JOB_HISTORY_DAYS)
        removed = db.execute(
            delete(JobRun).where(JobRun.started_at < cutoff)
        ).rowcount
        db.commit()
        outcome["ok"] = removed or 0
        outcome["detail"] = {"removed": removed, "older_than_days": JOB_HISTORY_DAYS}

    return _with_session(work, "prune_job_history")


@celery_app.task(name="app.worker.tasks.refresh_everything")
def refresh_everything() -> dict:
    """Пълно обновяване — ползва се при първоначално пускане."""
    ingest_macro()
    ingest_news()
    return refresh_analytics()


@celery_app.task(name="app.worker.tasks.dispatch_notifications")
def dispatch_notifications() -> dict:
    """Оценява кредитите на всички потребители и изпраща известия."""
    from app.notifications.dispatcher import dispatch_all

    def work(db: Session, outcome: dict) -> None:
        totals = dispatch_all(db)
        outcome["ok"] = totals["created"]
        outcome["failed"] = totals["email_failed"]
        outcome["detail"] = totals

    return _with_session(work, "dispatch_notifications")


@celery_app.task(name="app.worker.tasks.check_external_links")
def check_external_links() -> dict:
    """Проверява дали външните адреси, които показваме, още работят."""
    from app.services.link_check import check_all

    def work(db: Session, outcome: dict) -> None:
        results = check_all()
        broken = [r for r in results if not r.ok]
        outcome["ok"] = len(results) - len(broken)
        outcome["failed"] = len(broken)
        outcome["detail"] = {
            "total": len(results),
            "broken": [
                {"label": r.label, "url": r.url, "error": r.error} for r in broken
            ],
        }

    return _with_session(work, "check_external_links")

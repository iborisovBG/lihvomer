from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ingestion.http import UpstreamError
from app.ingestion.registry import SERIES, BY_CODE, SeriesDef
from app.ingestion.sources import fetch_series
from app.models import Frequency, MacroObservation, MacroSeries

logger = logging.getLogger(__name__)

HISTORY_START = date(2014, 1, 1)
# Данните се ревизират след първа публикация, затова презасичаме назад.
DAILY_REFRESH_WINDOW = timedelta(days=45)


@dataclass
class IngestResult:
    code: str
    fetched: int
    written: int
    latest_date: date | None
    latest_value: float | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def sync_series_registry(db: Session) -> None:
    """Привежда таблицата macro_series в съответствие с кода."""
    for definition in SERIES:
        row = db.scalar(
            select(MacroSeries).where(MacroSeries.code == definition.code)
        )
        if row is None:
            row = MacroSeries(code=definition.code)
            db.add(row)
        row.name_bg = definition.name_bg
        row.plain_bg = definition.plain_bg
        row.source = definition.source
        row.source_ref = definition.source_ref
        row.frequency = definition.frequency
        row.unit = definition.unit
    db.commit()


def _incremental_start(db: Session, series_row: MacroSeries) -> date | None:
    latest = db.scalar(
        select(func.max(MacroObservation.obs_date)).where(
            MacroObservation.series_id == series_row.id
        )
    )
    if latest is None:
        return HISTORY_START
    if series_row.frequency is Frequency.DAILY:
        return latest - DAILY_REFRESH_WINDOW
    # Месечните и годишните редове са малки — теглим ги изцяло, за да
    # поемем и ревизиите на вече публикувани периоди.
    return HISTORY_START


def ingest_one(db: Session, definition: SeriesDef) -> IngestResult:
    series_row = db.scalar(
        select(MacroSeries).where(MacroSeries.code == definition.code)
    )
    if series_row is None:
        sync_series_registry(db)
        series_row = db.scalar(
            select(MacroSeries).where(MacroSeries.code == definition.code)
        )
        if series_row is None:
            return IngestResult(definition.code, 0, 0, None, None, "Липсва в регистъра.")

    start = _incremental_start(db, series_row)

    try:
        observations = fetch_series(definition, start)
    except UpstreamError as exc:
        logger.warning("Ingestion пропадна за %s: %s", definition.code, exc)
        return IngestResult(definition.code, 0, 0, None, None, str(exc))
    except Exception as exc:  # мрежов/парсващ проблем не бива да спира останалите
        logger.exception("Неочаквана грешка при %s", definition.code)
        return IngestResult(
            definition.code, 0, 0, None, None, f"{type(exc).__name__}: {exc}"
        )

    if not observations:
        return IngestResult(
            definition.code, 0, 0, None, None, "Източникът върна нула наблюдения."
        )

    payload = [
        {"series_id": series_row.id, "obs_date": obs_date, "value": value}
        for obs_date, value in observations
    ]

    statement = insert(MacroObservation).values(payload)
    statement = statement.on_conflict_do_update(
        constraint="uq_series_obs_date",
        set_={"value": statement.excluded.value},
    )
    db.execute(statement)

    series_row.last_ingested_at = datetime.now(timezone.utc)
    db.commit()

    latest_date, latest_value = observations[-1]
    return IngestResult(
        code=definition.code,
        fetched=len(observations),
        written=len(payload),
        latest_date=latest_date,
        latest_value=latest_value,
    )


def ingest_all(db: Session, codes: list[str] | None = None) -> list[IngestResult]:
    sync_series_registry(db)
    targets = (
        [BY_CODE[c] for c in codes if c in BY_CODE] if codes else list(SERIES)
    )
    return [ingest_one(db, definition) for definition in targets]

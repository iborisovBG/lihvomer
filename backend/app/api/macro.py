from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.analytics.forecast import InsufficientData
from app.analytics.score import ScoreUnavailable, compute_score
from app.analytics.timeseries import load_series
from app.deps import DbSession
from app.ingestion import registry
from app.models import MacroObservation, MacroSeries
from app.schemas import LiveDashboard, MacroIndicator, ScoreOut, SeriesPoint
from app.services.analytics_cache import get_or_compute
from app.news.ingest import aggregate_sentiment
from app.services.projections import forecast_for

router = APIRouter(prefix="/api/v1/macro", tags=["macro"])

DASHBOARD_CODES = (
    registry.DE10Y_BUND,
    registry.EURIBOR_3M,
    registry.EURIBOR_6M,
    registry.EURIBOR_12M,
    registry.ECB_DFR,
    registry.BG_MORTGAGE_EUR,
    registry.BG_CONSUMER_EUR,
    registry.HICP_BG,
    registry.HICP_EU,
    registry.BG_10Y_GOVT_EUR,
    registry.BG_HOUSE_PRICES,
    registry.BG_DEPOSIT_TERM,
    registry.BG_DEPOSIT_OVERNIGHT,
    registry.BG_GOV_DEBT,
    registry.BG_GOV_BALANCE,
    registry.US_10Y,
)


SPARK_POINTS = 24


def _indicator(db, series: MacroSeries) -> MacroIndicator:
    rows = db.execute(
        select(MacroObservation.obs_date, MacroObservation.value)
        .where(MacroObservation.series_id == series.id)
        .order_by(MacroObservation.obs_date.desc())
        .limit(SPARK_POINTS)
    ).all()

    latest = rows[0] if rows else None
    previous = rows[1] if len(rows) > 1 else None

    latest_value = float(latest[1]) if latest else None
    previous_value = float(previous[1]) if previous else None

    return MacroIndicator(
        code=series.code,
        name_bg=series.name_bg,
        plain_bg=series.plain_bg,
        unit=series.unit.value,
        frequency=series.frequency.value,
        latest_date=latest[0] if latest else None,
        latest_value=latest_value,
        previous_value=previous_value,
        change=(
            round(latest_value - previous_value, 4)
            if latest_value is not None and previous_value is not None
            else None
        ),
        source=series.source.value,
        source_ref=series.source_ref,
        last_ingested_at=series.last_ingested_at,
        # Обръщаме реда: заявката е низходяща, а графиката върви напред.
        spark=[float(value) for _, value in reversed(rows)],
    )


@router.get("/live-dashboard", response_model=LiveDashboard)
def live_dashboard(db: DbSession) -> LiveDashboard:
    # Показваме всички заредени редове; групирането става в интерфейса.
    series_rows = db.scalars(select(MacroSeries).order_by(MacroSeries.code)).all()
    by_code = {row.code: row for row in series_rows}

    if not by_code:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Все още няма заредени макроданни. "
                "Пуснете `python -m scripts.ingest`."
            ),
        )

    indicators = [_indicator(db, row) for row in series_rows]

    mortgage = load_series(db, registry.BG_MORTGAGE_EUR)
    inflation = load_series(db, registry.HICP_BG)
    real_rate = (
        round(float(mortgage.iloc[-1]) - float(inflation.iloc[-1]), 3)
        if not mortgage.empty and not inflation.empty
        else None
    )

    score_out: ScoreOut | None = None
    try:
        forecast = forecast_for(db, registry.BG_MORTGAGE_EUR)
        sentiment = get_or_compute("news:sentiment", lambda: aggregate_sentiment(db))
        score = get_or_compute(
            "score:mortgage", lambda: compute_score(db, forecast, sentiment)
        )
        score_out = ScoreOut(
            score=score.score,
            signal=score.signal,
            signal_label_bg=score.signal_label_bg,
            headline_bg=score.headline_bg,
            real_rate=score.real_rate,
            bund_momentum_60d=score.bund_momentum_60d,
            sentiment_score=score.sentiment_score,
            components=score.components,
            computed_at=score.computed_at,
        )
    except (InsufficientData, ScoreUnavailable):
        score_out = None

    return LiveDashboard(
        generated_at=datetime.now(timezone.utc),
        indicators=indicators,
        real_mortgage_rate_pct=real_rate,
        score=score_out,
    )


@router.get("/series/{code}", response_model=list[SeriesPoint])
def series_history(
    code: str,
    db: DbSession,
    limit: int = Query(default=2000, ge=1, le=20000),
) -> list[SeriesPoint]:
    if code not in registry.BY_CODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Няма ред с код {code}.",
        )

    series = load_series(db, code)
    if series.empty:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Редът {code} все още не е зареден.",
        )

    trimmed = series.iloc[-limit:]
    return [
        SeriesPoint(date=timestamp.date(), value=float(value))
        for timestamp, value in trimmed.items()
    ]

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.analytics.forecast import InsufficientData, explain_bg
from app.analytics.timeseries import load_series, to_daily
from app.deps import DbSession
from app.ingestion import registry
from app.schemas import ForecastOut, ForecastPointOut, SeriesPoint
from app.services.projections import forecast_for

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])

# Редовете, за които моделът е смислен: цел с достатъчна история и драйвер,
# чието влияние е статистически значимо.
FORECASTABLE = {
    registry.BG_MORTGAGE_EUR,
    registry.EURIBOR_3M,
    registry.EURIBOR_6M,
    registry.EURIBOR_12M,
}

HISTORY_POINTS = 120


@router.get("/mortgage-rates", response_model=ForecastOut)
def mortgage_rates(
    db: DbSession,
    target: str = Query(default=registry.BG_MORTGAGE_EUR),
) -> ForecastOut:
    if target not in FORECASTABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"За {target} не се публикува прогноза. "
                f"Достъпни редове: {', '.join(sorted(FORECASTABLE))}."
            ),
        )

    try:
        result = forecast_for(db, target)
    except InsufficientData as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    history = load_series(db, target).iloc[-HISTORY_POINTS:]
    driver = (
        to_daily(load_series(db, result.driver_code))
        .resample("MS")
        .mean()
        .iloc[-HISTORY_POINTS:]
    )

    return ForecastOut(
        target_series_code=result.target_code,
        driver_series_code=result.driver_code,
        best_lag_days=result.best_lag_days,
        n_obs=result.n_obs,
        r_squared=result.r_squared,
        adj_r_squared=result.adj_r_squared,
        diagnostics=result.diagnostics,
        latest_actual_date=result.latest_actual_date,
        latest_actual_value=round(result.latest_actual_value, 4),
        points=[
            ForecastPointOut(
                horizon_days=h.horizon_days,
                target_date=h.target_date,
                predicted_value=h.predicted_value,
                ci_lower=h.ci_lower,
                ci_upper=h.ci_upper,
            )
            for h in result.horizons
        ],
        history=[
            SeriesPoint(date=ts.date(), value=float(v)) for ts, v in history.items()
        ],
        driver_history=[
            SeriesPoint(date=ts.date(), value=float(v))
            for ts, v in driver.items()
            if v == v
        ],
        explanation_bg=explain_bg(result),
    )

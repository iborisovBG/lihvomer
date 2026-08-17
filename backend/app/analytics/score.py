"""Mortgage Timing Score: 0-100 оценка доколко моментът е подходящ за кредит.

Скалите не са произволни — всяка компонента се нормира спрямо диапазон, който
реално е наблюдаван в българските и европейските данни през последното
десетилетие. Крайните стойности на диапазона дават 0 и 100, а всичко между тях
се интерполира линейно.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.forecast import ForecastResult
from app.analytics.timeseries import load_series, to_daily
from app.ingestion import registry
from app.models import ScoreSnapshot, Signal

MOMENTUM_WINDOW_DAYS = 60

# (стойност за 0 точки, стойност за 100 точки)
REAL_RATE_RANGE = (3.0, -3.0)
MOMENTUM_RANGE = (0.40, -0.40)
FORECAST_RANGE = (0.25, -0.25)
SENTIMENT_RANGE = (-1.0, 1.0)

WEIGHTS_WITHOUT_SENTIMENT = {"real_rate": 0.40, "momentum": 0.30, "forecast": 0.30}
WEIGHTS_WITH_SENTIMENT = {
    "real_rate": 0.35,
    "momentum": 0.25,
    "forecast": 0.25,
    "sentiment": 0.15,
}

TAKE_THRESHOLD = 70.0
WAIT_THRESHOLD = 40.0

SIGNAL_LABELS_BG = {
    Signal.TAKE: "ВЗЕМИ КРЕДИТ",
    Signal.NEUTRAL: "ВНИМАНИЕ / НЕУТРАЛНО",
    Signal.WAIT: "ИЗЧАКАЙ / РИСК",
}


class ScoreUnavailable(RuntimeError):
    """Липсва някой от задължителните входове за оценката."""


@dataclass
class ScoreResult:
    score: float
    signal: Signal
    signal_label_bg: str
    headline_bg: str
    real_rate: float
    bund_momentum_60d: float
    sentiment_score: float | None
    components: dict
    computed_at: datetime


def _normalise(value: float, zero_at: float, hundred_at: float) -> float:
    span = hundred_at - zero_at
    raw = (value - zero_at) / span * 100.0
    return max(0.0, min(100.0, raw))


def _latest(series: pd.Series) -> float | None:
    return None if series.empty else float(series.iloc[-1])


def compute_score(
    db: Session,
    forecast: ForecastResult,
    sentiment_score: float | None = None,
) -> ScoreResult:
    mortgage = load_series(db, registry.BG_MORTGAGE_EUR)
    inflation = load_series(db, registry.HICP_BG)
    bund_daily = to_daily(load_series(db, registry.DE10Y_BUND))

    nominal_rate = _latest(mortgage)
    inflation_rate = _latest(inflation)

    if nominal_rate is None or inflation_rate is None or bund_daily.empty:
        raise ScoreUnavailable(
            "За оценката са нужни ипотечна лихва, инфлация и германска доходност."
        )

    real_rate = nominal_rate - inflation_rate

    last_bund_date = bund_daily.index.max()
    reference_date = last_bund_date - pd.Timedelta(days=MOMENTUM_WINDOW_DAYS)
    bund_now = float(bund_daily.iloc[-1])
    bund_then = float(bund_daily.asof(reference_date))
    momentum = bund_now - bund_then

    ninety = next(
        (h for h in forecast.horizons if h.horizon_days == 90), forecast.horizons[-1]
    )
    forecast_change = ninety.predicted_value - forecast.latest_actual_value

    parts = {
        "real_rate": _normalise(real_rate, *REAL_RATE_RANGE),
        "momentum": _normalise(momentum, *MOMENTUM_RANGE),
        "forecast": _normalise(forecast_change, *FORECAST_RANGE),
    }
    if sentiment_score is not None:
        parts["sentiment"] = _normalise(sentiment_score, *SENTIMENT_RANGE)
        weights = WEIGHTS_WITH_SENTIMENT
    else:
        weights = WEIGHTS_WITHOUT_SENTIMENT

    score = sum(parts[name] * weight for name, weight in weights.items())

    if score > TAKE_THRESHOLD:
        signal = Signal.TAKE
    elif score >= WAIT_THRESHOLD:
        signal = Signal.NEUTRAL
    else:
        signal = Signal.WAIT

    components = {
        "real_rate": {
            "value": round(real_rate, 3),
            "points": round(parts["real_rate"], 1),
            "weight": weights["real_rate"],
            "label_bg": "Реален лихвен процент",
            "explanation_bg": (
                f"Лихвата по жилищните кредити е {nominal_rate:.2f}%, а "
                f"инфлацията {inflation_rate:.2f}%. Реалната цена на кредита е "
                f"{real_rate:+.2f}%"
                + (
                    " — тоест инфлацията изяжда дълга ви по-бързо, отколкото "
                    "растат лихвите."
                    if real_rate < 0
                    else " — тоест кредитът реално ви струва пари над инфлацията."
                )
            ),
        },
        "momentum": {
            "value": round(momentum, 3),
            "points": round(parts["momentum"], 1),
            "weight": weights["momentum"],
            "label_bg": "Посока на германските облигации (60 дни)",
            "explanation_bg": (
                f"За последните {MOMENTUM_WINDOW_DAYS} дни германската "
                f"10-годишна доходност се промени с {momentum:+.2f} пункта "
                f"(от {bund_then:.2f}% на {bund_now:.2f}%). "
                + (
                    "Понижението подсказва по-евтини кредити напред."
                    if momentum < 0
                    else "Покачването се пренася върху българските лихви с "
                    "няколко месеца закъснение."
                )
            ),
        },
        "forecast": {
            "value": round(forecast_change, 3),
            "points": round(parts["forecast"], 1),
            "weight": weights["forecast"],
            "label_bg": "Прогноза за следващите 90 дни",
            "explanation_bg": (
                f"Моделът очаква средната ипотечна лихва да се промени с "
                f"{forecast_change:+.2f} пункта до {ninety.target_date:%m.%Y}."
            ),
        },
    }
    if sentiment_score is not None:
        components["sentiment"] = {
            "value": round(sentiment_score, 3),
            "points": round(parts["sentiment"], 1),
            "weight": weights["sentiment"],
            "label_bg": "Тон на новините от ЕЦБ и ЕС",
            "explanation_bg": "Обобщена оценка на последните икономически новини.",
        }

    headline = _headline_bg(signal, score, real_rate, forecast_change)

    return ScoreResult(
        score=round(score, 2),
        signal=signal,
        signal_label_bg=SIGNAL_LABELS_BG[signal],
        headline_bg=headline,
        real_rate=round(real_rate, 3),
        bund_momentum_60d=round(momentum, 3),
        sentiment_score=sentiment_score,
        components=components,
        computed_at=datetime.now(timezone.utc),
    )


def _headline_bg(
    signal: Signal, score: float, real_rate: float, forecast_change: float
) -> str:
    if signal is Signal.TAKE:
        return (
            f"Моментът е благоприятен ({score:.0f}/100). Реалната цена на "
            f"кредита е {real_rate:+.2f}%, а лихвите се очаква да "
            f"{'намалеят' if forecast_change < 0 else 'останат стабилни'} "
            "през следващите месеци."
        )
    if signal is Signal.NEUTRAL:
        return (
            f"Смесена картина ({score:.0f}/100). Няма ясен сигнал нито за "
            "бързане, нито за изчакване — ако намерите добра оферта, тя е "
            "по-важна от момента."
        )
    return (
        f"Повишен риск ({score:.0f}/100). Показателите сочат натиск нагоре "
        "върху лихвите. Ако можете да изчакате или да фиксирате лихвата, "
        "обмислете го."
    )


def persist_score(db: Session, result: ScoreResult) -> ScoreSnapshot:
    snapshot = ScoreSnapshot(
        score=result.score,
        signal=result.signal,
        real_rate=result.real_rate,
        bund_momentum_60d=result.bund_momentum_60d,
        sentiment_score=result.sentiment_score,
        components=result.components,
    )
    db.add(snapshot)
    db.commit()
    return snapshot

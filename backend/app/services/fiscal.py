"""Фискалното състояние на държавата, преведено към лихвата по кредита.

Връзката не е абстрактна: когато пазарът поиска по-висока доходност по
българския дълг, разликата спрямо германския — спредът — се разширява, а
банките я калкулират в цената на новите кредити.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.timeseries import load_series
from app.ingestion import registry

# Референтната стойност по чл. 126 от ДФЕС и Протокол № 12.
DEFICIT_LIMIT_PCT = -3.0
DEBT_LIMIT_PCT = 60.0
# Нивото, около което се движи спредът BG-DE; ползва се като праг за внимание.
SPREAD_WATCH_BP = 100.0
SPREAD_ALERT_BP = 150.0


@dataclass
class SpreadPoint:
    period: date
    bg_yield: float
    de_yield: float
    spread_bp: float


@dataclass
class FiscalSnapshot:
    debt_pct_gdp: float | None
    debt_period: date | None
    debt_is_quarterly: bool
    deficit_pct_gdp: float | None
    deficit_period: date | None
    deficit_is_quarterly: bool
    exceeds_deficit_limit: bool
    exceeds_debt_limit: bool
    spread_latest_bp: float | None
    spread_period: date | None
    spread_status: str
    spread_history: list[SpreadPoint]
    explanation_bg: str


def _latest(series: pd.Series) -> tuple[date, float] | None:
    if series.empty:
        return None
    return series.index.max().date(), float(series.iloc[-1])


def spread_history(db: Session, limit: int = 60) -> list[SpreadPoint]:
    """Спред BG−DE по 10-годишните държавни облигации, в базисни точки.

    Българският ред е публикуван в лева до приемането на еврото и в евро след
    това; сливаме двата, за да няма дупка в историята.
    """
    bg_eur = load_series(db, registry.BG_10Y_GOVT_EUR)
    bg_bgn = load_series(db, registry.BG_10Y_GOVT_BGN)
    de = load_series(db, registry.DE_10Y_GOVT_M)

    bulgaria = pd.concat([bg_bgn, bg_eur])
    bulgaria = bulgaria[~bulgaria.index.duplicated(keep="last")].sort_index()

    if bulgaria.empty or de.empty:
        return []

    frame = pd.DataFrame({"bg": bulgaria, "de": de}).dropna()
    frame["spread"] = (frame["bg"] - frame["de"]) * 100.0

    return [
        SpreadPoint(
            period=timestamp.date(),
            bg_yield=round(float(row["bg"]), 3),
            de_yield=round(float(row["de"]), 3),
            spread_bp=round(float(row["spread"]), 1),
        )
        for timestamp, row in frame.iloc[-limit:].iterrows()
    ]


def _spread_status(spread_bp: float | None) -> str:
    if spread_bp is None:
        return "UNKNOWN"
    if spread_bp >= SPREAD_ALERT_BP:
        return "ALERT"
    if spread_bp >= SPREAD_WATCH_BP:
        return "WATCH"
    return "CALM"


def build_snapshot(db: Session) -> FiscalSnapshot:
    quarterly_debt = _latest(load_series(db, registry.BG_GOV_DEBT_Q))
    annual_debt = _latest(load_series(db, registry.BG_GOV_DEBT))
    quarterly_balance = _latest(load_series(db, registry.BG_GOV_BALANCE_Q))
    annual_balance = _latest(load_series(db, registry.BG_GOV_BALANCE))

    debt = quarterly_debt or annual_debt
    balance = quarterly_balance or annual_balance

    history = spread_history(db)
    latest_spread = history[-1] if history else None

    debt_value = debt[1] if debt else None
    deficit_value = balance[1] if balance else None
    spread_bp = latest_spread.spread_bp if latest_spread else None

    return FiscalSnapshot(
        debt_pct_gdp=debt_value,
        debt_period=debt[0] if debt else None,
        debt_is_quarterly=quarterly_debt is not None,
        deficit_pct_gdp=deficit_value,
        deficit_period=balance[0] if balance else None,
        deficit_is_quarterly=quarterly_balance is not None,
        exceeds_deficit_limit=(
            deficit_value is not None and deficit_value < DEFICIT_LIMIT_PCT
        ),
        exceeds_debt_limit=debt_value is not None and debt_value > DEBT_LIMIT_PCT,
        spread_latest_bp=spread_bp,
        spread_period=latest_spread.period if latest_spread else None,
        spread_status=_spread_status(spread_bp),
        spread_history=history,
        explanation_bg=_explain(debt_value, deficit_value, spread_bp, latest_spread),
    )


def _explain(
    debt: float | None,
    deficit: float | None,
    spread_bp: float | None,
    latest: SpreadPoint | None,
) -> str:
    parts: list[str] = []

    if debt is not None:
        if debt < DEBT_LIMIT_PCT:
            parts.append(
                f"Държавният дълг е {debt:.1f}% от икономиката — доста под "
                f"тавана от {DEBT_LIMIT_PCT:.0f}%. Това е буферът, който "
                "държи лихвите ви ниски."
            )
        else:
            parts.append(
                f"Държавният дълг е {debt:.1f}% от икономиката и надхвърля "
                f"тавана от {DEBT_LIMIT_PCT:.0f}%."
            )

    if deficit is not None:
        if deficit < DEFICIT_LIMIT_PCT:
            parts.append(
                f"Бюджетът е на дефицит от {abs(deficit):.1f}% от икономиката "
                f"при европейски праг от {abs(DEFICIT_LIMIT_PCT):.0f}%. "
                "Държавата харчи повече, отколкото събира, и разликата се "
                "покрива с нов дълг."
            )
        else:
            parts.append(
                f"Бюджетното салдо е {deficit:+.1f}% от икономиката — в "
                "рамките на европейския праг."
            )

    if spread_bp is not None and latest is not None:
        if spread_bp >= SPREAD_ALERT_BP:
            verdict = (
                "Това е повишено ниво — пазарът иска осезаема премия за "
                "българския риск и банките рано или късно я калкулират в "
                "лихвите."
            )
        elif spread_bp >= SPREAD_WATCH_BP:
            verdict = (
                "Нивото е близо до обичайното за България. Следете дали се "
                "разширява трайно — това е ранният сигнал, месеци преди "
                "промяната да стигне до вноската ви."
            )
        else:
            verdict = "Нивото е спокойно спрямо обичайното за България."
        parts.append(
            f"Разликата между българската и германската 10-годишна облигация "
            f"е {spread_bp:.0f} базисни точки ({latest.bg_yield:.2f}% срещу "
            f"{latest.de_yield:.2f}%). {verdict}"
        )

    return " ".join(parts) if parts else "Липсват достатъчно фискални данни."

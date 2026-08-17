"""Къде отиват парите на държавата — Eurostat COFOG (gov_10a_exp).

Класификацията COFOG разбива публичните разходи по предназначение. Тук се
показват само първото ниво (GF01–GF10) плюс няколко подгрупи, които хората
разпознават — пенсии, болници, училища.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ingestion.http import UpstreamError, fetch_json
from app.ingestion.sources import EUROSTAT_BASE
from app.ingestion.parsing import parse_period, parse_value

logger = logging.getLogger(__name__)

DATASET = "gov_10a_exp"

LABELS_BG: dict[str, str] = {
    "TOTAL": "Общо разходи",
    "GF01": "Общи държавни служби",
    "GF02": "Отбрана",
    "GF03": "Обществен ред и сигурност",
    "GF04": "Икономически дейности",
    "GF05": "Опазване на околната среда",
    "GF06": "Жилища и благоустройство",
    "GF07": "Здравеопазване",
    "GF08": "Култура, спорт и религия",
    "GF09": "Образование",
    "GF10": "Социална защита",
}

DETAIL_LABELS_BG: dict[str, str] = {
    "GF1002": "в т.ч. пенсии за старост",
    "GF0703": "в т.ч. болнична помощ",
    "GF0405": "в т.ч. транспорт",
    "GF0107": "в т.ч. лихви по държавния дълг",
}

TOP_LEVEL = tuple(code for code in LABELS_BG if code != "TOTAL")


@dataclass
class SpendingLine:
    cofog_code: str
    label_bg: str
    pct_gdp: float
    share_of_total_pct: float
    is_detail: bool


@dataclass
class SpendingBreakdown:
    period: str
    total_pct_gdp: float
    lines: list[SpendingLine]
    source_ref: str
    explanation_bg: str


def fetch_breakdown(geo: str = "BG") -> SpendingBreakdown:
    """Тегли последната година с публикувани данни.

    Eurostat връща и години без стойности, затова се връщаме назад, докато
    намерим напълно попълнена.
    """
    payload = fetch_json(
        f"{EUROSTAT_BASE}/{DATASET}",
        {
            "geo": geo,
            "sector": "S13",
            "na_item": "TE",
            "unit": "PC_GDP",
            "format": "JSON",
            "lang": "EN",
            "lastTimePeriod": "4",
        },
    )

    dimension_ids: list[str] = payload.get("id", [])
    values: dict = payload.get("value", {})
    if "cofog99" not in dimension_ids or not values:
        raise UpstreamError(
            f"Eurostat не върна COFOG разбивка за {geo} (измерения={dimension_ids})."
        )

    cofog_index: dict[str, int] = payload["dimension"]["cofog99"]["category"]["index"]
    time_index: dict[str, int] = payload["dimension"]["time"]["category"]["index"]
    period_count = len(time_index)

    # Row-major: cofog99 предхожда time, а измеренията между тях са с размер 1.
    def value_at(cofog_code: str, time_position: int) -> float | None:
        cofog_position = cofog_index.get(cofog_code)
        if cofog_position is None:
            return None
        return parse_value(values.get(str(cofog_position * period_count + time_position)))

    for period, time_position in sorted(time_index.items(), reverse=True):
        total = value_at("TOTAL", time_position)
        if total is None:
            continue

        lines: list[SpendingLine] = []
        for code in TOP_LEVEL:
            amount = value_at(code, time_position)
            if amount is None:
                continue
            lines.append(
                SpendingLine(
                    cofog_code=code,
                    label_bg=LABELS_BG[code],
                    pct_gdp=round(amount, 2),
                    share_of_total_pct=round(amount / total * 100.0, 1),
                    is_detail=False,
                )
            )

        for code, label in DETAIL_LABELS_BG.items():
            amount = value_at(code, time_position)
            if amount is None:
                continue
            lines.append(
                SpendingLine(
                    cofog_code=code,
                    label_bg=label,
                    pct_gdp=round(amount, 2),
                    share_of_total_pct=round(amount / total * 100.0, 1),
                    is_detail=True,
                )
            )

        if not lines:
            continue

        lines.sort(key=lambda line: (line.is_detail, -line.pct_gdp))
        biggest = max(
            (line for line in lines if not line.is_detail),
            key=lambda line: line.pct_gdp,
            default=None,
        )

        explanation = (
            f"През {period} г. държавата е изхарчила {total:.1f}% от всичко, "
            f"което икономиката произвежда."
        )
        if biggest is not None:
            explanation += (
                f" Най-голямото перо е „{biggest.label_bg}“ с {biggest.pct_gdp:.1f}% "
                f"от БВП, или {biggest.share_of_total_pct:.0f}% от целия бюджет."
            )
        explanation += (
            " Когато тези разходи растат по-бързо от приходите, разликата се "
            "финансира с нов дълг — а цената на този дълг се пренася върху "
            "лихвите по кредитите."
        )

        return SpendingBreakdown(
            period=period,
            total_pct_gdp=round(total, 2),
            lines=lines,
            source_ref=f"Eurostat {DATASET} (COFOG), geo={geo}",
            explanation_bg=explanation,
        )

    raise UpstreamError(
        f"Eurostat няма публикувани COFOG стойности за {geo} в последните "
        f"{period_count} периода."
    )

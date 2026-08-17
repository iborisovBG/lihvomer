"""Адаптери към четирите публични източника.

Всеки адаптер връща списък от (дата, стойност) и не знае нищо за базата.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime

from app.ingestion.http import UpstreamError, fetch_json, fetch_text
from app.ingestion.parsing import Observation, dedupe_sorted, parse_period, parse_value
from app.ingestion.registry import SeriesDef
from app.models import SourceSystem

logger = logging.getLogger(__name__)

ECB_BASE = "https://data-api.ecb.europa.eu/service/data"
BUNDESBANK_BASE = "https://api.statistiken.bundesbank.de/rest/data"
EUROSTAT_BASE = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
)


def fetch_ecb(series: SeriesDef, start: date | None = None) -> list[Observation]:
    """ЕЦБ Data Portal, SDMX 2.1, CSV представяне.

    CSV се предпочита пред JSON, защото ЕЦБ изисква точна version-негоциация
    за JSON, а колоните в CSV са именувани и стабилни между dataflow-ите.
    """
    params = {"format": "csvdata", "detail": "dataonly"}
    if start is not None:
        params["startPeriod"] = start.isoformat()

    body = fetch_text(f"{ECB_BASE}/{series.source_ref}", params)
    reader = csv.DictReader(io.StringIO(body))

    if reader.fieldnames is None or "TIME_PERIOD" not in reader.fieldnames:
        raise UpstreamError(
            f"ЕЦБ върна неочакван формат за {series.code}: {body[:200]}"
        )

    observations: list[Observation] = []
    for row in reader:
        obs_date = parse_period(row.get("TIME_PERIOD", ""))
        value = parse_value(row.get("OBS_VALUE"))
        if obs_date is not None and value is not None:
            observations.append((obs_date, value))

    return dedupe_sorted(observations)


def fetch_bundesbank(
    series: SeriesDef, start: date | None = None
) -> list[Observation]:
    """Bundesbank REST API. CSV с блок от метаредове преди самите данни."""
    params = {"format": "csv", "lang": "en"}
    if start is not None:
        params["startPeriod"] = start.isoformat()

    body = fetch_text(f"{BUNDESBANK_BASE}/{series.source_ref}", params)

    observations: list[Observation] = []
    for row in csv.reader(io.StringIO(body)):
        if len(row) < 2:
            continue
        obs_date = parse_period(row[0].lstrip("﻿"))
        if obs_date is None:
            continue
        value = parse_value(row[1])
        if value is not None:
            observations.append((obs_date, value))

    if not observations:
        raise UpstreamError(
            f"Bundesbank не върна нито едно наблюдение за {series.code}."
        )
    return dedupe_sorted(observations)


def fetch_eurostat(series: SeriesDef, start: date | None = None) -> list[Observation]:
    """Eurostat dissemination API, формат JSON-stat 2.0.

    Стойностите идват като плосък речник, индексиран по позиция в
    многомерния куб, затова възстановяваме стъпката на времевото измерение.
    """
    params = {"format": "JSON", "lang": "EN", **series.params}
    if start is not None:
        params["sinceTimePeriod"] = start.strftime("%Y-%m")

    payload = fetch_json(f"{EUROSTAT_BASE}/{series.source_ref}", params)

    dimension_ids: list[str] = payload.get("id", [])
    sizes: list[int] = payload.get("size", [])
    values: dict = payload.get("value", {})

    if "time" not in dimension_ids or not values:
        raise UpstreamError(
            f"Eurostat не върна данни за {series.code} "
            f"(измерения={dimension_ids}, брой стойности={len(values)})."
        )

    time_axis = dimension_ids.index("time")
    # Row-major подредба: стъпката е произведението на размерите след оста.
    stride = 1
    for size in sizes[time_axis + 1 :]:
        stride *= size

    time_index: dict[str, int] = (
        payload["dimension"]["time"]["category"]["index"]
    )

    observations: list[Observation] = []
    for period, position in time_index.items():
        obs_date = parse_period(period)
        if obs_date is None:
            continue
        value = parse_value(values.get(str(position * stride)))
        if value is not None:
            observations.append((obs_date, value))

    return dedupe_sorted(observations)


def fetch_us_treasury(
    series: SeriesDef, start: date | None = None
) -> list[Observation]:
    """Официалната дневна крива на доходността на US Treasury.

    Ресурсът се сервира по една календарна година, затова обхождаме годините
    от началото на заявения период до текущата. `source_ref` е името на
    колоната със съответната матуритетна точка (например "10 Yr").
    """
    first_year = (start or date(2014, 1, 1)).year
    last_year = date.today().year

    observations: list[Observation] = []
    for year in range(first_year, last_year + 1):
        body = fetch_text(
            "https://home.treasury.gov/resource-center/data-chart-center"
            f"/interest-rates/daily-treasury-rates.csv/{year}/all",
            {"type": "daily_treasury_yield_curve", "_format": "csv"},
        )
        reader = csv.DictReader(io.StringIO(body))
        if reader.fieldnames is None or series.source_ref not in reader.fieldnames:
            logger.warning(
                "US Treasury: липсва колона %r за %s", series.source_ref, year
            )
            continue

        for row in reader:
            try:
                obs_date = datetime.strptime(row["Date"].strip(), "%m/%d/%Y").date()
            except (KeyError, ValueError):
                continue
            value = parse_value(row.get(series.source_ref))
            if value is not None:
                observations.append((obs_date, value))

    if not observations:
        raise UpstreamError(
            f"US Treasury не върна наблюдения за колона {series.source_ref}."
        )
    return dedupe_sorted(observations)


_ADAPTERS = {
    SourceSystem.ECB: fetch_ecb,
    SourceSystem.BUNDESBANK: fetch_bundesbank,
    SourceSystem.EUROSTAT: fetch_eurostat,
    SourceSystem.US_TREASURY: fetch_us_treasury,
}


def fetch_series(series: SeriesDef, start: date | None = None) -> list[Observation]:
    return _ADAPTERS[series.source](series, start)

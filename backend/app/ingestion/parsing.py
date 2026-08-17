from __future__ import annotations

import re
from datetime import date

Observation = tuple[date, float]

_DAILY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MONTHLY = re.compile(r"^(\d{4})-(\d{2})$")
_QUARTERLY = re.compile(r"^(\d{4})-?Q([1-4])$")
_SEMESTER = re.compile(r"^(\d{4})-?S([12])$")
_ANNUAL = re.compile(r"^(\d{4})$")


def parse_period(raw: str) -> date | None:
    """Свежда SDMX/Eurostat период до първия ден от периода.

    Месечните и годишните наблюдения описват цял период, не конкретен ден;
    закотвяме ги в началото му, за да е еднозначно сравнението между редове
    с различна честота.
    """
    token = raw.strip()

    if m := _DAILY.match(token):
        return date(int(m[1]), int(m[2]), int(m[3]))
    if m := _MONTHLY.match(token):
        return date(int(m[1]), int(m[2]), 1)
    if m := _QUARTERLY.match(token):
        return date(int(m[1]), (int(m[2]) - 1) * 3 + 1, 1)
    if m := _SEMESTER.match(token):
        return date(int(m[1]), 1 if m[2] == "1" else 7, 1)
    if m := _ANNUAL.match(token):
        return date(int(m[1]), 1, 1)
    return None


def parse_value(raw: str | float | int | None) -> float | None:
    """Празно, ':' и '.' са маркери за липсваща стойност в тези източници."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    token = raw.strip()
    if token in {"", ".", ":", "-", "NA", "N/A"}:
        return None
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def dedupe_sorted(observations: list[Observation]) -> list[Observation]:
    """Последната стойност за дадена дата печели; резултатът е хронологичен."""
    collapsed: dict[date, float] = {}
    for obs_date, value in observations:
        collapsed[obs_date] = value
    return sorted(collapsed.items())

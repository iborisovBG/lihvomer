"""Зареждане на банкови тарифи в базата.

    .venv/bin/python -m scripts.load_bank_offers data/bank_offers.json

Всеки запис задължително носи `source_url` и `rate_effective_date`. Това не е
формалност: приложението показва тези оферти на хора, които вземат решение за
кредит, и всяко число трябва да може да бъде проследено до публикуваната
тарифа на банката и до датата, на която е била в сила. Записи без проследим
произход се отхвърлят.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import BankOffer, Currency, IndexType, LoanType

REQUIRED = ("bank_name", "product_name", "loan_type", "currency", "index_type",
            "source_url", "rate_effective_date")

NUMERIC_DEFAULTS = {
    "margin_pct": 0.0,
    "arrangement_fee_pct": 0.0,
    "arrangement_fee_fixed": 0.0,
    "monthly_fee": 0.0,
    "property_insurance_annual_pct": 0.0,
    "life_insurance_annual_pct": 0.0,
}


def _validate(entry: dict, position: int) -> list[str]:
    problems = []

    for field in REQUIRED:
        if not entry.get(field):
            problems.append(f"липсва задължително поле `{field}`")

    index_type = entry.get("index_type")
    if index_type == IndexType.FIXED.value and entry.get("fixed_rate_pct") is None:
        problems.append("при фиксирана лихва `fixed_rate_pct` е задължително")
    if index_type in {IndexType.BLP.value} and entry.get("fixed_rate_pct") is None:
        problems.append(
            "БЛП не се публикува централизирано — задайте `fixed_rate_pct` "
            "с текущата обявена от банката обща лихва"
        )

    url = str(entry.get("source_url", ""))
    if url and not url.startswith("https://"):
        problems.append("`source_url` трябва да е https адрес към тарифата на банката")

    raw_date = entry.get("rate_effective_date")
    if raw_date:
        try:
            effective = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
        except ValueError:
            problems.append("`rate_effective_date` трябва да е във формат ГГГГ-ММ-ДД")
        else:
            if effective > date.today():
                problems.append("`rate_effective_date` е в бъдещето")

    return [f"запис #{position} ({entry.get('bank_name', '?')}): {p}" for p in problems]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Файлът {path} не съществува.")
        return 2

    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        print("Файлът трябва да съдържа списък от оферти.")
        return 2

    problems: list[str] = []
    for position, entry in enumerate(entries, start=1):
        problems.extend(_validate(entry, position))

    if problems:
        print(f"Отхвърлени {len(problems)} проблема — нищо не е записано:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    written = 0
    with SessionLocal() as db:
        for entry in entries:
            existing = db.scalar(
                select(BankOffer).where(
                    BankOffer.bank_name == entry["bank_name"],
                    BankOffer.product_name == entry["product_name"],
                    BankOffer.currency == Currency(entry["currency"]),
                )
            )
            offer = existing or BankOffer()

            offer.bank_name = entry["bank_name"]
            offer.product_name = entry["product_name"]
            offer.loan_type = LoanType(entry["loan_type"])
            offer.currency = Currency(entry["currency"])
            offer.index_type = IndexType(entry["index_type"])
            offer.fixed_rate_pct = entry.get("fixed_rate_pct")
            offer.max_ltv_pct = entry.get("max_ltv_pct")
            offer.min_amount = entry.get("min_amount")
            offer.max_amount = entry.get("max_amount")
            offer.max_months = entry.get("max_months")
            offer.source_url = entry["source_url"]
            offer.rate_effective_date = datetime.strptime(
                entry["rate_effective_date"], "%Y-%m-%d"
            ).date()
            offer.is_active = entry.get("is_active", True)

            for field, default in NUMERIC_DEFAULTS.items():
                setattr(offer, field, entry.get(field, default))

            if existing is None:
                db.add(offer)
            written += 1

        db.commit()

    print(f"Записани {written} оферти от {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

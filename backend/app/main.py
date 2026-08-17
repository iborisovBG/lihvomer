from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api import (
    advice,
    auth,
    calculator,
    fiscal,
    forecast,
    loans,
    macro,
    notifications,
)
from app.config import get_settings
from app.db import SessionLocal
from app.models import MacroSeries

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title="Лихвомер — мониторинг и прогноза на кредитните лихви в България",
    version="1.0.0",
    description=(
        "Данните идват изцяло от публични официални източници: ЕЦБ Data "
        "Portal, Deutsche Bundesbank, Eurostat и US Treasury."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(macro.router)
app.include_router(forecast.router)
app.include_router(loans.router)
app.include_router(calculator.router)
app.include_router(fiscal.router)
app.include_router(advice.router)
app.include_router(notifications.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        series_count = len(db.scalars(select(MacroSeries.code)).all())
    return {"status": "ok", "series_registered": series_count}

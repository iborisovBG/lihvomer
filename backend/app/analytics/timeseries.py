from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MacroObservation, MacroSeries


def load_series(db: Session, code: str) -> pd.Series:
    """Наблюденията на един ред като pandas Series, индексирана по дата."""
    rows = db.execute(
        select(MacroObservation.obs_date, MacroObservation.value)
        .join(MacroSeries)
        .where(MacroSeries.code == code)
        .order_by(MacroObservation.obs_date)
    ).all()

    if not rows:
        return pd.Series(dtype="float64", name=code)

    index = pd.DatetimeIndex([r[0] for r in rows])
    return pd.Series([float(r[1]) for r in rows], index=index, name=code)


def to_daily(series: pd.Series) -> pd.Series:
    """Разпъва реда до календарни дни.

    Пазарните редове нямат стойности в почивните дни, а месечните имат по
    една стойност за цял период; и в двата случая последната известна
    стойност важи до следващата публикация.
    """
    if series.empty:
        return series
    daily_index = pd.date_range(series.index.min(), series.index.max(), freq="D")
    return series.reindex(daily_index).ffill()

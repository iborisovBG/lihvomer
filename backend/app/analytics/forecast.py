"""Иконометричен модел за пренасянето на европейските лихви върху българските.

Методология
-----------
И българската ипотечна лихва, и германската доходност са интегрирани от първи
ред (ADF не отхвърля единичен корен в нива, отхвърля го в първи разлики).
Регресия в нива между два такива реда е привидна (spurious) — дава висока
привидна значимост при силно автокорелирани остатъци. Затова моделът се
оценява в **първи разлики**:

    Δy_t = c + φ·Δy_(t-1) + δ·Δx_(t-L) + ε_t

    y = средна лихва по нови жилищни кредити в България (ЕЦБ MIR)
    x = германска 10-годишна доходност (Bundesbank), месечно осреднена
    L = закъснението на пренасянето, избрано по коригиран R²

φ улавя връщането към средното при месечните промени, δ е коефициентът на
пренасяне, а c — трендът на сближаване на българските лихви с европейските.

Прогнозата за нивото се получава чрез рекурсивно натрупване на прогнозните
изменения. Докато хоризонтът не надхвърли L, нужните изменения на драйвера са
вече наблюдавани; отвъд L драйверът се третира като случайно лутане, което е
стандартното допускане за доходности.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sqlalchemy.orm import Session
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import adfuller

from app.analytics.timeseries import load_series, to_daily
from app.ingestion import registry
from app.models import ForecastPoint, ForecastRun

logger = logging.getLogger(__name__)

LAG_GRID_MONTHS = range(1, 9)
HORIZONS_DAYS = (30, 60, 90, 180)
DAYS_PER_MONTH = 30
MIN_OBSERVATIONS = 36
CONFIDENCE_LEVEL = 0.95


class InsufficientData(RuntimeError):
    """Няма достатъчно наблюдения, за да се оцени моделът."""


@dataclass
class HorizonForecast:
    horizon_days: int
    target_date: date
    predicted_value: float
    ci_lower: float
    ci_upper: float
    driver_is_observed: bool


@dataclass
class ForecastResult:
    target_code: str
    driver_code: str
    best_lag_days: int
    n_obs: int
    r_squared: float
    adj_r_squared: float
    diagnostics: dict
    latest_actual_date: date
    latest_actual_value: float
    horizons: list[HorizonForecast] = field(default_factory=list)


def _monthly(series: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Свежда ред с произволна честота до месечни средни по зададения индекс."""
    return to_daily(series).resample("MS").mean().reindex(index)


def _cumulative_std(residual_std: float, phi: float, steps: int) -> float:
    """Стандартна грешка на натрупаното изменение след `steps` месеца.

    За Δy с AR(1) структура сумата от бъдещите изменения се представя чрез
    тегла ψ_m = (1 - φ^(m+1)) / (1 - φ); дисперсията на нивото расте с
    хоризонта, което разширява интервала така, както изисква теорията.
    """
    if abs(1.0 - phi) < 1e-9:
        weights = np.arange(1, steps + 1, dtype=float)
    else:
        powers = np.arange(steps, dtype=float)
        weights = (1.0 - phi ** (powers + 1)) / (1.0 - phi)
    return float(residual_std * np.sqrt(np.sum(weights**2)))


def fit_pass_through_model(
    db: Session,
    target_code: str = registry.BG_MORTGAGE_EUR,
    driver_code: str = registry.DE10Y_BUND,
) -> ForecastResult:
    target = load_series(db, target_code)
    driver = load_series(db, driver_code)

    if target.empty or driver.empty:
        raise InsufficientData(
            f"Липсват данни за {target_code} или {driver_code}. "
            "Пуснете ingestion преди прогнозата."
        )

    driver_monthly = _monthly(driver, target.index)
    d_target = target.diff()
    d_driver = driver_monthly.diff()

    best: tuple[float, int, sm.regression.linear_model.RegressionResults] | None = None
    lag_scores: dict[int, float] = {}

    for lag_months in LAG_GRID_MONTHS:
        frame = pd.DataFrame(
            {
                "dy": d_target,
                "dy_lag1": d_target.shift(1),
                "dx_lag": d_driver.shift(lag_months),
            }
        ).dropna()

        if len(frame) < MIN_OBSERVATIONS:
            continue

        model = sm.OLS(
            frame["dy"], sm.add_constant(frame[["dy_lag1", "dx_lag"]])
        ).fit()
        lag_scores[lag_months] = round(float(model.rsquared_adj), 5)

        if best is None or model.rsquared_adj > best[0]:
            best = (float(model.rsquared_adj), lag_months, model)

    if best is None:
        raise InsufficientData(
            f"Под {MIN_OBSERVATIONS} използваеми наблюдения при всички лагове."
        )

    _, best_lag, fitted = best
    constant = float(fitted.params["const"])
    phi = float(fitted.params["dy_lag1"])
    delta = float(fitted.params["dx_lag"])
    residual_std = float(np.std(fitted.resid, ddof=len(fitted.params)))

    adf_level = adfuller(target.dropna(), autolag="AIC")
    adf_diff = adfuller(target.diff().dropna(), autolag="AIC")

    diagnostics = {
        "specification": "Δy_t = c + φ·Δy_(t-1) + δ·Δx_(t-L)",
        "lag_grid_adj_r2_by_month": lag_scores,
        "constant_drift_pp_per_month": round(constant, 5),
        "constant_p_value": float(fitted.pvalues["const"]),
        "phi_mean_reversion": round(phi, 5),
        "phi_p_value": float(fitted.pvalues["dy_lag1"]),
        "delta_pass_through": round(delta, 5),
        "delta_p_value": float(fitted.pvalues["dx_lag"]),
        "delta_std_err": round(float(fitted.bse["dx_lag"]), 5),
        "durbin_watson": round(float(durbin_watson(fitted.resid)), 4),
        "residual_std_pp_per_month": round(residual_std, 5),
        "adf_level_p_value": round(float(adf_level[1]), 5),
        "adf_first_difference_p_value": round(float(adf_diff[1]), 5),
        "confidence_level": CONFIDENCE_LEVEL,
        "estimation_start": str(target.index.min().date()),
        "estimation_end": str(target.index.max().date()),
    }

    last_level = float(target.iloc[-1])
    last_date = target.index.max().date()
    last_change = float(d_target.iloc[-1]) if not np.isnan(d_target.iloc[-1]) else 0.0

    max_steps = max(HORIZONS_DAYS) // DAYS_PER_MONTH
    critical = float(stats.norm.ppf(0.5 + CONFIDENCE_LEVEL / 2))

    # Рекурсия напред: всяко следващо изменение зависи от предходното.
    level = last_level
    previous_change = last_change
    projected: dict[int, tuple[float, bool]] = {}

    for step in range(1, max_steps + 1):
        driver_position = len(d_driver) - 1 + step - best_lag
        if 0 <= driver_position < len(d_driver):
            raw = d_driver.iloc[driver_position]
            driver_change = 0.0 if pd.isna(raw) else float(raw)
            observed = True
        else:
            driver_change = 0.0
            observed = False

        change = constant + phi * previous_change + delta * driver_change
        level += change
        previous_change = change
        projected[step] = (level, observed)

    horizons: list[HorizonForecast] = []
    for horizon in HORIZONS_DAYS:
        steps = horizon // DAYS_PER_MONTH
        predicted, observed = projected[steps]
        margin = critical * _cumulative_std(residual_std, phi, steps)
        horizons.append(
            HorizonForecast(
                horizon_days=horizon,
                target_date=date.today() + timedelta(days=horizon),
                predicted_value=round(predicted, 4),
                ci_lower=round(predicted - margin, 4),
                ci_upper=round(predicted + margin, 4),
                driver_is_observed=observed,
            )
        )

    return ForecastResult(
        target_code=target_code,
        driver_code=driver_code,
        best_lag_days=best_lag * DAYS_PER_MONTH,
        n_obs=int(fitted.nobs),
        r_squared=round(float(fitted.rsquared), 5),
        adj_r_squared=round(float(fitted.rsquared_adj), 5),
        diagnostics=diagnostics,
        latest_actual_date=last_date,
        latest_actual_value=last_level,
        horizons=horizons,
    )


def persist_forecast(db: Session, result: ForecastResult) -> ForecastRun:
    run = ForecastRun(
        target_series_code=result.target_code,
        driver_series_code=result.driver_code,
        best_lag_days=result.best_lag_days,
        n_obs=result.n_obs,
        r_squared=result.r_squared,
        adj_r_squared=result.adj_r_squared,
        diagnostics=result.diagnostics,
    )
    run.points = [
        ForecastPoint(
            horizon_days=h.horizon_days,
            target_date=h.target_date,
            predicted_value=h.predicted_value,
            ci_lower=h.ci_lower,
            ci_upper=h.ci_upper,
        )
        for h in result.horizons
    ]
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def explain_bg(result: ForecastResult) -> str:
    ninety = next(
        (h for h in result.horizons if h.horizon_days == 90), result.horizons[-1]
    )
    change = ninety.predicted_value - result.latest_actual_value
    months = result.best_lag_days // DAYS_PER_MONTH
    pass_through = result.diagnostics["delta_pass_through"]

    if change > 0.10:
        direction = f"да се повиши с около {change:.2f} процентни пункта"
    elif change < -0.10:
        direction = f"да се понижи с около {abs(change):.2f} процентни пункта"
    else:
        direction = "да се задържи на приблизително същото ниво"

    return (
        f"Когато германската 10-годишна доходност се промени с 1 процентен "
        f"пункт, средната лихва по нови жилищни кредити в България се променя "
        f"с около {pass_through:.2f} пункта, но чак след {months} месеца. "
        f"Спрямо последното отчетено ниво от {result.latest_actual_value:.2f}% "
        f"({result.latest_actual_date:%m.%Y}) моделът очаква лихвата "
        f"{direction} до {ninety.target_date:%m.%Y}, като реалната стойност "
        f"най-вероятно ще е между {ninety.ci_lower:.2f}% и {ninety.ci_upper:.2f}%. "
        f"Моделът обяснява {result.r_squared * 100:.0f}% от месечните движения — "
        f"останалото зависи от конкуренцията между банките и от собствената им "
        f"ценова политика."
    )

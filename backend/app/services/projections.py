"""Превръща прогнозата за лихвите в конкретни левове по конкретния кредит."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.analytics.finance import monthly_payment, total_interest
from app.analytics.forecast import ForecastResult, fit_pass_through_model
from app.analytics.timeseries import load_series
from app.config import get_settings
from app.ingestion import registry
from app.models import Currency, IndexType, UserLoan
from app.schemas import LoanHorizon, LoanProjection
from app.services.analytics_cache import get_or_compute

_settings = get_settings()

INDEX_SERIES = {
    IndexType.EURIBOR_3M: registry.EURIBOR_3M,
    IndexType.EURIBOR_6M: registry.EURIBOR_6M,
    IndexType.EURIBOR_12M: registry.EURIBOR_12M,
}


def forecast_for(db: Session, series_code: str) -> ForecastResult:
    return get_or_compute(
        f"forecast:{series_code}",
        lambda: fit_pass_through_model(db, target_code=series_code),
    )


def to_eur(amount: float, currency: Currency) -> float:
    """България е в еврозоната; сумите се показват в евро.

    Кредити, въведени в лева преди приемането на еврото, се преобразуват по
    неотменимия фиксинг на БНБ.
    """
    return amount if currency is Currency.EUR else amount / _settings.bgn_per_eur


# Ако въведената лихва се разминава с „индекс + надбавка" с повече от това,
# предупреждаваме потребителя, вместо мълчаливо да сметнем нещо подвеждащо.
MARGIN_MISMATCH_TOLERANCE_PP = 0.30

# Колко често се преоценява лихвата при всеки индекс, когато договорът не
# посочва конкретна дата.
REPRICING_MONTHS = {
    IndexType.EURIBOR_3M: 3,
    IndexType.EURIBOR_6M: 6,
    IndexType.EURIBOR_12M: 12,
}


def _current_index_value(db: Session, index_type: IndexType) -> tuple[float, date] | None:
    series_code = INDEX_SERIES.get(index_type)
    if series_code is None:
        return None
    series = load_series(db, series_code)
    if series.empty:
        return None
    return float(series.iloc[-1]), series.index.max().date()


def project_loan(db: Session, loan: UserLoan) -> LoanProjection:
    principal = float(loan.principal_amount)
    months = int(loan.remaining_months)
    current_rate = float(loan.current_interest_rate)
    current_payment = monthly_payment(principal, current_rate, months)

    horizons: list[LoanHorizon] = []
    warning: str | None = None

    if loan.index_type is IndexType.FIXED:
        explanation = (
            "Лихвата по този кредит е фиксирана, затова вноската ви не се "
            "влияе от движението на Euribor или на европейските лихви. "
            "Прогнозата показва същата вноска за целия хоризонт."
        )
        forecast = None
    elif loan.index_type is IndexType.BLP:
        # БЛП се определя от всяка банка поотделно и не се публикува
        # централизирано, затова ползваме пазарната средна като приблизител.
        forecast = forecast_for(db, registry.BG_MORTGAGE_EUR)
        explanation = (
            "Кредитът ви е с БЛП — базов лихвен процент, който всяка банка "
            "определя сама и не се публикува централизирано. Затова "
            "прогнозата ползва като приблизител средната пазарна лихва по нови "
            "жилищни кредити. Реалната промяна зависи от решението на вашата "
            "банка и може да се различава."
        )
    else:
        series_code = INDEX_SERIES[loan.index_type]
        forecast = forecast_for(db, series_code)
        margin = float(loan.margin or 0.0)
        index_now = _current_index_value(db, loan.index_type)
        index_label = loan.index_type.value.replace("EURIBOR_", "Euribor ")
        reprice_months = REPRICING_MONTHS[loan.index_type]

        explanation = (
            f"Лихвата ви е обвързана с {index_label}. Прогнозата взема "
            f"очакваната промяна на индекса и я прибавя към вашата текуща "
            f"лихва от {current_rate:.2f}% — така резултатът не зависи от това "
            f"дали надбавката е въведена съвсем точно."
        )

        if index_now is not None:
            implied_margin = current_rate - index_now[0]
            if abs(implied_margin - margin) > MARGIN_MISMATCH_TOLERANCE_PP:
                warning = (
                    f"Текущият {index_label} е {index_now[0]:.2f}%. С надбавка "
                    f"{margin:.2f}% това би дало лихва {index_now[0] + margin:.2f}%, "
                    f"а вие сте въвели {current_rate:.2f}%. Това е обичайно при "
                    f"{index_label} — лихвата се преоценява веднъж на "
                    f"{reprice_months} месеца, затова носи стойността на индекса "
                    f"отпреди. Прогнозата ползва вашата лихва като отправна "
                    f"точка. Ако надбавката е сгрешена, поправете я в договора си."
                )

        if loan.next_reset_date is None:
            explanation += (
                f" Не сте въвели дата на следваща актуализация. Показваме "
                f"промяната все едно лихвата се преоценява веднага, но при "
                f"{index_label} банката я преоценява веднъж на {reprice_months} "
                f"месеца — до тази дата вноската ви не се променя."
            )
        else:
            explanation += (
                f" Вноската ви остава непроменена до "
                f"{loan.next_reset_date:%d.%m.%Y} г., когато банката преоценява "
                f"лихвата."
            )

    for horizon_days in (30, 60, 90, 180):
        target_date = date.today() + timedelta(days=horizon_days)

        if forecast is None:
            projected_rate = current_rate
            rate_low = rate_high = current_rate
        elif loan.next_reset_date is not None and loan.next_reset_date > target_date:
            # Договорът фиксира лихвата до датата на преоценка; каквото и да
            # прави индексът дотогава, вноската не се променя.
            projected_rate = current_rate
            rate_low = rate_high = current_rate
        else:
            point = next(h for h in forecast.horizons if h.horizon_days == horizon_days)
            # И при индекс, и при БЛП прилагаме ОЧАКВАНАТА ПРОМЯНА върху
            # реалната лихва на потребителя. Възстановяването на нивото от
            # „индекс + надбавка" би дало абсурден скок винаги когато
            # въведената лихва не съвпада точно с текущия индекс — а при
            # 6- и 12-месечните индекси тя почти никога не съвпада, защото
            # отразява стойността от последната преоценка.
            baseline = forecast.latest_actual_value
            projected_rate = current_rate + (point.predicted_value - baseline)
            rate_low = current_rate + (point.ci_lower - baseline)
            rate_high = current_rate + (point.ci_upper - baseline)

        projected_rate = max(0.0, projected_rate)
        payment = monthly_payment(principal, projected_rate, months)
        delta = payment - current_payment

        horizons.append(
            LoanHorizon(
                horizon_days=horizon_days,
                target_date=date.today() + timedelta(days=horizon_days),
                projected_rate_pct=round(projected_rate, 3),
                projected_monthly_payment=round(payment, 2),
                delta_monthly=round(delta, 2),
                delta_monthly_eur=round(to_eur(delta, loan.currency), 2),
                ci_lower_payment=round(
                    monthly_payment(principal, max(0.0, rate_low), months), 2
                ),
                ci_upper_payment=round(
                    monthly_payment(principal, max(0.0, rate_high), months), 2
                ),
            )
        )

    return LoanProjection(
        loan_id=loan.id,
        label=loan.label,
        bank_name=loan.bank_name,
        currency=loan.currency,
        current_rate_pct=round(current_rate, 3),
        current_monthly_payment=round(current_payment, 2),
        horizons=horizons,
        total_interest_remaining=round(
            total_interest(principal, current_rate, months), 2
        ),
        explanation_bg=explanation,
        rate_consistency_warning_bg=warning,
    )

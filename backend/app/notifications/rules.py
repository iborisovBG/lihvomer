"""Кога си струва да обезпокоим потребителя.

Приложението има право на вниманието на човека само когато има какво
конкретно да му каже. Затова всяко правило има праг, а всяко съобщение —
сума в евро и предложено действие.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.advice import MATERIAL_RATE_GAP_PP, compare_to_market
from app.analytics.forecast import InsufficientData
from app.analytics.timeseries import load_series
from app.ingestion import registry
from app.models import (
    LoanType,
    NotificationKind,
    NotificationSeverity,
    User,
    UserLoan,
)
from app.services.projections import project_loan, to_eur

# Колко дни преди преоценката има смисъл да се предупреди. По-рано няма
# какво да се направи, по-късно е късно за преговори с банката.
RESET_WARNING_DAYS = 45
# Проверката „плащате над пазара" се повтаря не по-често от веднъж на
# толкова дни — пазарната средна се движи бавно.
ABOVE_MARKET_COOLDOWN_DAYS = 90


@dataclass
class DraftNotification:
    user_id: int
    loan_id: int | None
    kind: NotificationKind
    severity: NotificationSeverity
    dedupe_key: str
    title_bg: str
    body_bg: str
    action_bg: str | None = None
    payload: dict = field(default_factory=dict)


def _period_key(reference: date, days: int) -> str:
    """Групира времето на кофи, за да не се повтаря едно и също съобщение."""
    return str(reference.toordinal() // days)


def evaluate_user(db: Session, user: User, today: date | None = None) -> list[DraftNotification]:
    today = today or date.today()
    loans = db.scalars(
        select(UserLoan).where(UserLoan.user_id == user.id)
    ).all()
    if not loans:
        return []

    threshold_eur = float(user.alert_threshold_eur)
    drafts: list[DraftNotification] = []

    mortgage = load_series(db, registry.BG_MORTGAGE_EUR)
    consumer = load_series(db, registry.BG_CONSUMER_EUR)

    for loan in loans:
        drafts.extend(_payment_change(db, loan, threshold_eur, today))
        drafts.extend(_reset_approaching(loan, today))
        drafts.extend(_above_market(loan, mortgage, consumer, today))

    return drafts


def _payment_change(
    db: Session, loan: UserLoan, threshold_eur: float, today: date
) -> list[DraftNotification]:
    """Прогнозната вноска се променя над прага, зададен от потребителя."""
    try:
        projection = project_loan(db, loan)
    except InsufficientData:
        return []

    horizon = next(
        (h for h in projection.horizons if h.horizon_days == 90),
        None,
    )
    if horizon is None:
        return []

    change_eur = horizon.delta_monthly_eur
    if abs(change_eur) < threshold_eur:
        return []

    rising = change_eur > 0
    currency = loan.currency.value

    if rising:
        title = f"Вноската по „{loan.label}“ се очаква да се повиши"
        action = "Проверете дали предоговарянето или фиксирането на лихвата си струва."
        severity = NotificationSeverity.WARNING
    else:
        title = f"Вноската по „{loan.label}“ се очаква да се понижи"
        action = "Няма нужда от действие — следете дали тенденцията се задържа."
        severity = NotificationSeverity.OPPORTUNITY

    body = (
        f"До {horizon.target_date:%m.%Y} г. вноската ви в {loan.bank_name} се "
        f"очаква да се промени с {abs(horizon.delta_monthly):.2f} {currency} "
        f"на месец — от "
        f"{projection.current_monthly_payment:.2f} на "
        f"{horizon.projected_monthly_payment:.2f} {currency}. "
        f"Прогнозата е статистическа оценка; реалната стойност най-вероятно "
        f"ще е между {horizon.ci_lower_payment:.2f} и "
        f"{horizon.ci_upper_payment:.2f} {currency}."
    )

    return [
        DraftNotification(
            user_id=loan.user_id,
            loan_id=loan.id,
            kind=NotificationKind.PAYMENT_CHANGE,
            severity=severity,
            # Веднъж на две седмици за даден кредит и посока.
            dedupe_key=(
                f"payment:{loan.id}:{'up' if rising else 'down'}:"
                f"{_period_key(today, 14)}"
            ),
            title_bg=title,
            body_bg=body,
            action_bg=action,
            payload={
                "delta_monthly": horizon.delta_monthly,
                "delta_monthly_eur": change_eur,
                "horizon_days": horizon.horizon_days,
            },
        )
    ]


def _reset_approaching(loan: UserLoan, today: date) -> list[DraftNotification]:
    """Наближава датата, на която банката преизчислява лихвата."""
    if loan.next_reset_date is None:
        return []

    days_left = (loan.next_reset_date - today).days
    if days_left < 0 or days_left > RESET_WARNING_DAYS:
        return []

    return [
        DraftNotification(
            user_id=loan.user_id,
            loan_id=loan.id,
            kind=NotificationKind.RESET_APPROACHING,
            severity=NotificationSeverity.INFO,
            dedupe_key=f"reset:{loan.id}:{loan.next_reset_date.isoformat()}",
            title_bg=f"След {days_left} дни банката преизчислява лихвата ви",
            body_bg=(
                f"На {loan.next_reset_date:%d.%m.%Y} г. {loan.bank_name} "
                f"актуализира лихвата по „{loan.label}“. Това е моментът, в "
                f"който имате най-голяма тежест в разговор за условията — "
                f"след преоценката банката няма причина да я преразглежда "
                f"отново скоро."
            ),
            action_bg="Свържете се с банката преди датата, не след нея.",
            payload={"days_left": days_left},
        )
    ]


def _above_market(
    loan: UserLoan, mortgage, consumer, today: date
) -> list[DraftNotification]:
    """Лихвата на потребителя е осезаемо над средната за нови кредити."""
    series = mortgage if loan.loan_type is LoanType.MORTGAGE else consumer
    if series.empty:
        return []

    market_rate = float(series.iloc[-1])
    market_period = series.index.max().strftime("%m.%Y")
    principal = float(loan.principal_amount)
    months = int(loan.remaining_months)
    rate = float(loan.current_interest_rate)

    comparison = compare_to_market(principal, months, rate, market_rate, market_period)
    if not comparison.is_above_market:
        return []

    monthly_eur = to_eur(comparison.monthly_difference, loan.currency)
    term_eur = to_eur(comparison.remaining_term_difference, loan.currency)

    return [
        DraftNotification(
            user_id=loan.user_id,
            loan_id=loan.id,
            kind=NotificationKind.ABOVE_MARKET,
            severity=NotificationSeverity.OPPORTUNITY,
            dedupe_key=(
                f"market:{loan.id}:{_period_key(today, ABOVE_MARKET_COOLDOWN_DAYS)}"
            ),
            title_bg=f"Плащате над пазара по „{loan.label}“",
            body_bg=(
                f"Лихвата ви е {rate:.2f}%, а средната за нови "
                f"{'жилищни' if loan.loan_type is LoanType.MORTGAGE else 'потребителски'} "
                f"кредити е {market_rate:.2f}% ({market_period} по данни на ЕЦБ). "
                f"Разликата ви струва около {monthly_eur:.0f} € на месец и "
                f"{term_eur:.0f} € до края на срока."
            ),
            action_bg="Поискайте предоговаряне или проверете офертите за рефинансиране.",
            payload={
                "difference_pp": comparison.difference_pp,
                "monthly_difference_eur": round(monthly_eur, 2),
            },
        )
    ]

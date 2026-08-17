from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.analytics.advice import (
    compare_to_market,
    cost_of_waiting,
    evaluate_offer,
    evaluate_early_repayment,
    evaluate_refinancing,
    savings_erosion,
)
from app.analytics.finance import monthly_payment
from app.analytics.timeseries import load_series
from app.deps import CurrentUser, DbSession
from app.ingestion import registry
from app.models import LoanType, UserLoan
from app.schemas import (
    EarlyRepaymentOut,
    LoanHealthOut,
    MarketComparisonOut,
    RefinanceOut,
    OfferOut,
    OfferRequest,
    SavingsOut,
    SavingsRequest,
    WaitingOut,
    WaitingRequest,
)

router = APIRouter(prefix="/api/v1/advice", tags=["advice"])

# Сумите, с които показваме ефекта от предсрочно погасяване. Избрани са
# кръгли и постижими, за да е разбираемо без въвеждане.
EXTRA_PAYMENT_STEPS = (50.0, 100.0, 200.0, 500.0)

REFINANCE_COST_NOTE_BG = (
    "Разходите по рефинансиране не се публикуват централизирано, затова по "
    "подразбиране са нула. Въведете сами какво ви струва прехвърлянето: "
    "оценка на имота, нотариални такси, заличаване и вписване на нова ипотека, "
    "такса за разглеждане. По закон таксата за предсрочно погасяване при "
    "жилищните кредити отпада след първите 12 месеца от усвояването."
)


def _latest(db, code: str) -> tuple[float, str] | None:
    series = load_series(db, code)
    if series.empty:
        return None
    return float(series.iloc[-1]), series.index.max().strftime("%m.%Y")


@router.get("/loan-health", response_model=list[LoanHealthOut])
def loan_health(
    user: CurrentUser,
    db: DbSession,
    refinance_cost: float = Query(default=0.0, ge=0, le=100_000),
) -> list[LoanHealthOut]:
    """Отговаря на въпроса „аз добре ли съм?“ за всеки кредит на потребителя."""
    loans = db.scalars(
        select(UserLoan).where(UserLoan.user_id == user.id).order_by(UserLoan.created_at)
    ).all()
    if not loans:
        return []

    mortgage = _latest(db, registry.BG_MORTGAGE_EUR)
    consumer = _latest(db, registry.BG_CONSUMER_EUR)

    if mortgage is None or consumer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Липсват пазарните лихви от ЕЦБ. Пуснете ingestion.",
        )

    result: list[LoanHealthOut] = []
    for loan in loans:
        market_rate, market_period = (
            mortgage if loan.loan_type is LoanType.MORTGAGE else consumer
        )
        principal = float(loan.principal_amount)
        months = int(loan.remaining_months)
        rate = float(loan.current_interest_rate)

        comparison = compare_to_market(
            principal, months, rate, market_rate, market_period
        )
        refinance = evaluate_refinancing(
            principal, months, rate, market_rate, refinance_cost
        )
        early = [
            evaluate_early_repayment(principal, months, rate, extra)
            for extra in EXTRA_PAYMENT_STEPS
        ]

        result.append(
            LoanHealthOut(
                loan_id=loan.id,
                label=loan.label,
                bank_name=loan.bank_name,
                currency=loan.currency,
                principal_amount=principal,
                remaining_months=months,
                current_monthly_payment=round(
                    monthly_payment(principal, rate, months), 2
                ),
                market=MarketComparisonOut(**comparison.__dict__),
                refinance=RefinanceOut(**refinance.__dict__),
                early_repayment=[EarlyRepaymentOut(**e.__dict__) for e in early],
                refinance_cost_note_bg=REFINANCE_COST_NOTE_BG,
            )
        )

    return result


@router.post("/savings", response_model=SavingsOut)
def savings(payload: SavingsRequest, db: DbSession) -> SavingsOut:
    """Колко покупателна способност губят спестяванията при текущите лихви."""
    code = (
        registry.BG_DEPOSIT_TERM
        if payload.use_term_deposit
        else registry.BG_DEPOSIT_OVERNIGHT
    )
    deposit = _latest(db, code)
    inflation = _latest(db, registry.HICP_BG)

    if deposit is None or inflation is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Липсват депозитната лихва или инфлацията. Пуснете ingestion.",
        )

    deposit_rate, _ = deposit
    inflation_rate, inflation_period = inflation
    erosion = savings_erosion(payload.amount, deposit_rate, inflation_rate)

    return SavingsOut(
        amount=erosion.amount,
        deposit_rate_pct=erosion.deposit_rate_pct,
        deposit_kind_bg=(
            "срочен депозит" if payload.use_term_deposit else "разплащателна сметка"
        ),
        inflation_pct=erosion.inflation_pct,
        inflation_period=inflation_period,
        real_rate_pct=erosion.real_rate_pct,
        annual_loss=erosion.annual_loss,
        five_year_loss=erosion.five_year_loss,
        verdict_bg=erosion.verdict_bg,
    )


ASSUMPTION_NOTE_BG = (
    "Ръстът на цените по подразбиране е последният отчетен от Евростат. "
    "Той е моментна снимка, а не прогноза — двуцифрен ръст рядко се задържа "
    "с години. Сменете го с ваша по-консервативна стойност, за да видите "
    "по-предпазлив сценарий."
)


@router.post("/cost-of-waiting", response_model=WaitingOut)
def cost_of_waiting_endpoint(payload: WaitingRequest, db: DbSession) -> WaitingOut:
    """Колко струва отлагането на покупка при текущия ръст на цените."""
    prices = _latest(db, registry.BG_HOUSE_PRICES)
    deposit = _latest(db, registry.BG_DEPOSIT_TERM)

    if prices is None or deposit is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Липсват цените на жилищата или депозитната лихва.",
        )

    observed_growth, growth_period = prices
    deposit_rate, _ = deposit
    growth = (
        observed_growth if payload.house_growth_pct is None else payload.house_growth_pct
    )

    result = cost_of_waiting(
        payload.target_price,
        payload.down_payment_pct,
        payload.saved_now,
        payload.monthly_saving,
        growth,
        deposit_rate,
    )

    return WaitingOut(
        **result.__dict__,
        house_growth_period=growth_period,
        house_growth_is_observed=payload.house_growth_pct is None,
        assumption_note_bg=ASSUMPTION_NOTE_BG,
    )


@router.post("/evaluate-offer", response_model=OfferOut)
def evaluate_offer_endpoint(payload: OfferRequest, db: DbSession) -> OfferOut:
    """Оценява конкретна банкова оферта срещу средния пазарен ГПР.

    Обръща посоката на сравнението: вместо да класира банки — за което няма
    публичен източник — измерва офертата на потребителя срещу число, което
    идва автоматично от ЕЦБ.
    """
    code = (
        registry.BG_MORTGAGE_APRC
        if payload.loan_type is LoanType.MORTGAGE
        else registry.BG_CONSUMER_APRC
    )
    market = _latest(db, code)
    if market is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Липсва средният пазарен ГПР от ЕЦБ. Пуснете ingestion.",
        )

    market_aprc, market_period = market
    try:
        result = evaluate_offer(
            payload.amount,
            payload.months,
            payload.nominal_rate_pct,
            payload.monthly_fee,
            payload.upfront_fee,
            payload.property_insurance_annual_pct,
            payload.life_insurance_annual_pct,
            market_aprc,
            market_period,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return OfferOut(**result.__dict__)

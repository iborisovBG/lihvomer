from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.analytics.finance import (
    amortization_schedule,
    annual_percentage_rate,
    apr_from_cashflows,
    monthly_payment,
    real_value,
)
from app.analytics.timeseries import load_series
from app.deps import DbSession
from app.ingestion import registry
from app.models import BankOffer, IndexType, LoanType
from app.schemas import (
    AmortizationRow,
    BankQuote,
    CalculatorRequest,
    CalculatorResponse,
    CompareRequest,
    CompareResponse,
)

router = APIRouter(prefix="/api/v1/calculator", tags=["calculator"])

INDEX_SERIES = {
    IndexType.EURIBOR_3M: registry.EURIBOR_3M,
    IndexType.EURIBOR_6M: registry.EURIBOR_6M,
    IndexType.EURIBOR_12M: registry.EURIBOR_12M,
}


@router.post("/payment", response_model=CalculatorResponse)
def payment(payload: CalculatorRequest) -> CalculatorResponse:
    schedule = amortization_schedule(
        payload.amount, payload.annual_rate_pct, payload.months
    )
    base_payment = monthly_payment(
        payload.amount, payload.annual_rate_pct, payload.months
    )

    try:
        apr = annual_percentage_rate(
            payload.amount,
            payload.months,
            base_payment + payload.monthly_fee,
            payload.upfront_fee,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return CalculatorResponse(
        monthly_payment=round(base_payment, 2),
        total_paid=round(
            sum(row.payment for row in schedule)
            + payload.monthly_fee * payload.months
            + payload.upfront_fee,
            2,
        ),
        total_interest=round(sum(row.interest for row in schedule), 2),
        apr_pct=round(apr, 3),
        schedule=[
            AmortizationRow(
                month=row.month,
                payment=row.payment,
                interest=row.interest,
                principal=row.principal,
                balance=row.balance,
            )
            for row in schedule
        ],
    )


def _latest(db, code: str) -> float | None:
    series = load_series(db, code)
    return None if series.empty else float(series.iloc[-1])


def _quote(
    offer: BankOffer,
    request: CompareRequest,
    index_values: dict[str, float],
    inflation_pct: float | None,
) -> BankQuote:
    amount, months = request.amount, request.months

    if offer.index_type is IndexType.FIXED or offer.fixed_rate_pct is not None:
        index_value = None
        nominal = float(offer.fixed_rate_pct or 0.0)
    else:
        series_code = INDEX_SERIES[offer.index_type]
        index_value = index_values.get(series_code)
        nominal = (index_value or 0.0) + float(offer.margin_pct)

    schedule = amortization_schedule(amount, nominal, months)
    base_payment = monthly_payment(amount, nominal, months)

    insured_property = request.property_value or amount
    monthly_property_insurance = (
        float(offer.property_insurance_annual_pct) / 100.0 * insured_property / 12.0
    )
    monthly_fee = float(offer.monthly_fee)

    # Животозастраховката следва остатъчната главница, затова паричните
    # потоци не са константни и ГПР се смята по пълния им профил.
    life_rate_monthly = float(offer.life_insurance_annual_pct) / 100.0 / 12.0
    outflows: list[float] = []
    total_insurance = 0.0
    for row in schedule:
        life_premium = life_rate_monthly * (row.balance + row.principal)
        total_insurance += life_premium + monthly_property_insurance
        outflows.append(
            row.payment + monthly_fee + monthly_property_insurance + life_premium
        )

    upfront = (
        float(offer.arrangement_fee_pct) / 100.0 * amount
        + float(offer.arrangement_fee_fixed)
    )

    try:
        apr = apr_from_cashflows(amount - upfront, outflows)
    except ValueError:
        apr = 0.0

    total_cost = sum(outflows) + upfront
    ltv = (
        round(amount / request.property_value * 100.0, 2)
        if request.property_value
        else None
    )

    disqualified: str | None = None
    if offer.min_amount is not None and amount < float(offer.min_amount):
        disqualified = f"Минимална сума {float(offer.min_amount):,.0f}."
    elif offer.max_amount is not None and amount > float(offer.max_amount):
        disqualified = f"Максимална сума {float(offer.max_amount):,.0f}."
    elif offer.max_months is not None and months > int(offer.max_months):
        disqualified = f"Максимален срок {int(offer.max_months)} месеца."
    elif (
        offer.max_ltv_pct is not None
        and ltv is not None
        and ltv > float(offer.max_ltv_pct)
    ):
        disqualified = (
            f"Финансирането е {ltv:.0f}% от имота при таван {float(offer.max_ltv_pct):.0f}%."
        )

    first_month_total = outflows[0] if outflows else 0.0

    return BankQuote(
        bank_name=offer.bank_name,
        product_name=offer.product_name,
        index_type=offer.index_type,
        index_value_pct=round(index_value, 4) if index_value is not None else None,
        margin_pct=float(offer.margin_pct),
        nominal_rate_pct=round(nominal, 3),
        monthly_payment=round(base_payment, 2),
        monthly_fee=round(monthly_fee, 2),
        monthly_insurance=round(
            monthly_property_insurance + life_rate_monthly * amount, 2
        ),
        total_monthly_cost=round(first_month_total, 2),
        upfront_fees=round(upfront, 2),
        total_cost=round(total_cost, 2),
        total_interest=round(sum(row.interest for row in schedule), 2),
        apr_pct=round(apr, 3),
        ltv_pct=ltv,
        real_monthly_payment_end_of_term=round(
            real_value(first_month_total, inflation_pct, months)
            if inflation_pct is not None
            else first_month_total,
            2,
        ),
        source_url=offer.source_url,
        rate_effective_date=offer.rate_effective_date,
        disqualified_reason=disqualified,
    )


@router.post("/compare-banks", response_model=CompareResponse)
def compare_banks(payload: CompareRequest, db: DbSession) -> CompareResponse:
    offers = db.scalars(
        select(BankOffer).where(
            BankOffer.is_active.is_(True),
            BankOffer.loan_type == payload.loan_type,
            BankOffer.currency == payload.currency,
        )
    ).all()

    index_values = {
        code: value
        for code in INDEX_SERIES.values()
        if (value := _latest(db, code)) is not None
    }
    inflation = _latest(db, registry.HICP_BG)

    market_code = (
        registry.BG_MORTGAGE_EUR
        if payload.loan_type is LoanType.MORTGAGE
        else registry.BG_CONSUMER_EUR
    )
    market_average = _latest(db, market_code)

    quotes = [_quote(offer, payload, index_values, inflation) for offer in offers]

    sort_key = {
        "apr": lambda q: q.apr_pct,
        "monthly_payment": lambda q: q.total_monthly_cost,
        "total_cost": lambda q: q.total_cost,
    }[payload.sort_by]
    # Офертите, за които заявката не отговаря на условията, слизат най-долу.
    quotes.sort(key=lambda q: (q.disqualified_reason is not None, sort_key(q)))

    if market_average is None:
        note = (
            "Средната пазарна лихва все още не е заредена — пуснете ingestion "
            "на данните от ЕЦБ."
        )
    elif offers:
        note = (
            f"Средната лихва по нови {'жилищни' if payload.loan_type is LoanType.MORTGAGE else 'потребителски'} "
            f"кредити в България е {market_average:.2f}% по данни на ЕЦБ (MIR). "
            "Ползвайте я като ориентир дали дадена оферта е конкурентна."
        )
    else:
        note = (
            f"В базата няма заредени банкови оферти, затова таблицата е празна. "
            f"Средната пазарна лихва по данни на ЕЦБ е {market_average:.2f}%. "
            "Заредете реални тарифи през `python -m scripts.load_bank_offers`."
        )

    return CompareResponse(
        generated_at=datetime.now(timezone.utc),
        amount=payload.amount,
        months=payload.months,
        currency=payload.currency,
        inflation_bg_pct=inflation,
        index_values={code: round(value, 4) for code, value in index_values.items()},
        market_average_rate_pct=(
            round(market_average, 3) if market_average is not None else None
        ),
        market_average_note_bg=note,
        quotes=quotes,
    )

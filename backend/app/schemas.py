from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import (
    Currency,
    JobStatus,
    NotificationKind,
    NotificationSeverity,
    IndexType,
    LoanType,
    NewsImpact,
    RiskTolerance,
    Signal,
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    notify_email: bool
    notify_push: bool
    risk_tolerance: RiskTolerance
    alert_threshold_eur: float
    created_at: datetime


class LoanIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    bank_name: str = Field(min_length=1, max_length=120)
    loan_type: LoanType
    currency: Currency
    principal_amount: float = Field(gt=0, le=10_000_000)
    remaining_months: int = Field(ge=1, le=480)
    current_interest_rate: float = Field(ge=0, le=100)
    index_type: IndexType
    margin: float | None = Field(default=None, ge=-5, le=25)
    next_reset_date: date | None = None

    @model_validator(mode="after")
    def _check_margin(self) -> LoanIn:
        if self.index_type is not IndexType.FIXED and self.margin is None:
            raise ValueError(
                "При плаваща лихва е задължително да въведете надбавката над индекса."
            )
        return self


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    bank_name: str
    loan_type: LoanType
    currency: Currency
    principal_amount: float
    remaining_months: int
    current_interest_rate: float
    index_type: IndexType
    margin: float | None
    next_reset_date: date | None
    created_at: datetime
    updated_at: datetime


class LoanProjection(BaseModel):
    """Какво се случва с вноската на конкретния кредит при прогнозните лихви."""

    loan_id: int
    label: str
    bank_name: str
    currency: Currency
    current_rate_pct: float
    current_monthly_payment: float
    horizons: list[LoanHorizon]
    total_interest_remaining: float
    explanation_bg: str
    rate_consistency_warning_bg: str | None = None


class LoanHorizon(BaseModel):
    horizon_days: int
    target_date: date
    projected_rate_pct: float
    projected_monthly_payment: float
    delta_monthly: float
    delta_monthly_eur: float
    ci_lower_payment: float
    ci_upper_payment: float


class SeriesPoint(BaseModel):
    date: date
    value: float


class MacroIndicator(BaseModel):
    code: str
    name_bg: str
    plain_bg: str
    unit: str
    frequency: str
    latest_date: date | None
    latest_value: float | None
    previous_value: float | None
    change: float | None
    source: str
    source_ref: str
    last_ingested_at: datetime | None
    # Последните наблюдения за спарклайн. Посоката на реда казва повече от
    # едно число, а изпращането им тук спестява 26 отделни заявки.
    spark: list[float]


class LiveDashboard(BaseModel):
    generated_at: datetime
    indicators: list[MacroIndicator]
    real_mortgage_rate_pct: float | None
    score: ScoreOut | None


class ScoreOut(BaseModel):
    score: float
    signal: Signal
    signal_label_bg: str
    headline_bg: str
    real_rate: float
    bund_momentum_60d: float
    sentiment_score: float | None
    components: dict
    computed_at: datetime


class ForecastPointOut(BaseModel):
    horizon_days: int
    target_date: date
    predicted_value: float
    ci_lower: float
    ci_upper: float


class ForecastOut(BaseModel):
    target_series_code: str
    driver_series_code: str
    best_lag_days: int
    n_obs: int
    r_squared: float
    adj_r_squared: float
    diagnostics: dict
    latest_actual_date: date
    latest_actual_value: float
    points: list[ForecastPointOut]
    history: list[SeriesPoint]
    driver_history: list[SeriesPoint]
    explanation_bg: str


class AmortizationRow(BaseModel):
    month: int
    payment: float
    interest: float
    principal: float
    balance: float


class PaymentBreakdown(BaseModel):
    monthly_payment: float
    total_paid: float
    total_interest: float
    effective_rate_pct: float


class CompareRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    months: int = Field(ge=6, le=480)
    loan_type: LoanType
    currency: Currency = Currency.EUR
    property_value: float | None = Field(default=None, gt=0)
    sort_by: str = Field(default="apr", pattern="^(apr|monthly_payment|total_cost)$")

    @model_validator(mode="after")
    def _check_ltv_inputs(self) -> CompareRequest:
        if self.property_value is not None and self.property_value < self.amount:
            raise ValueError(
                "Стойността на имота не може да е по-малка от искания кредит."
            )
        return self


class BankQuote(BaseModel):
    bank_name: str
    product_name: str
    index_type: IndexType
    index_value_pct: float | None
    margin_pct: float
    nominal_rate_pct: float
    monthly_payment: float
    monthly_fee: float
    monthly_insurance: float
    total_monthly_cost: float
    upfront_fees: float
    total_cost: float
    total_interest: float
    apr_pct: float
    ltv_pct: float | None
    real_monthly_payment_end_of_term: float
    source_url: str
    rate_effective_date: date
    disqualified_reason: str | None


class CompareResponse(BaseModel):
    generated_at: datetime
    amount: float
    months: int
    currency: Currency
    inflation_bg_pct: float | None
    index_values: dict[str, float]
    market_average_rate_pct: float | None
    market_average_note_bg: str
    quotes: list[BankQuote]


class CalculatorRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    months: int = Field(ge=1, le=480)
    annual_rate_pct: float = Field(ge=0, le=100)
    monthly_fee: float = Field(default=0, ge=0)
    upfront_fee: float = Field(default=0, ge=0)


class CalculatorResponse(BaseModel):
    monthly_payment: float
    total_paid: float
    total_interest: float
    apr_pct: float
    schedule: list[AmortizationRow]


LoanProjection.model_rebuild()
LiveDashboard.model_rebuild()


# --- Фискален модул --------------------------------------------------------


class SpreadPointOut(BaseModel):
    period: date
    bg_yield: float
    de_yield: float
    spread_bp: float


class FiscalOut(BaseModel):
    debt_pct_gdp: float | None
    debt_period: date | None
    debt_is_quarterly: bool
    debt_limit_pct: float
    deficit_pct_gdp: float | None
    deficit_period: date | None
    deficit_is_quarterly: bool
    deficit_limit_pct: float
    exceeds_deficit_limit: bool
    exceeds_debt_limit: bool
    spread_latest_bp: float | None
    spread_period: date | None
    spread_status: str
    spread_watch_bp: float
    spread_alert_bp: float
    spread_history: list[SpreadPointOut]
    explanation_bg: str


class SpendingLineOut(BaseModel):
    cofog_code: str
    label_bg: str
    pct_gdp: float
    share_of_total_pct: float
    is_detail: bool


class SpendingOut(BaseModel):
    period: str
    total_pct_gdp: float
    lines: list[SpendingLineOut]
    source_ref: str
    explanation_bg: str


# --- Новини ----------------------------------------------------------------


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_code: str
    source_name: str
    url: str
    language: str
    title_bg: str
    title_original: str
    summary_bg: str | None
    was_translated: bool
    published_at: datetime
    sentiment_score: float
    impact: NewsImpact
    wallet_explanation_bg: str
    is_bulgaria_related: bool


class NewsFeedOut(BaseModel):
    generated_at: datetime
    aggregate_sentiment: float | None
    aggregate_label_bg: str
    translator_available: bool
    items: list[NewsItemOut]


# --- Свежест на данните ----------------------------------------------------


class FreshnessOut(BaseModel):
    code: str
    name_bg: str
    latest_date: date | None
    age_days: int | None
    expected_max_age_days: int
    is_stale: bool
    superseded_by: str | None
    source: str


class SourceSeriesOut(BaseModel):
    code: str
    name_bg: str
    plain_bg: str
    frequency: str
    source_ref: str
    browse_url: str
    latest_date: date | None
    superseded_by: str | None


class SourceProviderOut(BaseModel):
    key: str
    name_bg: str
    description_bg: str
    portal_url: str
    api_base_url: str
    licence_bg: str
    series: list[SourceSeriesOut]


class NewsFeedSourceOut(BaseModel):
    code: str
    name_bg: str
    url: str
    language: str


class SourcesOut(BaseModel):
    generated_at: datetime
    providers: list[SourceProviderOut]
    news_feeds: list[NewsFeedSourceOut]
    disclaimer_bg: str


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_name: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None
    items_ok: int
    items_failed: int


class AutomationOut(BaseModel):
    generated_at: datetime
    worker_online: bool
    schedule_bg: dict[str, str]
    last_runs: list[JobRunOut]
    hint_bg: str


class PartnerOut(BaseModel):
    key: str
    name: str
    url: str
    role_bg: str
    what_they_do_bg: str
    disclosure_bg: str
    good_fit_bg: list[str]


class PartnersOut(BaseModel):
    partners: list[PartnerOut]
    general_note_bg: str


class MarketComparisonOut(BaseModel):
    your_rate_pct: float
    market_rate_pct: float
    market_period: str
    difference_pp: float
    is_above_market: bool
    monthly_difference: float
    remaining_term_difference: float
    verdict_bg: str


class RefinanceOut(BaseModel):
    new_rate_pct: float
    new_monthly_payment: float
    monthly_saving: float
    upfront_cost: float
    break_even_month: int | None
    total_saving_over_term: float
    is_worth_it: bool
    verdict_bg: str


class EarlyRepaymentOut(BaseModel):
    extra_monthly: float
    months_saved: int
    interest_saved: float
    new_term_months: int
    verdict_bg: str


class LoanHealthOut(BaseModel):
    loan_id: int
    label: str
    bank_name: str
    currency: Currency
    principal_amount: float
    remaining_months: int
    current_monthly_payment: float
    market: MarketComparisonOut
    refinance: RefinanceOut
    early_repayment: list[EarlyRepaymentOut]
    refinance_cost_note_bg: str


class SavingsRequest(BaseModel):
    amount: float = Field(gt=0, le=100_000_000)
    use_term_deposit: bool = True


class SavingsOut(BaseModel):
    amount: float
    deposit_rate_pct: float
    deposit_kind_bg: str
    inflation_pct: float
    inflation_period: str
    real_rate_pct: float
    annual_loss: float
    five_year_loss: float
    verdict_bg: str


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int | None
    kind: NotificationKind
    severity: NotificationSeverity
    title_bg: str
    body_bg: str
    action_bg: str | None
    created_at: datetime
    read_at: datetime | None
    emailed_at: datetime | None


class NotificationFeedOut(BaseModel):
    unread_count: int
    email_delivery_enabled: bool
    items: list[NotificationOut]


class PreferencesIn(BaseModel):
    notify_email: bool
    notify_push: bool
    alert_threshold_eur: float = Field(ge=0, le=10_000)
    risk_tolerance: RiskTolerance


class WaitingRequest(BaseModel):
    target_price: float = Field(gt=0, le=10_000_000)
    down_payment_pct: float = Field(default=20, ge=0, le=100)
    saved_now: float = Field(ge=0, le=10_000_000)
    monthly_saving: float = Field(default=0, ge=0, le=100_000)
    # По подразбиране се ползва наблюдаваният ръст, но потребителят може да
    # заложи свой — 14.8% годишно не е устойчиво допускане за дълъг период.
    house_growth_pct: float | None = Field(default=None, ge=-30, le=50)


class WaitingOut(BaseModel):
    target_price: float
    down_payment_pct: float
    saved_now: float
    monthly_saving: float
    house_growth_pct: float
    house_growth_period: str
    house_growth_is_observed: bool
    deposit_rate_pct: float
    needed_now: float
    gap_now: float
    months_to_afford: int | None
    needed_in_year: float
    saved_in_year: float
    gap_in_year: float
    cost_of_one_year: float
    gap_is_widening: bool
    verdict_bg: str
    assumption_note_bg: str


class OfferRequest(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    months: int = Field(ge=6, le=480)
    loan_type: LoanType = LoanType.MORTGAGE
    nominal_rate_pct: float = Field(ge=0, le=100)
    monthly_fee: float = Field(default=0, ge=0, le=10_000)
    upfront_fee: float = Field(default=0, ge=0, le=1_000_000)
    property_insurance_annual_pct: float = Field(default=0, ge=0, le=10)
    life_insurance_annual_pct: float = Field(default=0, ge=0, le=10)


class OfferOut(BaseModel):
    amount: float
    months: int
    nominal_rate_pct: float
    monthly_payment: float
    monthly_fee: float
    monthly_insurance: float
    total_monthly_cost: float
    upfront_fee: float
    offer_aprc_pct: float
    market_aprc_pct: float
    market_period: str
    difference_pp: float
    is_above_market: bool
    monthly_difference: float
    total_difference: float
    hidden_cost_pp: float
    verdict_bg: str
    hidden_cost_note_bg: str

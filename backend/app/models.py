from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Frequency(str, enum.Enum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class SourceSystem(str, enum.Enum):
    ECB = "ECB"
    BUNDESBANK = "BUNDESBANK"
    EUROSTAT = "EUROSTAT"
    US_TREASURY = "US_TREASURY"


class Unit(str, enum.Enum):
    PERCENT_PER_ANNUM = "PERCENT_PER_ANNUM"
    PERCENT_CHANGE = "PERCENT_CHANGE"
    PERCENT_OF_GDP = "PERCENT_OF_GDP"
    MILLION_EUR = "MILLION_EUR"


class LoanType(str, enum.Enum):
    MORTGAGE = "MORTGAGE"
    CONSUMER = "CONSUMER"


class Currency(str, enum.Enum):
    BGN = "BGN"
    EUR = "EUR"


class IndexType(str, enum.Enum):
    EURIBOR_3M = "EURIBOR_3M"
    EURIBOR_6M = "EURIBOR_6M"
    EURIBOR_12M = "EURIBOR_12M"
    BLP = "BLP"
    FIXED = "FIXED"


class RiskTolerance(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class Signal(str, enum.Enum):
    TAKE = "TAKE"
    NEUTRAL = "NEUTRAL"
    WAIT = "WAIT"


class MacroSeries(Base):
    """Регистър на времевите редове, които теглим от публичните API-та."""

    __tablename__ = "macro_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_bg: Mapped[str] = mapped_column(String(255))
    source: Mapped[SourceSystem] = mapped_column(Enum(SourceSystem, native_enum=False, length=32))
    source_ref: Mapped[str] = mapped_column(Text)
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, native_enum=False, length=32))
    unit: Mapped[Unit] = mapped_column(Enum(Unit, native_enum=False, length=32))
    plain_bg: Mapped[str] = mapped_column(Text)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    observations: Mapped[list[MacroObservation]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class MacroObservation(Base):
    __tablename__ = "macro_observation"
    __table_args__ = (
        UniqueConstraint("series_id", "obs_date", name="uq_series_obs_date"),
        Index("ix_macro_obs_series_date", "series_id", "obs_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("macro_series.id", ondelete="CASCADE"), index=True
    )
    obs_date: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Numeric(14, 6))

    series: Mapped[MacroSeries] = relationship(back_populates="observations")


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_push: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_tolerance: Mapped[RiskTolerance] = mapped_column(
        Enum(RiskTolerance, native_enum=False, length=32), default=RiskTolerance.BALANCED
    )
    # Праг в евро, над който потребителят иска да бъде известяван.
    alert_threshold_eur: Mapped[float] = mapped_column(Numeric(10, 2), default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    loans: Mapped[list[UserLoan]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserLoan(Base):
    __tablename__ = "user_loan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    bank_name: Mapped[str] = mapped_column(String(120))
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType, native_enum=False, length=32))
    currency: Mapped[Currency] = mapped_column(Enum(Currency, native_enum=False, length=32))
    principal_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    remaining_months: Mapped[int] = mapped_column(Integer)
    current_interest_rate: Mapped[float] = mapped_column(Numeric(6, 3))
    index_type: Mapped[IndexType] = mapped_column(Enum(IndexType, native_enum=False, length=32))
    # Надбавка над индекса. При FIXED е None.
    margin: Mapped[float | None] = mapped_column(Numeric(6, 3))
    next_reset_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="loans")


class BankOffer(Base):
    """Тарифни условия на банка. Всеки ред задължително носи произход и дата."""

    __tablename__ = "bank_offer"
    __table_args__ = (
        UniqueConstraint("bank_name", "product_name", "currency", name="uq_bank_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(120), index=True)
    product_name: Mapped[str] = mapped_column(String(160))
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType, native_enum=False, length=32))
    currency: Mapped[Currency] = mapped_column(Enum(Currency, native_enum=False, length=32))
    index_type: Mapped[IndexType] = mapped_column(Enum(IndexType, native_enum=False, length=32))
    margin_pct: Mapped[float] = mapped_column(Numeric(6, 3))
    # Ползва се само когато index_type == FIXED.
    fixed_rate_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    arrangement_fee_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    arrangement_fee_fixed: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    monthly_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    property_insurance_annual_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    life_insurance_annual_pct: Mapped[float] = mapped_column(Numeric(6, 3), default=0)
    max_ltv_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    min_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    max_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    max_months: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text)
    rate_effective_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ForecastRun(Base):
    __tablename__ = "forecast_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    target_series_code: Mapped[str] = mapped_column(String(64))
    driver_series_code: Mapped[str] = mapped_column(String(64))
    best_lag_days: Mapped[int] = mapped_column(Integer)
    n_obs: Mapped[int] = mapped_column(Integer)
    r_squared: Mapped[float] = mapped_column(Numeric(8, 5))
    adj_r_squared: Mapped[float] = mapped_column(Numeric(8, 5))
    diagnostics: Mapped[dict] = mapped_column(JSONB)

    points: Mapped[list[ForecastPoint]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ForecastPoint(Base):
    __tablename__ = "forecast_point"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_run.id", ondelete="CASCADE"), index=True
    )
    horizon_days: Mapped[int] = mapped_column(Integer)
    target_date: Mapped[date] = mapped_column(Date)
    predicted_value: Mapped[float] = mapped_column(Numeric(8, 4))
    ci_lower: Mapped[float] = mapped_column(Numeric(8, 4))
    ci_upper: Mapped[float] = mapped_column(Numeric(8, 4))

    run: Mapped[ForecastRun] = relationship(back_populates="points")


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    signal: Mapped[Signal] = mapped_column(Enum(Signal, native_enum=False, length=32))
    real_rate: Mapped[float] = mapped_column(Numeric(6, 3))
    bund_momentum_60d: Mapped[float] = mapped_column(Numeric(6, 3))
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    components: Mapped[dict] = mapped_column(JSONB)


class NewsImpact(str, enum.Enum):
    FAVOURABLE = "FAVOURABLE"
    NEUTRAL = "NEUTRAL"
    UNFAVOURABLE = "UNFAVOURABLE"


class NewsItem(Base):
    """Новина от публичен RSS източник, оценена за влияние върху кредитите."""

    __tablename__ = "news_item"
    __table_args__ = (
        UniqueConstraint("source_code", "guid", name="uq_news_source_guid"),
        Index("ix_news_published", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_code: Mapped[str] = mapped_column(String(40), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    guid: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(5))

    title_original: Mapped[str] = mapped_column(Text)
    title_bg: Mapped[str] = mapped_column(Text)
    summary_bg: Mapped[str | None] = mapped_column(Text)
    was_translated: Mapped[bool] = mapped_column(Boolean, default=False)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # -1.0 = натиск нагоре върху лихвите, +1.0 = натиск надолу.
    sentiment_score: Mapped[float] = mapped_column(Numeric(4, 3))
    impact: Mapped[NewsImpact] = mapped_column(
        Enum(NewsImpact, native_enum=False, length=32)
    )
    wallet_explanation_bg: Mapped[str] = mapped_column(Text)
    matched_terms: Mapped[dict] = mapped_column(JSONB)
    is_bulgaria_related: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class JobStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class JobRun(Base):
    """История на автоматичните задачи, за да е видимо дали работят."""

    __tablename__ = "job_run"
    __table_args__ = (Index("ix_job_run_name_started", "job_name", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=32)
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 3))
    items_ok: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)


class NotificationKind(str, enum.Enum):
    PAYMENT_CHANGE = "PAYMENT_CHANGE"
    RESET_APPROACHING = "RESET_APPROACHING"
    ABOVE_MARKET = "ABOVE_MARKET"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    OPPORTUNITY = "OPPORTUNITY"


class Notification(Base):
    """Известие до потребител.

    `dedupe_key` пази от повтаряне на едно и също съобщение всеки ден —
    приложение, което известява твърде често, се изключва.
    """

    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notification_dedupe"),
        Index("ix_notification_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), index=True
    )
    loan_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_loan.id", ondelete="CASCADE")
    )
    kind: Mapped[NotificationKind] = mapped_column(
        Enum(NotificationKind, native_enum=False, length=32)
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False, length=32)
    )
    dedupe_key: Mapped[str] = mapped_column(String(160))
    title_bg: Mapped[str] = mapped_column(String(200))
    body_bg: Mapped[str] = mapped_column(Text)
    action_bg: Mapped[str | None] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_error: Mapped[str | None] = mapped_column(Text)

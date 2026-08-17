from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import DbSession
from app.ingestion.http import UpstreamError
from app.ingestion import registry
from app.models import Frequency, MacroSeries, NewsItem
from app.news.ingest import aggregate_sentiment
from app.news.translate import translator_available
from app.schemas import (
    AutomationOut,
    FiscalOut,
    JobRunOut,
    PartnerOut,
    PartnersOut,
    FreshnessOut,
    NewsFeedOut,
    NewsFeedSourceOut,
    NewsItemOut,
    SourceProviderOut,
    SourcesOut,
    SourceSeriesOut,
    SpendingOut,
    SpreadPointOut,
)
from app.services import fiscal as fiscal_service
from app.services import spending as spending_service
from app.services.analytics_cache import get_or_compute

router = APIRouter(prefix="/api/v1", tags=["fiscal"])

# Колко може да остарее един ред, преди да го обявим за застоял. Мери се от
# КРАЯ на отчетния период, не от началото му: наблюдение за първото тримесечие
# е закотвено на 1 януари, но реално описва състоянието към 31 март.
MAX_AGE_BY_FREQUENCY = {
    Frequency.DAILY: 10,
    Frequency.MONTHLY: 75,
    Frequency.QUARTERLY: 130,
    Frequency.ANNUAL: 550,
}

PERIOD_LENGTH_DAYS = {
    Frequency.DAILY: 0,
    Frequency.MONTHLY: 30,
    Frequency.QUARTERLY: 91,
    Frequency.ANNUAL: 365,
}


@router.get("/fiscal/overview", response_model=FiscalOut)
def fiscal_overview(db: DbSession) -> FiscalOut:
    snapshot = fiscal_service.build_snapshot(db)

    if snapshot.debt_pct_gdp is None and snapshot.deficit_pct_gdp is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Фискалните редове още не са заредени. Пуснете ingestion.",
        )

    return FiscalOut(
        debt_pct_gdp=snapshot.debt_pct_gdp,
        debt_period=snapshot.debt_period,
        debt_is_quarterly=snapshot.debt_is_quarterly,
        debt_limit_pct=fiscal_service.DEBT_LIMIT_PCT,
        deficit_pct_gdp=snapshot.deficit_pct_gdp,
        deficit_period=snapshot.deficit_period,
        deficit_is_quarterly=snapshot.deficit_is_quarterly,
        deficit_limit_pct=fiscal_service.DEFICIT_LIMIT_PCT,
        exceeds_deficit_limit=snapshot.exceeds_deficit_limit,
        exceeds_debt_limit=snapshot.exceeds_debt_limit,
        spread_latest_bp=snapshot.spread_latest_bp,
        spread_period=snapshot.spread_period,
        spread_status=snapshot.spread_status,
        spread_watch_bp=fiscal_service.SPREAD_WATCH_BP,
        spread_alert_bp=fiscal_service.SPREAD_ALERT_BP,
        spread_history=[
            SpreadPointOut(
                period=point.period,
                bg_yield=point.bg_yield,
                de_yield=point.de_yield,
                spread_bp=point.spread_bp,
            )
            for point in snapshot.spread_history
        ],
        explanation_bg=snapshot.explanation_bg,
    )


@router.get("/fiscal/spending", response_model=SpendingOut)
def government_spending() -> SpendingOut:
    try:
        breakdown = get_or_compute("spending:BG", spending_service.fetch_breakdown)
    except UpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return SpendingOut(
        period=breakdown.period,
        total_pct_gdp=breakdown.total_pct_gdp,
        lines=[line.__dict__ for line in breakdown.lines],
        source_ref=breakdown.source_ref,
        explanation_bg=breakdown.explanation_bg,
    )


@router.get("/news/translated-sentiment", response_model=NewsFeedOut)
def news_feed(
    db: DbSession,
    limit: int = Query(default=40, ge=1, le=200),
    bulgaria_only: bool = Query(default=False),
) -> NewsFeedOut:
    query = select(NewsItem).order_by(NewsItem.published_at.desc())
    if bulgaria_only:
        query = query.where(NewsItem.is_bulgaria_related.is_(True))

    items = db.scalars(query.limit(limit)).all()
    aggregate = aggregate_sentiment(db)

    if aggregate is None:
        label = "Няма ясен сигнал от новините през последния месец."
    elif aggregate <= -0.15:
        label = "Тонът на новините сочи натиск нагоре върху лихвите."
    elif aggregate >= 0.15:
        label = "Тонът на новините сочи натиск надолу върху лихвите."
    else:
        label = "Тонът на новините е смесен, без ясна посока."

    return NewsFeedOut(
        generated_at=datetime.now(timezone.utc),
        aggregate_sentiment=aggregate,
        aggregate_label_bg=label,
        translator_available=translator_available(),
        items=[NewsItemOut.model_validate(item) for item in items],
    )


@router.get("/macro/freshness", response_model=list[FreshnessOut])
def data_freshness(db: DbSession) -> list[FreshnessOut]:
    """Колко стари са данните зад всеки показател.

    Показва се на потребителя, защото официалните източници публикуват с
    различно закъснение и застоял ред би подвел решението за кредит.
    """
    from sqlalchemy import func

    from app.models import MacroObservation

    rows = db.execute(
        select(
            MacroSeries.code,
            MacroSeries.name_bg,
            MacroSeries.frequency,
            MacroSeries.source,
            func.max(MacroObservation.obs_date),
        )
        .outerjoin(MacroObservation, MacroObservation.series_id == MacroSeries.id)
        .group_by(
            MacroSeries.code,
            MacroSeries.name_bg,
            MacroSeries.frequency,
            MacroSeries.source,
        )
        .order_by(MacroSeries.code)
    ).all()

    today = date.today()
    result: list[FreshnessOut] = []
    for code, name_bg, frequency, source, latest in rows:
        allowed = MAX_AGE_BY_FREQUENCY[frequency]
        age = (
            (today - latest).days - PERIOD_LENGTH_DAYS[frequency] if latest else None
        )
        definition = registry.BY_CODE.get(code)
        superseded = definition is not None and definition.superseded_by is not None

        result.append(
            FreshnessOut(
                code=code,
                name_bg=name_bg,
                latest_date=latest,
                age_days=max(0, age) if age is not None else None,
                expected_max_age_days=allowed,
                # Прекратен ред не е застоял — той просто е приключил.
                is_stale=not superseded and (age is None or age > allowed),
                superseded_by=definition.superseded_by if definition else None,
                source=source.value,
            )
        )
    return result


@router.get("/macro/sources", response_model=SourcesOut)
def data_sources(db: DbSession) -> SourcesOut:
    """Пълен списък на публичните източници зад всяко число в приложението."""
    from sqlalchemy import func

    from app.models import MacroObservation
    from app.news.sources import FEEDS
    from app.services.sources_catalog import DISCLAIMER_BG, PROVIDERS

    latest_by_code = dict(
        db.execute(
            select(MacroSeries.code, func.max(MacroObservation.obs_date))
            .outerjoin(MacroObservation, MacroObservation.series_id == MacroSeries.id)
            .group_by(MacroSeries.code)
        ).all()
    )

    providers: list[SourceProviderOut] = []
    for system, provider in PROVIDERS.items():
        series = [
            SourceSeriesOut(
                code=definition.code,
                name_bg=definition.name_bg,
                plain_bg=definition.plain_bg,
                frequency=definition.frequency.value,
                source_ref=definition.source_ref,
                browse_url=definition.browse_url,
                latest_date=latest_by_code.get(definition.code),
                superseded_by=definition.superseded_by,
            )
            for definition in registry.SERIES
            if definition.source is system
        ]
        if not series:
            continue
        providers.append(
            SourceProviderOut(
                key=provider.key,
                name_bg=provider.name_bg,
                description_bg=provider.description_bg,
                portal_url=provider.portal_url,
                api_base_url=provider.api_base_url,
                licence_bg=provider.licence_bg,
                series=series,
            )
        )

    return SourcesOut(
        generated_at=datetime.now(timezone.utc),
        providers=providers,
        news_feeds=[
            NewsFeedSourceOut(
                code=feed.code,
                name_bg=feed.name_bg,
                url=feed.url,
                language=feed.language,
            )
            for feed in FEEDS
        ],
        disclaimer_bg=DISCLAIMER_BG,
    )


SCHEDULE_BG = {
    "ingest_macro": "всеки ден в 07:15 и 18:30",
    "ingest_news": "на всеки 3 часа",
    "refresh_analytics": "всеки ден в 19:00",
    "prune_job_history": "всеки понеделник в 03:30",
    "check_external_links": "всеки понеделник в 04:15",
}


@router.get("/system/automation", response_model=AutomationOut)
def automation_status(db: DbSession) -> AutomationOut:
    """Показва дали автоматичното обновяване на данните работи."""
    from app.models import JobRun

    subquery = (
        select(JobRun.job_name, func.max(JobRun.started_at).label("latest"))
        .group_by(JobRun.job_name)
        .subquery()
    )
    last_runs = list(
        db.scalars(
            select(JobRun)
            .join(
                subquery,
                (JobRun.job_name == subquery.c.job_name)
                & (JobRun.started_at == subquery.c.latest),
            )
            .order_by(JobRun.job_name)
        ).all()
    )

    worker_online = False
    try:
        from app.worker.celery_app import celery_app

        worker_online = bool(celery_app.control.ping(timeout=1.0))
    except Exception:
        worker_online = False

    hint = (
        "Данните се обновяват автоматично по графика вляво."
        if worker_online
        else (
            "Автоматичният процес не е стартиран. Пуснете "
            "`celery -A app.worker.celery_app worker --beat`, за да спрат "
            "ръчните зареждания."
        )
    )

    return AutomationOut(
        generated_at=datetime.now(timezone.utc),
        worker_online=worker_online,
        schedule_bg=SCHEDULE_BG,
        last_runs=[JobRunOut.model_validate(r) for r in last_runs],
        hint_bg=hint,
    )


@router.get("/partners", response_model=PartnersOut)
def partners() -> PartnersOut:
    """Партньори, предлагащи човешка помощ. Не влияят на изчисленията."""
    from app.services.partners import ACTIVE_PARTNERS, GENERAL_NOTE_BG

    return PartnersOut(
        partners=[
            PartnerOut(
                key=p.key,
                name=p.name,
                url=p.url,
                role_bg=p.role_bg,
                what_they_do_bg=p.what_they_do_bg,
                disclosure_bg=p.disclosure_bg,
                good_fit_bg=p.good_fit_bg,
            )
            for p in ACTIVE_PARTNERS
        ],
        general_note_bg=GENERAL_NOTE_BG,
    )

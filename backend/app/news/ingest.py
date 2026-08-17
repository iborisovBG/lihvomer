"""Сваляне, оценка и запис на новините."""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NewsImpact, NewsItem
from app.news.lexicon import mentions_bulgaria, normalise, score_text
from app.news.sources import FEEDS, TOPIC_TERMS, FeedDef
from app.news.translate import translate_to_bg

logger = logging.getLogger(__name__)

# Argos логва всяка стъпка от превода на INFO; това залива изхода.
logging.getLogger("argostranslate").setLevel(logging.WARNING)

MAX_AGE_DAYS = 45
FAVOURABLE_AT = 0.15
UNFAVOURABLE_AT = -0.15
_TAGS = re.compile(r"<[^>]+>")


@dataclass
class NewsIngestResult:
    source_code: str
    seen: int
    kept: int
    written: int
    error: str | None = None


def _clean(raw: str) -> str:
    return html.unescape(_TAGS.sub(" ", raw or "")).strip()


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    return None


def _is_relevant(feed: FeedDef, title: str, summary: str) -> bool:
    if feed.bulgaria_only and not mentions_bulgaria(f"{title} {summary}"):
        return False
    if feed.language != "bg":
        return True

    # Заглавието носи темата на новината; резюмето често изброява несвързани
    # други материали, затова му се доверяваме само като подкрепящ сигнал.
    title_hay = normalise(title)
    if any(term in title_hay for term in TOPIC_TERMS):
        return True

    summary_hay = normalise(summary)
    matches = sum(1 for term in TOPIC_TERMS if term in summary_hay)
    return matches >= 2


def _impact(score: float) -> NewsImpact:
    if score >= FAVOURABLE_AT:
        return NewsImpact.FAVOURABLE
    if score <= UNFAVOURABLE_AT:
        return NewsImpact.UNFAVOURABLE
    return NewsImpact.NEUTRAL


def _wallet_explanation(score: float, terms: dict, bulgaria: bool) -> str:
    """Какво означава новината за вноската — на разбираем български."""
    impact = _impact(score)
    scope = "Пряко засяга България. " if bulgaria else ""

    if impact is NewsImpact.UNFAVOURABLE:
        body = (
            "Тонът на съобщението сочи натиск нагоре върху лихвите. Ако "
            "кредитът ви е с плаваща лихва, подобни новини обикновено се "
            "усещат във вноската след няколко месеца, а не веднага."
        )
    elif impact is NewsImpact.FAVOURABLE:
        body = (
            "Тонът сочи натиск надолу върху лихвите. За кредит с плаваща "
            "лихва това е добра новина, но ефектът върху вноската идва със "
            "закъснение от няколко месеца."
        )
    else:
        body = (
            "Новината няма ясна посока за лихвите. Отбелязваме я, защото "
            "касае темите, които движат вноската ви."
        )

    detected = terms.get("hawkish") or terms.get("dovish")
    hint = (
        f" Разпознати изрази: {', '.join(detected[:3])}." if detected else ""
    )
    return scope + body + hint


# Някои издания отказват заявки без разпознаваем браузър. Представяме се
# честно: име на приложението и адрес, на който да ни намерят.
USER_AGENT = (
    "Mozilla/5.0 (compatible; Lihvomer/1.0; +https://xbotics.ai) "
    "feedparser"
)


def ingest_feed(db: Session, feed: FeedDef) -> NewsIngestResult:
    try:
        parsed = feedparser.parse(feed.url, agent=USER_AGENT)
    except Exception as exc:
        return NewsIngestResult(feed.code, 0, 0, 0, f"{type(exc).__name__}: {exc}")

    if getattr(parsed, "status", None) not in (None, 200, 301, 302):
        return NewsIngestResult(
            feed.code, 0, 0, 0, f"HTTP {parsed.status} от {feed.url}"
        )
    if not parsed.entries:
        return NewsIngestResult(feed.code, 0, 0, 0, "Фийдът не върна записи.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    seen = kept = written = 0

    for entry in parsed.entries:
        seen += 1
        title = _clean(entry.get("title", ""))
        summary = _clean(entry.get("summary", ""))
        if not title:
            continue

        published = _published(entry)
        if published is None or published < cutoff:
            continue

        if not _is_relevant(feed, title, summary):
            continue
        combined = f"{title} {summary}"

        kept += 1
        guid = (entry.get("id") or entry.get("link") or title)[:500]

        exists = db.scalar(
            select(NewsItem.id).where(
                NewsItem.source_code == feed.code, NewsItem.guid == guid
            )
        )
        if exists:
            continue

        score, terms = score_text(combined)
        bulgaria = mentions_bulgaria(combined)

        title_bg, translated = translate_to_bg(title, feed.language)
        summary_bg = None
        if summary:
            summary_bg, _ = translate_to_bg(summary[:600], feed.language)

        db.add(
            NewsItem(
                source_code=feed.code,
                source_name=feed.name_bg,
                guid=guid,
                url=entry.get("link", ""),
                language=feed.language,
                title_original=title,
                title_bg=title_bg,
                summary_bg=summary_bg,
                was_translated=translated,
                published_at=published,
                sentiment_score=score,
                impact=_impact(score),
                wallet_explanation_bg=_wallet_explanation(score, terms, bulgaria),
                matched_terms=terms,
                is_bulgaria_related=bulgaria,
            )
        )
        written += 1

    db.commit()
    return NewsIngestResult(feed.code, seen, kept, written)


def ingest_all_news(db: Session) -> list[NewsIngestResult]:
    return [ingest_feed(db, feed) for feed in FEEDS]


def aggregate_sentiment(db: Session, days: int = 30) -> float | None:
    """Среднопретеглен тон на скорошните новини за Mortgage Timing Score.

    По-новите новини тежат повече, а тези за България — двойно, защото
    касаят пряко българските лихви.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(
            NewsItem.sentiment_score, NewsItem.published_at, NewsItem.is_bulgaria_related
        ).where(NewsItem.published_at >= cutoff)
    ).all()

    scored = [(float(s), p, b) for s, p, b in rows if float(s) != 0.0]
    if not scored:
        return None

    now = datetime.now(timezone.utc)
    weighted = 0.0
    total_weight = 0.0
    for score, published, bulgaria in scored:
        age_days = max(0.0, (now - published).total_seconds() / 86400)
        weight = (1.0 - age_days / days) * (2.0 if bulgaria else 1.0)
        weighted += score * weight
        total_weight += weight

    return round(weighted / total_weight, 3) if total_weight else None

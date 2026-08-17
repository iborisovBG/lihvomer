"""Преоценка на вече заредените новини след промяна в речника.

    .venv/bin/python -m scripts.rescore_news
"""
import logging
from sqlalchemy import select
from app.db import SessionLocal
from app.models import NewsItem
from app.news.ingest import _impact, _wallet_explanation
from app.news.lexicon import mentions_bulgaria, score_text


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    changed = 0
    with SessionLocal() as db:
        items = db.scalars(select(NewsItem)).all()
        for item in items:
            text = f"{item.title_original} {item.summary_bg or ''}"
            score, terms = score_text(text)
            bulgaria = mentions_bulgaria(text)
            if float(item.sentiment_score) != score:
                changed += 1
            item.sentiment_score = score
            item.impact = _impact(score)
            item.matched_terms = terms
            item.is_bulgaria_related = bulgaria
            item.wallet_explanation_bg = _wallet_explanation(score, terms, bulgaria)
        db.commit()
        print(f"преоценени {len(items)} новини, променени {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Сваляне на новините: .venv/bin/python -m scripts.ingest_news"""
import logging
from app.db import SessionLocal
from app.news.ingest import ingest_all_news, aggregate_sentiment
from app.news.translate import translator_available


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    print("превод EN→BG:", "наличен" if translator_available() else "ИЗКЛЮЧЕН")
    with SessionLocal() as db:
        results = ingest_all_news(db)
        for r in results:
            if r.error:
                print(f"FAIL {r.source_code:<10} {r.error}")
            else:
                print(f"OK   {r.source_code:<10} видени {r.seen:>3}, по темата {r.kept:>3}, нови {r.written:>3}")
        agg = aggregate_sentiment(db)
        print(f"\nагрегиран тон за 30 дни: {agg if agg is not None else 'няма сигнал'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

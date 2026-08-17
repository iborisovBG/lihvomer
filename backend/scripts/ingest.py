"""Ръчно пускане на ingestion: .venv/bin/python -m scripts.ingest [CODE ...]"""

from __future__ import annotations

import logging
import sys

from app.db import Base, SessionLocal, engine
from app.ingestion.runner import ingest_all
from app.models import *  # noqa: F401,F403  регистрира таблиците в metadata


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    Base.metadata.create_all(engine)

    codes = sys.argv[1:] or None
    with SessionLocal() as db:
        results = ingest_all(db, codes)

    width = max(len(r.code) for r in results)
    failures = 0
    for result in results:
        if result.ok:
            print(
                f"OK   {result.code:<{width}}  {result.fetched:>5} набл.  "
                f"последно {result.latest_date} = {result.latest_value}"
            )
        else:
            failures += 1
            print(f"FAIL {result.code:<{width}}  {result.error}")

    print(f"\n{len(results) - failures}/{len(results)} серии заредени успешно.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

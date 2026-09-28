"""Check that DATABASE_URL is reachable and the tables exist.

Run with:  python -m app.check_db
"""

import sys

from sqlalchemy import func, inspect, select
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import SessionLocal, engine, init_db
from app.models import Posting


def main() -> None:
    url = make_url(get_settings().database_url)
    print(f"Connecting to {url.drivername}://{url.host or ''}/{url.database or ''}")
    try:
        init_db()
        tables = sorted(inspect(engine).get_table_names())
        with SessionLocal() as db:
            count = db.scalar(select(func.count()).select_from(Posting))
    except Exception as exc:  # noqa: BLE001 - report any connection failure plainly
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: tables={tables}, postings={count}")


if __name__ == "__main__":
    main()

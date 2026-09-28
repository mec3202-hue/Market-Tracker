"""Export the data the frontend needs as static JSON, for hosting without an API.

Run with:  python -m app.export_static --out ../frontend/public/data

Writes:
  meta.json      the same payload as GET /filters, plus generated_at
  skills.json    the skill catalog (GET /skills)
  postings.json  recent postings in the GET /postings item shape

The frontend's static mode (VITE_STATIC_DATA=1) computes trending skills,
salaries, pagination, and the skill gap from these files in the browser.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import Posting
from app.routers.deps import since
from app.routers.postings import _to_out, filters
from app.routers.skills import list_skills

# Trending compares two back-to-back windows of up to 90 days each.
DEFAULT_DAYS = 180


def export(out_dir: Path, days: int = DEFAULT_DAYS) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        meta = filters(db).model_dump(mode="json")
        rows = db.scalars(
            select(Posting)
            .where(Posting.posted_at >= since(days))
            .order_by(Posting.posted_at.desc(), Posting.id)
        ).all()
        postings = [_to_out(p).model_dump(mode="json") for p in rows]

    meta["generated_at"] = datetime.now(UTC).isoformat()
    skills = [s.model_dump() for s in list_skills()]
    for name, payload in (("meta", meta), ("skills", skills), ("postings", postings)):
        with open(out_dir / f"{name}.json", "w") as f:
            json.dump(payload, f, separators=(",", ":"))
    return len(postings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()
    count = export(args.out, args.days)
    print(f"Exported {count} postings to {args.out}")


if __name__ == "__main__":
    main()

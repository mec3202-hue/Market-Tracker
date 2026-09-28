"""Export the data the frontend needs as static JSON, for hosting without an API.

Run with:  python -m app.export_static --out ../frontend/public/data

Writes:
  meta.json      the same payload as GET /filters, plus generated_at
  skills.json    the skill catalog (GET /skills)
  facts.json     every posting from the last --days, in a compact form holding
                 just what the charts need (dates, role, place, work setting,
                 salary, skills)
  postings.json  the newest --max-detail postings in the GET /postings item
                 shape, for the browsable list

The frontend's static mode (VITE_STATIC_DATA=1) computes trending skills,
salaries, locations, and the skill gap from these files in the browser.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import noload

from app.db import SessionLocal, init_db
from app.models import Posting, PostingSkill
from app.routers.deps import since
from app.routers.postings import _to_out, filters
from app.routers.skills import list_skills

# Trending compares two back-to-back windows of up to 90 days each.
DEFAULT_DAYS = 180
DEFAULT_MAX_DETAIL = 3000

# Column order of each row in facts.json; the frontend reads the same order.
FACT_FIELDS = [
    "posted",  # unix seconds
    "role",  # index into dims.roles
    "state",  # index into dims.states, or -1
    "city",  # index into dims.cities, or -1
    "work_mode",  # index into dims.work_modes, or -1
    "salary_min",
    "salary_max",
    "salary_is_predicted",  # 0 / 1
    "skills",  # list of indexes into dims.skills
]


class _Dim:
    """Assigns each distinct value a small integer index."""

    def __init__(self) -> None:
        self.values: list[str] = []
        self._index: dict[str, int] = {}

    def __call__(self, value: str | None) -> int:
        if value is None:
            return -1
        if value not in self._index:
            self._index[value] = len(self.values)
            self.values.append(value)
        return self._index[value]


def _num(value: float | None) -> float | int | None:
    return int(value) if value is not None and float(value).is_integer() else value


def build_facts(db, start: datetime) -> dict:
    dims = {k: _Dim() for k in ("roles", "states", "cities", "work_modes", "skills")}
    skills_by_posting: dict[str, list[int]] = {}
    for pid, skill in db.execute(
        select(PostingSkill.posting_id, PostingSkill.skill)
        .join(Posting, Posting.id == PostingSkill.posting_id)
        .where(Posting.posted_at >= start)
        .order_by(PostingSkill.posting_id, PostingSkill.skill)
    ):
        skills_by_posting.setdefault(pid, []).append(dims["skills"](skill))

    rows = []
    for p in db.execute(
        select(
            Posting.id,
            Posting.posted_at,
            Posting.role,
            Posting.state,
            Posting.city,
            Posting.work_mode,
            Posting.salary_min,
            Posting.salary_max,
            Posting.salary_is_predicted,
        )
        .where(Posting.posted_at >= start)
        .order_by(Posting.posted_at.desc(), Posting.id)
    ):
        posted = p.posted_at if p.posted_at.tzinfo else p.posted_at.replace(tzinfo=UTC)
        rows.append(
            [
                int(posted.timestamp()),
                dims["roles"](p.role),
                dims["states"](p.state),
                dims["cities"](p.city),
                dims["work_modes"](p.work_mode),
                _num(p.salary_min),
                _num(p.salary_max),
                int(bool(p.salary_is_predicted)),
                skills_by_posting.get(p.id, []),
            ]
        )
    return {
        "fields": FACT_FIELDS,
        "dims": {k: d.values for k, d in dims.items()},
        "rows": rows,
    }


def export(
    out_dir: Path, days: int = DEFAULT_DAYS, max_detail: int = DEFAULT_MAX_DETAIL
) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    start = since(days)
    with SessionLocal() as db:
        meta = filters(db).model_dump(mode="json")
        facts = build_facts(db, start)
        recent = db.scalars(
            select(Posting)
            .options(noload(Posting.skills))
            .where(Posting.posted_at >= start)
            .order_by(Posting.posted_at.desc(), Posting.id)
            .limit(max_detail)
        ).all()
        # Load skills for just these postings in one query.
        ids = [p.id for p in recent]
        skills: dict[str, list[str]] = {}
        for pid, skill in db.execute(
            select(PostingSkill.posting_id, PostingSkill.skill).where(
                PostingSkill.posting_id.in_(ids)
            )
        ):
            skills.setdefault(pid, []).append(skill)
        postings = []
        for p in recent:
            item = _to_out(p).model_dump(mode="json")
            item["skills"] = sorted(skills.get(p.id, []))
            postings.append(item)

    meta["generated_at"] = datetime.now(UTC).isoformat()
    meta["detail_limit"] = max_detail
    catalog = [s.model_dump() for s in list_skills()]
    for name, payload in (
        ("meta", meta),
        ("skills", catalog),
        ("facts", facts),
        ("postings", postings),
    ):
        with open(out_dir / f"{name}.json", "w") as f:
            json.dump(payload, f, separators=(",", ":"))
    return len(facts["rows"]), len(postings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--max-detail", type=int, default=DEFAULT_MAX_DETAIL)
    args = parser.parse_args()
    facts, detail = export(args.out, args.days, args.max_detail)
    print(f"Exported {facts} postings for charts and {detail} for the postings list to {args.out}")


if __name__ == "__main__":
    main()

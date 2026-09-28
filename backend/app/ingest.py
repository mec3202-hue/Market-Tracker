"""Daily ingest: pull postings from Adzuna, extract skills, store new ones.

Run with:  python -m app.ingest [--pages 5] [--max-days-old 1]
"""

import argparse
import logging
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import SessionLocal, init_db
from app.models import Posting, PostingSkill
from app.skills import classify_role, extract_skills

log = logging.getLogger("ingest")

RESULTS_PER_PAGE = 50


class AdzunaClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None):
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            raise RuntimeError("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set to ingest postings")
        self.settings = settings
        self.http = http or httpx.Client(timeout=30)

    def search(self, what: str, page: int, max_days_old: int) -> list[dict]:
        url = f"{self.settings.adzuna_base_url}/{self.settings.adzuna_country}/search/{page}"
        params = {
            "app_id": self.settings.adzuna_app_id,
            "app_key": self.settings.adzuna_app_key,
            "what_phrase": what,
            "results_per_page": RESULTS_PER_PAGE,
            "max_days_old": max_days_old,
            "sort_by": "date",
        }
        for attempt in range(3):
            resp = self.http.get(url, params=params, headers={"Accept": "application/json"})
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 2 ** (attempt + 1)
                log.warning("Adzuna returned %s, retrying in %ss", resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("results", [])
        resp.raise_for_status()
        return []

    def iter_postings(self, what: str, pages: int, max_days_old: int) -> Iterator[dict]:
        for page in range(1, pages + 1):
            results = self.search(what, page, max_days_old)
            yield from results
            if len(results) < RESULTS_PER_PAGE:
                break


@dataclass
class ParsedPosting:
    posting: Posting
    skills: set[str]


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true"}


def parse_result(raw: dict, search_term: str) -> ParsedPosting:
    """Map one Adzuna search result onto a Posting (not yet added to a session)."""
    location = raw.get("location") or {}
    # area looks like ["US", "California", "Los Angeles County", "Los Angeles"]
    area = location.get("area") or []
    state = area[1] if len(area) > 1 else None
    city = area[-1] if len(area) > 2 else None
    title = (raw.get("title") or "").strip()
    description = raw.get("description") or ""

    posting = Posting(
        id=str(raw["id"]),
        title=title[:300],
        company=((raw.get("company") or {}).get("display_name") or None),
        location=location.get("display_name"),
        city=city,
        state=state,
        role=classify_role(title, fallback=search_term),
        salary_min=raw.get("salary_min"),
        salary_max=raw.get("salary_max"),
        salary_is_predicted=_parse_bool(raw.get("salary_is_predicted", 0)),
        description=description,
        url=raw.get("redirect_url"),
        posted_at=_parse_datetime(raw.get("created")),
    )
    return ParsedPosting(posting, extract_skills(f"{title}\n{description}"))


def store_postings(db: Session, parsed: Iterable[ParsedPosting]) -> int:
    """Insert postings whose IDs aren't stored yet. Returns the number inserted."""
    batch: dict[str, ParsedPosting] = {}
    for item in parsed:
        batch.setdefault(item.posting.id, item)  # dedupe within this run
    if not batch:
        return 0

    existing = set(db.scalars(select(Posting.id).where(Posting.id.in_(batch))))
    new = [item for pid, item in batch.items() if pid not in existing]
    for item in new:
        item.posting.skills = [PostingSkill(skill=s) for s in sorted(item.skills)]
        db.add(item.posting)
    db.commit()
    return len(new)


def run(pages: int, max_days_old: int, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    client = AdzunaClient(settings)
    init_db()
    total = 0
    with SessionLocal() as db:
        for term in settings.search_terms:
            parsed = [
                parse_result(r, term) for r in client.iter_postings(term, pages, max_days_old)
            ]
            inserted = store_postings(db, parsed)
            log.info("%-20s fetched=%-4d new=%d", term, len(parsed), inserted)
            total += inserted
    log.info("Done: %d new postings", total)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=5, help="pages per search term (50/page)")
    parser.add_argument("--max-days-old", type=int, default=2)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.pages, args.max_days_old)


if __name__ == "__main__":
    main()

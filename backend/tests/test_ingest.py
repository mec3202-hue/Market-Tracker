import httpx
import pytest
from sqlalchemy import func, select

from app.config import Settings
from app.ingest import AdzunaClient, parse_result, store_postings
from app.models import Posting, PostingSkill

RAW = {
    "id": "4812345678",
    "title": "Senior Analytics Engineer",
    "company": {"display_name": "Acme Corp"},
    "location": {
        "display_name": "Austin, Travis County",
        "area": ["US", "Texas", "Travis County", "Austin"],
    },
    "salary_min": 120000,
    "salary_max": 150000,
    "salary_is_predicted": "0",
    "description": "Own our dbt project on Snowflake. Strong SQL and Python required. Remote.",
    "redirect_url": "https://www.adzuna.com/details/4812345678",
    "created": "2026-09-27T14:03:11Z",
}


def test_parse_result():
    parsed = parse_result(RAW, "data analyst")
    p = parsed.posting
    assert p.id == "4812345678"
    assert p.company == "Acme Corp"
    assert (p.city, p.state) == ("Austin", "Texas")
    assert p.role == "Analytics Engineer"  # title beats the search term
    assert p.work_mode == "remote"
    assert (p.salary_min, p.salary_max, p.salary_is_predicted) == (120000, 150000, False)
    assert p.posted_at.isoformat() == "2026-09-27T14:03:11+00:00"
    assert parsed.skills == {"dbt", "Snowflake", "SQL", "Python"}


def test_parse_result_handles_missing_fields():
    parsed = parse_result(
        {"id": 7, "title": "Associate", "location": {"area": ["US"]}}, "marketing analyst"
    )
    p = parsed.posting
    assert p.id == "7"
    assert p.role == "Marketing Analyst"
    assert p.city is None and p.state is None
    assert p.company is None
    assert p.salary_is_predicted is False
    assert parsed.skills == set()


def test_store_postings_dedupes_within_and_across_runs(db):
    first = [parse_result(RAW, "data analyst"), parse_result(RAW, "analytics engineer")]
    assert store_postings(db, first) == 1

    again = [parse_result(RAW, "data analyst"), parse_result({**RAW, "id": "999"}, "data analyst")]
    assert store_postings(db, again) == 1

    assert db.scalar(select(func.count()).select_from(Posting)) == 2
    skills = set(db.scalars(select(PostingSkill.skill).where(PostingSkill.posting_id == "999")))
    assert skills == {"dbt", "Snowflake", "SQL", "Python"}


def test_adzuna_client_pages_until_short_page():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.path.rsplit("/", 1)[1])
        calls.append((page, dict(request.url.params)))
        count = 50 if page == 1 else 3
        return httpx.Response(200, json={"results": [{"id": f"{page}-{i}"} for i in range(count)]})

    settings = Settings(adzuna_app_id="id", adzuna_app_key="key")
    client = AdzunaClient(
        settings, http=httpx.Client(transport=httpx.MockTransport(handler)), min_interval=0
    )
    results = list(client.iter_postings("data analyst", pages=5, max_days_old=1))

    assert len(results) == 53
    assert client.requests_made == 2
    assert [page for page, _ in calls] == [1, 2]
    assert calls[0][1]["what_phrase"] == "data analyst"
    assert calls[0][1]["app_id"] == "id"


def test_adzuna_client_requires_credentials():
    with pytest.raises(RuntimeError):
        AdzunaClient(Settings(adzuna_app_id="", adzuna_app_key=""))


def test_settings_normalize_postgres_url_and_csv():
    s = Settings(
        database_url="postgres://u:p@host/db?sslmode=require",
        search_terms="data analyst, bi analyst",
        cors_origins="https://a.example,https://b.example",
    )
    assert s.database_url == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert s.search_terms == ["data analyst", "bi analyst"]
    assert s.cors_origins == ["https://a.example", "https://b.example"]


def test_migration_adds_and_backfills_work_mode(tmp_path):
    """A database created before work_mode existed gets the column and backfilled values."""
    from sqlalchemy import text

    from app.db import init_db, make_engine

    engine = make_engine(f"sqlite:///{tmp_path}/old.db")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE postings (id VARCHAR(64) PRIMARY KEY, title VARCHAR(300),"
                " company VARCHAR(300), location VARCHAR(300), city VARCHAR(120),"
                " state VARCHAR(120), role VARCHAR(60), salary_min FLOAT, salary_max FLOAT,"
                " salary_is_predicted BOOLEAN, description TEXT, url VARCHAR(1000),"
                " posted_at DATETIME, ingested_at DATETIME)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO postings (id, title, description, role, posted_at)"
                " VALUES ('a', 'Remote Data Analyst', '', 'Data Analyst', '2026-09-01'),"
                " ('b', 'Data Analyst', 'Hybrid in Austin', 'Data Analyst', '2026-09-01')"
            )
        )

    init_db(engine)
    init_db(engine)  # idempotent

    with engine.connect() as conn:
        rows = dict(conn.execute(text("SELECT id, work_mode FROM postings")).all())
    assert rows == {"a": "remote", "b": "hybrid"}

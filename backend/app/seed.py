"""Load synthetic demo postings so the app can be explored without an Adzuna key.

Run with:  python -m app.seed [--count 600] [--reset]

Every seeded posting has an ID starting with "demo-" so it can be told apart
from (and removed without touching) real ingested data.
"""

import argparse
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.db import SessionLocal, init_db
from app.ingest import ParsedPosting, store_postings
from app.models import Posting
from app.skills import classify_role, extract_skills

CITIES = [
    ("New York", "New York", 1.18),
    ("San Francisco", "California", 1.25),
    ("Seattle", "Washington", 1.15),
    ("Austin", "Texas", 1.0),
    ("Chicago", "Illinois", 1.0),
    ("Boston", "Massachusetts", 1.1),
    ("Atlanta", "Georgia", 0.93),
    ("Denver", "Colorado", 0.97),
]
ROLES = {
    "Data Analyst": (72_000, ["SQL", "Excel", "Tableau", "Python", "Power BI", "Statistics"]),
    "Marketing Analyst": (68_000, ["Google Analytics", "Excel", "SQL", "A/B Testing", "Tableau"]),
    "Business Analyst": (78_000, ["Excel", "SQL", "Jira", "Power BI", "Salesforce"]),
    "Analytics Engineer": (118_000, ["SQL", "dbt", "Snowflake", "Python", "Git", "Airflow"]),
    "BI Analyst": (85_000, ["Power BI", "SQL", "Tableau", "Data Modeling", "Excel"]),
}
EXTRAS = [
    "Looker",
    "BigQuery",
    "AWS",
    "R",
    "Databricks",
    "Machine Learning",
    "Forecasting",
    "pandas",
]
COMPANIES = [
    "Northwind",
    "Acme Analytics",
    "Globex",
    "Initech",
    "Umbrella Health",
    "Hooli",
    "Vandelay",
]


def demo_postings(count: int, rng: random.Random) -> list[ParsedPosting]:
    now = datetime.now(UTC)
    out = []
    for i in range(count):
        role = rng.choice(list(ROLES))
        base_salary, core = ROLES[role]
        city, state, multiplier = rng.choice(CITIES)
        age_days = rng.uniform(0, 90)
        # dbt and Snowflake get steadily more common over the period, so the
        # trending view has something to show.
        recency = 1 - age_days / 90
        skills = [s for s in core if rng.random() < 0.75]
        skills += [s for s in EXTRAS if rng.random() < 0.12]
        if "dbt" not in skills and rng.random() < 0.35 * recency:
            skills.append("dbt")
        if "Snowflake" not in skills and rng.random() < 0.3 * recency:
            skills.append("Snowflake")

        seniority = rng.choice(["", "", "Senior ", "Junior "])
        title = f"{seniority}{role}"
        description = f"We are hiring a {title.lower()}. Required: {', '.join(skills)}."
        mid = (
            base_salary
            * multiplier
            * (1.25 if seniority == "Senior " else 0.85 if seniority else 1)
        )
        mid *= rng.uniform(0.9, 1.1)
        has_salary = rng.random() < 0.8

        posting = Posting(
            id=f"demo-{i}",
            title=title,
            company=rng.choice(COMPANIES),
            location=f"{city}, {state}",
            city=city,
            state=state,
            role=classify_role(title),
            salary_min=round(mid * 0.9, -3) if has_salary else None,
            salary_max=round(mid * 1.1, -3) if has_salary else None,
            salary_is_predicted=False,
            description=description,
            url=None,
            posted_at=now - timedelta(days=age_days),
        )
        out.append(ParsedPosting(posting, extract_skills(f"{title}\n{description}")))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--reset", action="store_true", help="delete existing demo postings first")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        if args.reset:
            db.execute(delete(Posting).where(Posting.id.like("demo-%")))
            db.commit()
        inserted = store_postings(db, demo_postings(args.count, random.Random(args.seed)))
    print(f"Inserted {inserted} demo postings")


if __name__ == "__main__":
    main()

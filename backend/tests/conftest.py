import os
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

# CI points TEST_DATABASE_URL at a real Postgres service; locally the tests use
# a throwaway SQLite file. Set before importing the app so its global engine
# never touches a real database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/market_tracker_test.db"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import Base, get_db, make_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Posting, PostingSkill  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    engine = make_engine(get_settings().database_url)
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def add_posting(db: Session) -> Callable[..., Posting]:
    counter = iter(range(1_000_000))

    def _add(
        *,
        skills: list[str] = (),
        role: str = "Data Analyst",
        city: str | None = "Austin",
        days_ago: float = 1,
        salary: tuple[float | None, float | None] = (None, None),
        predicted: bool = False,
        title: str | None = None,
    ) -> Posting:
        n = next(counter)
        posting = Posting(
            id=f"t-{n}",
            title=title or f"{role} {n}",
            company="Acme",
            location=f"{city}, Somewhere" if city else None,
            city=city,
            state="Somewhere",
            role=role,
            salary_min=salary[0],
            salary_max=salary[1],
            salary_is_predicted=predicted,
            description=" ".join(skills),
            posted_at=datetime.now(UTC) - timedelta(days=days_ago),
            skills=[PostingSkill(skill=s) for s in skills],
        )
        db.add(posting)
        db.commit()
        return posting

    return _add

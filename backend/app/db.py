from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(bind: Engine | None = None) -> None:
    from app import models  # noqa: F401  (registers tables on Base.metadata)

    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    _migrate(bind)


def _migrate(bind: Engine) -> None:
    """Bring databases created by earlier versions up to date.

    create_all() only creates missing tables, so columns added later are
    added here, and existing rows are backfilled.
    """
    from app.models import Posting
    from app.skills import detect_work_mode

    inspector = inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("postings")}
    indexes = {i["name"] for i in inspector.get_indexes("postings")}
    with bind.begin() as conn:
        if "work_mode" not in columns:
            conn.execute(text("ALTER TABLE postings ADD COLUMN work_mode VARCHAR(10)"))
        for column in ("work_mode", "state"):
            name = f"ix_postings_{column}"
            if name not in indexes:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON postings ({column})"))

        rows = conn.execute(
            select(Posting.id, Posting.title, Posting.location, Posting.description).where(
                Posting.work_mode.is_(None)
            )
        ).all()
        for pid, title, location, description in rows:
            conn.execute(
                update(Posting)
                .where(Posting.id == pid)
                .values(work_mode=detect_work_mode(title, location, description))
            )


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

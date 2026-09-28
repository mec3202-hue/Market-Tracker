from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Posting(Base):
    __tablename__ = "postings"

    # Adzuna's posting ID; the primary key is what makes ingest idempotent.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(60), index=True)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_is_predicted: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str | None] = mapped_column(String(1000))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    skills: Mapped[list["PostingSkill"]] = relationship(
        back_populates="posting", cascade="all, delete-orphan", lazy="selectin"
    )


class PostingSkill(Base):
    __tablename__ = "posting_skills"

    posting_id: Mapped[str] = mapped_column(
        ForeignKey("postings.id", ondelete="CASCADE"), primary_key=True
    )
    skill: Mapped[str] = mapped_column(String(60), primary_key=True)

    posting: Mapped[Posting] = relationship(back_populates="skills")

    __table_args__ = (Index("ix_posting_skills_skill", "skill"),)

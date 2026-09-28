import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting, PostingSkill
from app.routers.deps import validate_role, validate_skill
from app.schemas import FiltersResponse, PostingOut, PostingPage
from app.skills import ROLE_NAMES

router = APIRouter(tags=["postings"])

SNIPPET_CHARS = 280


def _to_out(p: Posting) -> PostingOut:
    desc = " ".join(p.description.split())
    snippet = desc if len(desc) <= SNIPPET_CHARS else desc[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
    return PostingOut(
        id=p.id,
        title=p.title,
        company=p.company,
        location=p.location,
        city=p.city,
        role=p.role,
        salary_min=p.salary_min,
        salary_max=p.salary_max,
        salary_is_predicted=p.salary_is_predicted,
        url=p.url,
        posted_at=p.posted_at,
        skills=sorted(s.skill for s in p.skills),
        snippet=snippet,
    )


@router.get("/postings", response_model=PostingPage)
def list_postings(
    skill: str | None = Query(None, max_length=60),
    role: str | None = Query(None, max_length=60),
    city: str | None = Query(None, min_length=1, max_length=120),
    q: str | None = Query(None, min_length=2, max_length=100, description="Search in titles"),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PostingPage:
    """Newest postings first, filtered by skill, role, city, and title text."""
    skill = validate_skill(skill)
    role = validate_role(role)

    stmt = select(Posting)
    if skill:
        stmt = stmt.where(
            Posting.id.in_(select(PostingSkill.posting_id).where(PostingSkill.skill == skill))
        )
    if role:
        stmt = stmt.where(Posting.role == role)
    if city:
        stmt = stmt.where(func.lower(Posting.city) == city.strip().lower())
    if q:
        stmt = stmt.where(func.lower(Posting.title).contains(q.strip().lower(), autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Posting.posted_at.desc(), Posting.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PostingPage(
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
        items=[_to_out(p) for p in rows],
    )


@router.get("/filters", response_model=FiltersResponse)
def filters(db: Session = Depends(get_db)) -> FiltersResponse:
    """Values for the frontend's dropdowns, plus freshness info."""
    present_roles = set(db.scalars(select(Posting.role).distinct()))
    cities = db.scalars(
        select(Posting.city)
        .where(Posting.city.is_not(None))
        .group_by(Posting.city)
        .order_by(func.count().desc(), Posting.city)
        .limit(40)
    ).all()
    return FiltersResponse(
        roles=[r for r in ROLE_NAMES if r in present_roles]
        + sorted(present_roles - set(ROLE_NAMES)),
        cities=list(cities),
        total_postings=db.scalar(select(func.count()).select_from(Posting)) or 0,
        last_ingested_at=db.scalar(select(func.max(Posting.ingested_at))),
    )

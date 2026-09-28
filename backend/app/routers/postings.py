import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting, PostingSkill
from app.routers.deps import Scope, scope_params, validate_skill
from app.schemas import CityOption, FiltersResponse, PostingOut, PostingPage
from app.skills import ROLE_NAMES

router = APIRouter(tags=["postings"])

SNIPPET_CHARS = 280
MAX_CITIES = 150


def _to_out(p: Posting) -> PostingOut:
    desc = " ".join(p.description.split())
    snippet = desc if len(desc) <= SNIPPET_CHARS else desc[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
    return PostingOut(
        id=p.id,
        title=p.title,
        company=p.company,
        location=p.location,
        city=p.city,
        state=p.state,
        role=p.role,
        work_mode=p.work_mode,
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
    q: str | None = Query(None, min_length=2, max_length=100, description="Search in titles"),
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(20, ge=1, le=100),
    scope: Scope = Depends(scope_params),
    db: Session = Depends(get_db),
) -> PostingPage:
    """Newest postings first, filtered by skill, title text, and the shared scope
    (role, state, city, work setting)."""
    skill = validate_skill(skill)

    stmt = select(Posting).where(*scope.conditions())
    if skill:
        stmt = stmt.where(
            Posting.id.in_(select(PostingSkill.posting_id).where(PostingSkill.skill == skill))
        )
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
    states = db.scalars(
        select(Posting.state)
        .where(Posting.state.is_not(None))
        .group_by(Posting.state)
        .order_by(Posting.state)
    ).all()
    cities = db.execute(
        select(Posting.city, Posting.state)
        .where(Posting.city.is_not(None))
        .group_by(Posting.city, Posting.state)
        .order_by(func.count().desc(), Posting.city)
        .limit(MAX_CITIES)
    ).all()
    return FiltersResponse(
        roles=[r for r in ROLE_NAMES if r in present_roles]
        + sorted(present_roles - set(ROLE_NAMES)),
        states=list(states),
        cities=[CityOption(city=c, state=s) for c, s in cities],
        total_postings=db.scalar(select(func.count()).select_from(Posting)) or 0,
        last_ingested_at=db.scalar(select(func.max(Posting.ingested_at))),
    )

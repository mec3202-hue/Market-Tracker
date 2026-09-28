from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting, PostingSkill
from app.routers.deps import Scope, scope_params, since, validate_role
from app.schemas import (
    GapSkill,
    SkillGapRequest,
    SkillGapResponse,
    SkillInfo,
    TrendingResponse,
    TrendingSkill,
)
from app.skills import SKILLS, SKILLS_BY_NAME, canonical_skill, canonical_state

router = APIRouter(prefix="/skills", tags=["skills"])


def _skill_counts(
    db: Session, start: datetime, end: datetime | None, scope: Scope
) -> tuple[int, dict[str, int]]:
    """Posting total and per-skill posting counts for in-scope postings in [start, end)."""
    conditions = [Posting.posted_at >= start, *scope.conditions()]
    if end is not None:
        conditions.append(Posting.posted_at < end)

    total = db.scalar(select(func.count()).select_from(Posting).where(*conditions)) or 0
    rows = db.execute(
        select(PostingSkill.skill, func.count())
        .join(Posting, Posting.id == PostingSkill.posting_id)
        .where(*conditions)
        .group_by(PostingSkill.skill)
    )
    return total, {skill: count for skill, count in rows}


def _category(name: str) -> str:
    return SKILLS_BY_NAME[name].category if name in SKILLS_BY_NAME else "Other"


@router.get("", response_model=list[SkillInfo])
def list_skills() -> list[SkillInfo]:
    """The full skill catalog that postings are matched against."""
    return [SkillInfo(name=s.name, category=s.category) for s in SKILLS]


@router.get("/trending", response_model=TrendingResponse)
def trending_skills(
    days: int = Query(30, ge=1, le=365, description="Window length in days"),
    limit: int = Query(20, ge=1, le=100),
    scope: Scope = Depends(scope_params),
    db: Session = Depends(get_db),
) -> TrendingResponse:
    """Most-requested skills in the last `days`, compared with the window before it."""
    current_start, previous_start = since(days), since(2 * days)
    total, counts = _skill_counts(db, current_start, None, scope)
    prev_total, prev_counts = _skill_counts(db, previous_start, current_start, scope)

    skills = []
    for name, count in counts.items():
        share = count / total if total else 0.0
        prev_share = prev_counts.get(name, 0) / prev_total if prev_total else 0.0
        skills.append(
            TrendingSkill(
                skill=name,
                category=_category(name),
                count=count,
                share=round(share, 4),
                previous_share=round(prev_share, 4),
                change=round(share - prev_share, 4),
            )
        )
    skills.sort(key=lambda s: (-s.count, s.skill))
    return TrendingResponse(
        days=days,
        role=scope.role,
        total_postings=total,
        previous_total_postings=prev_total,
        skills=skills[:limit],
    )


@router.post("/gap", response_model=SkillGapResponse)
def skill_gap(body: SkillGapRequest, db: Session = Depends(get_db)) -> SkillGapResponse:
    """Compare your skills with the most common skills in recent postings."""
    scope = Scope(
        role=validate_role(body.role),
        state=canonical_state(body.state) if body.state else None,
        city=body.city.strip() if body.city else None,
        work_mode=body.work_mode,
    )
    mine: set[str] = set()
    unrecognized: list[str] = []
    for raw in body.skills:
        name = canonical_skill(raw)
        if name:
            mine.add(name)
        elif raw.strip():
            unrecognized.append(raw.strip()[:60])

    total, counts = _skill_counts(db, since(body.days), None, scope)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[: body.top_n]
    top = [
        GapSkill(
            skill=name,
            category=_category(name),
            share=round(count / total, 4) if total else 0.0,
            have=name in mine,
        )
        for name, count in ranked
    ]
    return SkillGapResponse(
        role=scope.role,
        total_postings=total,
        coverage=round(sum(s.have for s in top) / len(top), 4) if top else 0.0,
        top_skills=top,
        missing=[s for s in top if not s.have],
        unrecognized=unrecognized,
    )

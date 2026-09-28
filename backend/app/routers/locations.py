from collections import Counter
from dataclasses import replace

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting
from app.routers.deps import Scope, scope_params, since
from app.routers.salaries import median_mid, salary_ranges
from app.schemas import LocationGroup, LocationsResponse, WorkModeShare
from app.skills import REMOTE, WORK_MODES

router = APIRouter(tags=["locations"])


@router.get("/locations", response_model=LocationsResponse)
def locations(
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(25, ge=1, le=100),
    scope: Scope = Depends(scope_params),
    db: Session = Depends(get_db),
) -> LocationsResponse:
    """Where the jobs are: postings by state (or by city, when a state is chosen),
    plus the remote / hybrid / onsite split.

    The split ignores the work_mode filter (so it always shows all three
    settings for the other filters); everything else respects it."""
    group_by = "city" if scope.state else "state"
    column = Posting.city if scope.state else Posting.state
    conditions = [Posting.posted_at >= since(days), *scope.conditions()]

    total = db.scalar(select(func.count()).select_from(Posting).where(*conditions)) or 0
    split_scope = replace(scope, work_mode=None)
    split_conditions = [Posting.posted_at >= since(days), *split_scope.conditions()]
    mode_counts = dict(
        db.execute(
            select(Posting.work_mode, func.count())
            .where(*split_conditions)
            .group_by(Posting.work_mode)
        ).all()
    )
    split_total = sum(mode_counts.values())

    per_place: Counter[str] = Counter()
    remote_per_place: Counter[str] = Counter()
    for place, mode, count in db.execute(
        select(column, Posting.work_mode, func.count())
        .where(*conditions, column.is_not(None))
        .group_by(column, Posting.work_mode)
    ):
        per_place[place] += count
        if mode == REMOTE:
            remote_per_place[place] += count

    salaries = salary_ranges(db, scope, days, include_predicted=False, group_by=group_by)
    ranked = sorted(per_place.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return LocationsResponse(
        days=days,
        group_by=group_by,
        state=scope.state,
        total_postings=total,
        work_modes=[
            WorkModeShare(
                work_mode=mode,
                postings=mode_counts.get(mode, 0),
                share=round(mode_counts.get(mode, 0) / split_total, 4) if split_total else 0.0,
            )
            for mode in WORK_MODES
        ],
        groups=[
            LocationGroup(
                name=place,
                postings=count,
                share=round(count / total, 4) if total else 0.0,
                remote_share=round(remote_per_place[place] / count, 4),
                median_salary=median_mid(salaries[place]) if salaries.get(place) else None,
                salary_postings=len(salaries.get(place, [])),
            )
            for place, count in ranked
        ],
    )

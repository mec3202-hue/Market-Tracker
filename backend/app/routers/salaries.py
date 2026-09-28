from collections import defaultdict
from statistics import mean, median
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting
from app.routers.deps import Scope, scope_params, since
from app.schemas import SalaryGroup, SalaryResponse

router = APIRouter(prefix="/salaries", tags=["salaries"])

GROUP_COLUMNS = {
    "role": Posting.role,
    "state": Posting.state,
    "city": Posting.city,
    "work_mode": Posting.work_mode,
}


def salary_ranges(
    db: Session, scope: Scope, days: int, include_predicted: bool, group_by: str
) -> dict[str, list[tuple[float, float]]]:
    """In-scope (min, max) salary ranges bucketed by the `group_by` column."""
    column = GROUP_COLUMNS[group_by]
    stmt = select(column, Posting.salary_min, Posting.salary_max).where(
        Posting.posted_at >= since(days),
        or_(Posting.salary_min.is_not(None), Posting.salary_max.is_not(None)),
        *scope.conditions(),
    )
    if not include_predicted:
        stmt = stmt.where(Posting.salary_is_predicted.is_(False))

    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for key, lo, hi in db.execute(stmt):
        if key is None:
            continue
        lo = lo if lo is not None else hi
        hi = hi if hi is not None else lo
        buckets[key].append((lo, hi))
    return buckets


def median_mid(ranges: list[tuple[float, float]]) -> int:
    return round(median((lo + hi) / 2 for lo, hi in ranges))


@router.get("", response_model=SalaryResponse)
def salaries(
    group_by: Literal["role", "state", "city", "work_mode"] = "role",
    days: int = Query(90, ge=1, le=365),
    include_predicted: bool = Query(
        False, description="Include salaries Adzuna estimated rather than read from the posting"
    ),
    min_postings: int = Query(3, ge=1, le=1000, description="Hide groups smaller than this"),
    limit: int = Query(20, ge=1, le=100),
    scope: Scope = Depends(scope_params),
    db: Session = Depends(get_db),
) -> SalaryResponse:
    """Salary ranges grouped by role, state, city, or work setting."""
    buckets = salary_ranges(db, scope, days, include_predicted, group_by)
    groups = [
        SalaryGroup(
            group=key,
            postings=len(ranges),
            avg_min=round(mean(lo for lo, _ in ranges)),
            avg_max=round(mean(hi for _, hi in ranges)),
            median_mid=median_mid(ranges),
        )
        for key, ranges in buckets.items()
        if len(ranges) >= min_postings
    ]
    groups.sort(key=lambda g: (-g.median_mid, g.group))
    return SalaryResponse(
        group_by=group_by,
        role=scope.role,
        city=scope.city,
        include_predicted=include_predicted,
        groups=groups[:limit],
    )

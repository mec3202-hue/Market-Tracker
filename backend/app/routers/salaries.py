from collections import defaultdict
from statistics import mean, median
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Posting
from app.routers.deps import since, validate_role
from app.schemas import SalaryGroup, SalaryResponse

router = APIRouter(prefix="/salaries", tags=["salaries"])


@router.get("", response_model=SalaryResponse)
def salaries(
    role: str | None = Query(None, max_length=60),
    city: str | None = Query(None, min_length=1, max_length=120),
    group_by: Literal["role", "city"] = "role",
    days: int = Query(90, ge=1, le=365),
    include_predicted: bool = Query(
        False, description="Include salaries Adzuna estimated rather than read from the posting"
    ),
    min_postings: int = Query(3, ge=1, le=1000, description="Hide groups smaller than this"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SalaryResponse:
    """Salary ranges grouped by role or city, optionally filtered by either."""
    role = validate_role(role)
    city = city.strip() if city else None

    stmt = select(Posting.role, Posting.city, Posting.salary_min, Posting.salary_max).where(
        Posting.posted_at >= since(days),
        or_(Posting.salary_min.is_not(None), Posting.salary_max.is_not(None)),
    )
    if role:
        stmt = stmt.where(Posting.role == role)
    if city:
        stmt = stmt.where(func.lower(Posting.city) == city.lower())
    if not include_predicted:
        stmt = stmt.where(Posting.salary_is_predicted.is_(False))

    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row_role, row_city, lo, hi in db.execute(stmt):
        key = row_role if group_by == "role" else row_city
        if key is None:
            continue
        lo = lo if lo is not None else hi
        hi = hi if hi is not None else lo
        buckets[key].append((lo, hi))

    groups = [
        SalaryGroup(
            group=key,
            postings=len(ranges),
            avg_min=round(mean(lo for lo, _ in ranges)),
            avg_max=round(mean(hi for _, hi in ranges)),
            median_mid=round(median((lo + hi) / 2 for lo, hi in ranges)),
        )
        for key, ranges in buckets.items()
        if len(ranges) >= min_postings
    ]
    groups.sort(key=lambda g: (-g.median_mid, g.group))
    return SalaryResponse(
        group_by=group_by,
        role=role,
        city=city,
        include_predicted=include_predicted,
        groups=groups[:limit],
    )

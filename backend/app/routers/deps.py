from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import HTTPException, Query
from sqlalchemy import ColumnElement, func

from app.models import Posting
from app.skills import OTHER_ROLE, ROLE_NAMES, canonical_skill, canonical_state

VALID_ROLES = (*ROLE_NAMES, OTHER_ROLE)
WorkMode = Literal["remote", "hybrid", "onsite"]


def validate_role(role: str | None) -> str | None:
    if role is None or role == "":
        return None
    for valid in VALID_ROLES:
        if valid.lower() == role.strip().lower():
            return valid
    raise HTTPException(422, detail=f"Unknown role '{role}'. Valid roles: {', '.join(VALID_ROLES)}")


def validate_skill(skill: str | None) -> str | None:
    if skill is None or skill == "":
        return None
    name = canonical_skill(skill)
    if name is None:
        raise HTTPException(
            422, detail=f"Unknown skill '{skill}'. See GET /skills for the catalog."
        )
    return name


def since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@dataclass
class Scope:
    """Filters shared by every view: which postings are we looking at?"""

    role: str | None = None
    state: str | None = None
    city: str | None = None
    work_mode: str | None = None

    def conditions(self) -> list[ColumnElement[bool]]:
        conds = []
        if self.role:
            conds.append(Posting.role == self.role)
        if self.state:
            conds.append(func.lower(Posting.state) == self.state.lower())
        if self.city:
            conds.append(func.lower(Posting.city) == self.city.lower())
        if self.work_mode:
            conds.append(Posting.work_mode == self.work_mode)
        return conds


def scope_params(
    role: str | None = Query(None, max_length=60),
    state: str | None = Query(
        None, min_length=2, max_length=60, description="State name or two-letter code"
    ),
    city: str | None = Query(None, min_length=1, max_length=120),
    work_mode: WorkMode | None = Query(None, description="remote, hybrid, or onsite"),
) -> Scope:
    return Scope(
        role=validate_role(role),
        state=canonical_state(state) if state else None,
        city=city.strip() if city else None,
        work_mode=work_mode,
    )

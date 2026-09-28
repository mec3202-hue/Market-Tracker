from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.skills import OTHER_ROLE, ROLE_NAMES, canonical_skill

VALID_ROLES = (*ROLE_NAMES, OTHER_ROLE)


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

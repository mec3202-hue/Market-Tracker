from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillInfo(BaseModel):
    name: str
    category: str


class TrendingSkill(BaseModel):
    skill: str
    category: str
    count: int = Field(description="Postings in the current window mentioning the skill")
    share: float = Field(description="Fraction of postings in the current window (0-1)")
    previous_share: float = Field(description="Fraction in the preceding window of equal length")
    change: float = Field(description="share - previous_share")


class TrendingResponse(BaseModel):
    days: int
    role: str | None
    total_postings: int
    previous_total_postings: int
    skills: list[TrendingSkill]


class SalaryGroup(BaseModel):
    group: str
    postings: int
    avg_min: float
    avg_max: float
    median_mid: float


class SalaryResponse(BaseModel):
    group_by: str
    role: str | None
    city: str | None
    include_predicted: bool
    groups: list[SalaryGroup]


class PostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str | None
    location: str | None
    city: str | None
    state: str | None
    role: str
    work_mode: str | None
    salary_min: float | None
    salary_max: float | None
    salary_is_predicted: bool
    url: str | None
    posted_at: datetime
    skills: list[str]
    snippet: str


class PostingPage(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: list[PostingOut]


class SkillGapRequest(BaseModel):
    skills: list[str] = Field(default_factory=list, max_length=60)
    role: str | None = None
    state: str | None = Field(None, max_length=60)
    city: str | None = Field(None, max_length=120)
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None
    days: int = Field(90, ge=1, le=365)
    top_n: int = Field(15, ge=1, le=50)


class GapSkill(BaseModel):
    skill: str
    category: str
    share: float
    have: bool


class SkillGapResponse(BaseModel):
    role: str | None
    total_postings: int
    coverage: float = Field(description="Share of the top skills you already have (0-1)")
    top_skills: list[GapSkill]
    missing: list[GapSkill]
    unrecognized: list[str]


class CityOption(BaseModel):
    city: str
    state: str | None


class WorkModeShare(BaseModel):
    work_mode: str
    postings: int
    share: float


class LocationGroup(BaseModel):
    name: str
    postings: int
    share: float = Field(description="Share of in-scope postings (0-1)")
    remote_share: float = Field(description="Share of this place's postings that are remote")
    median_salary: int | None = Field(description="Median salary midpoint (posted salaries only)")
    salary_postings: int


class LocationsResponse(BaseModel):
    days: int
    group_by: Literal["state", "city"]
    state: str | None
    total_postings: int
    work_modes: list[WorkModeShare]
    groups: list[LocationGroup]


class FiltersResponse(BaseModel):
    roles: list[str]
    states: list[str]
    cities: list[CityOption]
    total_postings: int
    last_ingested_at: datetime | None

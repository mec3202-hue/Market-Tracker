"""Skill catalog and keyword-based skill extraction.

Each skill has a canonical name, a category, and one or more regex patterns.
Patterns are matched case-insensitively unless the skill sets
``case_sensitive`` (needed for short names like "R" or "Go" that collide with
ordinary words).
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    patterns: tuple[str, ...]
    case_sensitive: bool = False
    _compiled: tuple[re.Pattern, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        # (?<![\w]) / (?![\w]) act as word boundaries that also work for names
        # ending in symbols, such as "C++" or "Power BI".
        compiled = tuple(re.compile(rf"(?<!\w){p}(?!\w)", flags) for p in self.patterns)
        object.__setattr__(self, "_compiled", compiled)

    def found_in(self, text: str) -> bool:
        return any(p.search(text) for p in self._compiled)


def _s(name: str, category: str, *patterns: str, case_sensitive: bool = False) -> Skill:
    return Skill(name, category, patterns or (re.escape(name),), case_sensitive)


SKILLS: tuple[Skill, ...] = (
    # Languages
    _s("SQL", "Languages", r"sql", r"t-sql", r"pl/sql"),
    _s("Python", "Languages", r"python"),
    _s("R", "Languages", r"R(?![&/-])", r"RStudio", r"tidyverse", case_sensitive=True),
    _s("SAS", "Languages", r"SAS", case_sensitive=True),
    _s("SPSS", "Languages", r"spss"),
    _s("Stata", "Languages", r"stata"),
    _s("Scala", "Languages", r"scala"),
    _s("Java", "Languages", r"java(?!script)"),
    _s("JavaScript", "Languages", r"javascript", r"node\.?js"),
    _s("VBA", "Languages", r"vba", r"visual basic"),
    # BI & visualization
    _s("Tableau", "BI & Visualization", r"tableau"),
    _s("Power BI", "BI & Visualization", r"power\s?bi", r"dax"),
    _s("Looker", "BI & Visualization", r"looker(?! studio)", r"lookml"),
    _s("Looker Studio", "BI & Visualization", r"looker studio", r"data studio"),
    _s("Qlik", "BI & Visualization", r"qlik(?:view|sense)?"),
    _s("Excel", "BI & Visualization", r"excel", r"spreadsheets?", r"pivot tables?", r"vlookup"),
    _s("Google Sheets", "BI & Visualization", r"google sheets"),
    _s("Mode", "BI & Visualization", r"Mode Analytics", case_sensitive=True),
    _s("Metabase", "BI & Visualization", r"metabase"),
    _s("Sigma", "BI & Visualization", r"Sigma Computing", case_sensitive=True),
    _s("Alteryx", "BI & Visualization", r"alteryx"),
    # Data platforms & warehouses
    _s("Snowflake", "Data Platforms", r"snowflake"),
    _s("BigQuery", "Data Platforms", r"big\s?query"),
    _s("Redshift", "Data Platforms", r"redshift"),
    _s("Databricks", "Data Platforms", r"databricks"),
    _s("PostgreSQL", "Data Platforms", r"postgres(?:ql)?"),
    _s("MySQL", "Data Platforms", r"mysql"),
    _s("SQL Server", "Data Platforms", r"sql server", r"mssql", r"ssis", r"ssrs"),
    _s("Oracle", "Data Platforms", r"oracle"),
    _s("Spark", "Data Platforms", r"spark", r"pyspark"),
    _s("Hadoop", "Data Platforms", r"hadoop", r"hive"),
    # Transformation & orchestration
    _s("dbt", "Data Engineering", r"dbt"),
    _s("Airflow", "Data Engineering", r"airflow"),
    _s("ETL", "Data Engineering", r"etl", r"elt", r"data pipelines?"),
    _s("Fivetran", "Data Engineering", r"fivetran"),
    _s("Git", "Data Engineering", r"git", r"github", r"gitlab"),
    _s("Docker", "Data Engineering", r"docker"),
    _s("Kafka", "Data Engineering", r"kafka"),
    _s("Data Governance", "Data Engineering", r"data governance", r"data quality"),
    # Cloud
    _s("AWS", "Cloud", r"aws", r"amazon web services"),
    _s("Azure", "Cloud", r"azure"),
    _s("GCP", "Cloud", r"gcp", r"google cloud"),
    # Analytics & methods
    _s("Statistics", "Methods", r"statistic(?:s|al)", r"regression", r"hypothesis testing"),
    _s(
        "A/B Testing", "Methods", r"a/b test(?:s|ing)?", r"experimentation", r"split test(?:s|ing)?"
    ),
    _s(
        "Machine Learning",
        "Methods",
        r"machine learning",
        r"ml models?",
        r"predictive model(?:s|ing)?",
    ),
    _s("Forecasting", "Methods", r"forecast(?:s|ing)?"),
    _s(
        "Data Modeling",
        "Methods",
        r"data model(?:s|ing|ling)?",
        r"dimensional model(?:s|ing|ling)?",
    ),
    _s("Data Visualization", "Methods", r"data visuali[sz]ation", r"dashboards?"),
    _s(
        "Generative AI",
        "Methods",
        r"generative ai",
        r"gen ?ai",
        r"llms?",
        r"large language models?",
    ),
    _s("KPIs", "Methods", r"kpis?", r"key performance indicators?"),
    # Libraries
    _s("pandas", "Libraries", r"pandas"),
    _s("NumPy", "Libraries", r"numpy"),
    _s("scikit-learn", "Libraries", r"scikit-learn", r"sklearn"),
    # Business & marketing tools
    _s("Google Analytics", "Business Tools", r"google analytics", r"GA4"),
    _s("Salesforce", "Business Tools", r"salesforce", r"sfdc"),
    _s("HubSpot", "Business Tools", r"hubspot"),
    _s("Adobe Analytics", "Business Tools", r"adobe analytics", r"omniture"),
    _s("Jira", "Business Tools", r"jira"),
    _s("SAP", "Business Tools", r"SAP", case_sensitive=True),
    _s("Workday", "Business Tools", r"workday"),
    _s("Amplitude", "Business Tools", r"amplitude analytics", r"Amplitude"),
    _s("Mixpanel", "Business Tools", r"mixpanel"),
)

SKILLS_BY_NAME: dict[str, Skill] = {s.name: s for s in SKILLS}
_SKILLS_BY_LOWER: dict[str, Skill] = {s.name.lower(): s for s in SKILLS}


def canonical_skill(name: str) -> str | None:
    """Return the catalog spelling of ``name`` (case-insensitive), or None."""
    skill = _SKILLS_BY_LOWER.get(name.strip().lower())
    return skill.name if skill else None


def extract_skills(text: str) -> set[str]:
    """Return the canonical names of every catalog skill mentioned in ``text``."""
    if not text:
        return set()
    return {skill.name for skill in SKILLS if skill.found_in(text)}


# Role buckets, most specific first. A posting's title decides its role; the
# search term that found it is only the fallback.
ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Analytics Engineer", ("analytics engineer",)),
    ("Data Engineer", ("data engineer",)),
    ("Data Scientist", ("data scientist",)),
    ("Marketing Analyst", ("marketing analyst", "marketing analytics", "digital analyst")),
    ("Financial Analyst", ("financial analyst", "finance analyst", "fp&a")),
    ("Product Analyst", ("product analyst",)),
    ("Operations Analyst", ("operations analyst", "business operations analyst")),
    ("BI Analyst", ("bi analyst", "business intelligence", "bi developer", "bi engineer")),
    ("Business Analyst", ("business analyst", "business systems analyst")),
    ("Data Analyst", ("data analyst", "analyst")),
)
ROLE_NAMES: tuple[str, ...] = tuple(name for name, _ in ROLES)
OTHER_ROLE = "Other"


def classify_role(title: str, fallback: str | None = None) -> str:
    lowered = (title or "").lower()
    for name, keywords in ROLES:
        if any(k in lowered for k in keywords):
            return name
    if fallback:
        return classify_role(fallback)
    return OTHER_ROLE


# Work setting ---------------------------------------------------------------
# Adzuna has no remote flag, so it's inferred from the posting's text. Postings
# that don't mention either are "onsite" (in person, or not stated).
REMOTE, HYBRID, ONSITE = "remote", "hybrid", "onsite"
WORK_MODES: tuple[str, ...] = (REMOTE, HYBRID, ONSITE)

_NOT_REMOTE = re.compile(
    r"(?<!\w)(?:not|no|non)[- ]remote(?!\w)|not (?:a |an )?remote|remote work is not", re.I
)
_HYBRID = re.compile(r"(?<!\w)hybrid(?!\w)(?! cloud)", re.I)
_REMOTE = re.compile(
    r"(?<!\w)(?:remote(?! sensing)|work(?:ing)? from home|wfh|telecommut\w*|work from anywhere"
    r"|virtual (?:role|position))(?!\w)",
    re.I,
)


def detect_work_mode(*texts: str | None) -> str:
    """Classify a posting as remote, hybrid, or onsite from its title/location/description."""
    text = "\n".join(t for t in texts if t)
    if _NOT_REMOTE.search(text):
        return HYBRID if _HYBRID.search(text) else ONSITE
    if _HYBRID.search(text):
        return HYBRID
    if _REMOTE.search(text):
        return REMOTE
    return ONSITE


# US states -------------------------------------------------------------------
US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip


def canonical_state(value: str) -> str:
    """Expand a two-letter abbreviation ("CA" -> "California"); otherwise return as given."""
    value = value.strip()
    return US_STATES.get(value.upper(), value)

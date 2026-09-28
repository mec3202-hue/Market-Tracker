import pytest

from app.skills import (
    canonical_skill,
    canonical_state,
    classify_role,
    detect_work_mode,
    extract_skills,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Must know SQL and Python", {"SQL", "Python"}),
        ("Experience with Power BI (DAX) or PowerBI", {"Power BI"}),
        ("Build data models in dbt on Snowflake", {"dbt", "Snowflake", "Data Modeling"}),
        ("Proficient in R and RStudio", {"R"}),
        ("Advanced Excel incl. pivot tables", {"Excel"}),
        ("Google BigQuery and Big Query", {"BigQuery"}),
    ],
)
def test_extracts_expected_skills(text, expected):
    assert expected <= extract_skills(text)


@pytest.mark.parametrize(
    ("text", "absent"),
    [
        ("Join our R&D team", "R"),
        ("We're a remote-first company", "R"),
        ("Strong JavaScript experience", "Java"),
        ("PostgreSQL and MySQL databases", "SQL"),
        ("A digital marketing role", "Git"),
        ("Collect sas and other things", "SAS"),
        ("Looker Studio reports", "Looker"),
    ],
)
def test_avoids_false_positives(text, absent):
    assert absent not in extract_skills(text)


def test_empty_text_has_no_skills():
    assert extract_skills("") == set()


def test_canonical_skill_is_case_insensitive():
    assert canonical_skill("power bi") == "Power BI"
    assert canonical_skill("  DBT ") == "dbt"
    assert canonical_skill("cobol") is None


@pytest.mark.parametrize(
    ("title", "fallback", "role"),
    [
        ("Senior Analytics Engineer", None, "Analytics Engineer"),
        ("Digital Marketing Analyst II", None, "Marketing Analyst"),
        ("Business Intelligence Analyst", None, "BI Analyst"),
        ("Business Analyst - Payments", None, "Business Analyst"),
        ("Analyst, Operations", None, "Data Analyst"),
        ("Insights Associate", "marketing analyst", "Marketing Analyst"),
        ("Insights Associate", None, "Other"),
    ],
)
def test_classify_role(title, fallback, role):
    assert classify_role(title, fallback) == role


@pytest.mark.parametrize(
    ("texts", "mode"),
    [
        (("Remote Data Analyst",), "remote"),
        (("Data Analyst", "US", "This position is 100% remote."), "remote"),
        (("Analyst", "Work from home, anywhere in the US"), "remote"),
        (("Analyst", "Hybrid: 3 days in our Chicago office"), "hybrid"),
        (("Analyst", "Hybrid schedule, remote Fridays"), "hybrid"),
        (("Analyst", "This is not a remote role."), "onsite"),
        (("Analyst", "Non-remote position based in Dallas"), "onsite"),
        (("GIS Analyst", "Remote sensing experience preferred"), "onsite"),
        (("Cloud Analyst", "Experience with hybrid cloud"), "onsite"),
        (("Analyst", None, "Join our Denver team."), "onsite"),
    ],
)
def test_detect_work_mode(texts, mode):
    assert detect_work_mode(*texts) == mode


def test_canonical_state():
    assert canonical_state("ca") == "California"
    assert canonical_state(" NY ") == "New York"
    assert canonical_state("Texas") == "Texas"

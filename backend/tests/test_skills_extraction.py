import pytest

from app.skills import canonical_skill, classify_role, extract_skills


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

import json

from app import export_static


def test_export_writes_frontend_data(db, add_posting, tmp_path, monkeypatch):
    # Point the exporter at the test database session.
    monkeypatch.setattr(export_static, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    add_posting(skills=["SQL", "dbt"], role="Analytics Engineer", salary=(100_000, 120_000))
    add_posting(skills=["Excel"], days_ago=400)  # too old to export

    assert export_static.export(tmp_path) == 1

    postings = json.loads((tmp_path / "postings.json").read_text())
    assert postings[0]["skills"] == ["SQL", "dbt"]
    assert postings[0]["salary_min"] == 100_000
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["total_postings"] == 2
    assert "generated_at" in meta
    skills = json.loads((tmp_path / "skills.json").read_text())
    assert {"name": "SQL", "category": "Languages"} in skills

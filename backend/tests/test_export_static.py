import json

from app import export_static


def _export(db, monkeypatch, tmp_path, **kwargs):
    monkeypatch.setattr(export_static, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    return export_static.export(tmp_path, **kwargs)


def test_export_writes_frontend_data(db, add_posting, tmp_path, monkeypatch):
    add_posting(
        skills=["SQL", "dbt"],
        role="Analytics Engineer",
        state="California",
        city="Los Angeles",
        work_mode="remote",
        salary=(100_000, 120_000),
    )
    add_posting(skills=["Excel"], city=None, state=None)
    add_posting(skills=["Excel"], days_ago=400)  # too old to export

    assert _export(db, monkeypatch, tmp_path) == (2, 2)

    facts = json.loads((tmp_path / "facts.json").read_text())
    assert facts["fields"][0] == "posted"
    dims = facts["dims"]
    first, second = facts["rows"]  # newest first
    assert dims["roles"][second[1]] == "Analytics Engineer"
    assert dims["states"][second[2]] == "California"
    assert dims["cities"][second[3]] == "Los Angeles"
    assert dims["work_modes"][second[4]] == "remote"
    assert second[5:8] == [100_000, 120_000, 0]
    assert sorted(dims["skills"][i] for i in second[8]) == ["SQL", "dbt"]
    assert first[2] == -1 and first[3] == -1

    postings = json.loads((tmp_path / "postings.json").read_text())
    assert postings[1]["skills"] == ["SQL", "dbt"]
    assert postings[1]["work_mode"] == "remote"
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["total_postings"] == 3
    assert meta["states"] == ["California", "Texas"]
    assert "generated_at" in meta
    skills = json.loads((tmp_path / "skills.json").read_text())
    assert {"name": "SQL", "category": "Languages"} in skills


def test_export_caps_detailed_postings(db, add_posting, tmp_path, monkeypatch):
    for _ in range(5):
        add_posting()
    assert _export(db, monkeypatch, tmp_path, max_detail=2) == (5, 2)

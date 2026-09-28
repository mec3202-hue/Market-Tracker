def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_skill_catalog(client):
    body = client.get("/skills").json()
    names = {s["name"] for s in body}
    assert {"SQL", "Python", "dbt", "Tableau", "Power BI", "Snowflake"} <= names


# /skills/trending ------------------------------------------------------------


def test_trending_counts_and_shares(client, add_posting):
    add_posting(skills=["SQL", "Python"])
    add_posting(skills=["SQL", "Tableau"])
    add_posting(skills=["SQL"])
    add_posting(skills=["dbt"], days_ago=45)  # previous window only

    body = client.get("/skills/trending", params={"days": 30}).json()
    assert body["total_postings"] == 3
    assert body["previous_total_postings"] == 1
    top = body["skills"][0]
    assert top["skill"] == "SQL"
    assert top["count"] == 3
    assert top["share"] == 1.0
    assert top["previous_share"] == 0.0
    assert "dbt" not in {s["skill"] for s in body["skills"]}


def test_trending_change_against_previous_window(client, add_posting):
    add_posting(skills=["dbt"], days_ago=5)
    add_posting(skills=["SQL"], days_ago=5)
    add_posting(skills=["SQL"], days_ago=40)

    skills = {s["skill"]: s for s in client.get("/skills/trending?days=30").json()["skills"]}
    assert skills["dbt"]["change"] == 0.5
    assert skills["SQL"]["change"] == -0.5


def test_trending_filters_by_role_case_insensitively(client, add_posting):
    add_posting(skills=["dbt"], role="Analytics Engineer")
    add_posting(skills=["Excel"], role="Business Analyst")

    body = client.get("/skills/trending", params={"role": "analytics engineer"}).json()
    assert body["role"] == "Analytics Engineer"
    assert [s["skill"] for s in body["skills"]] == ["dbt"]


def test_trending_limit(client, add_posting):
    add_posting(skills=["SQL", "Python", "Excel", "Tableau"])
    assert len(client.get("/skills/trending?limit=2").json()["skills"]) == 2


def test_trending_empty_database(client):
    body = client.get("/skills/trending").json()
    assert body["total_postings"] == 0
    assert body["skills"] == []


def test_trending_validation(client):
    assert client.get("/skills/trending?days=0").status_code == 422
    assert client.get("/skills/trending?days=366").status_code == 422
    assert client.get("/skills/trending?limit=abc").status_code == 422
    resp = client.get("/skills/trending?role=astronaut")
    assert resp.status_code == 422
    assert "Unknown role" in resp.json()["detail"]


# /salaries -------------------------------------------------------------------


def test_salaries_grouped_by_role(client, add_posting):
    add_posting(role="Data Analyst", salary=(60_000, 80_000))
    add_posting(role="Data Analyst", salary=(70_000, 90_000))
    add_posting(role="Analytics Engineer", salary=(110_000, 130_000))
    add_posting(role="Business Analyst")  # no salary: ignored

    body = client.get("/salaries?min_postings=1").json()
    groups = {g["group"]: g for g in body["groups"]}
    assert set(groups) == {"Data Analyst", "Analytics Engineer"}
    assert groups["Data Analyst"] == {
        "group": "Data Analyst",
        "postings": 2,
        "avg_min": 65_000,
        "avg_max": 85_000,
        "median_mid": 75_000,
    }
    # Sorted highest-paying first.
    assert body["groups"][0]["group"] == "Analytics Engineer"


def test_salaries_grouped_by_city_with_role_filter(client, add_posting):
    add_posting(role="Data Analyst", city="Austin", salary=(60_000, 60_000))
    add_posting(role="Data Analyst", city="Seattle", salary=(90_000, 90_000))
    add_posting(role="Analytics Engineer", city="Seattle", salary=(150_000, 150_000))

    body = client.get(
        "/salaries", params={"group_by": "city", "role": "Data Analyst", "min_postings": 1}
    ).json()
    assert [(g["group"], g["median_mid"]) for g in body["groups"]] == [
        ("Seattle", 90_000),
        ("Austin", 60_000),
    ]


def test_salaries_city_filter_is_case_insensitive(client, add_posting):
    add_posting(city="Austin", salary=(60_000, 70_000))
    add_posting(city="Denver", salary=(80_000, 90_000))
    body = client.get("/salaries?city=austin&min_postings=1").json()
    assert body["groups"][0]["avg_min"] == 60_000
    assert body["groups"][0]["postings"] == 1


def test_salaries_single_sided_ranges(client, add_posting):
    add_posting(salary=(None, 100_000))
    body = client.get("/salaries?min_postings=1").json()
    assert body["groups"][0]["avg_min"] == 100_000


def test_salaries_excludes_predicted_by_default(client, add_posting):
    add_posting(salary=(50_000, 50_000), predicted=True)
    assert client.get("/salaries?min_postings=1").json()["groups"] == []
    body = client.get("/salaries?min_postings=1&include_predicted=true").json()
    assert body["groups"][0]["postings"] == 1


def test_salaries_min_postings(client, add_posting):
    add_posting(salary=(50_000, 60_000))
    assert client.get("/salaries").json()["groups"] == []  # default min_postings=3


def test_salaries_grouped_by_state_and_work_mode(client, add_posting):
    add_posting(state="California", city="Los Angeles", salary=(100_000, 120_000))
    add_posting(state="Texas", work_mode="remote", salary=(80_000, 80_000))

    by_state = client.get("/salaries?group_by=state&min_postings=1").json()
    assert [g["group"] for g in by_state["groups"]] == ["California", "Texas"]
    by_mode = client.get("/salaries?group_by=work_mode&min_postings=1").json()
    assert [g["group"] for g in by_mode["groups"]] == ["onsite", "remote"]


def test_salaries_validation(client):
    assert client.get("/salaries?group_by=company").status_code == 422
    assert client.get("/salaries?role=chef").status_code == 422
    assert client.get("/salaries?city=").status_code == 422


# /postings -------------------------------------------------------------------


def test_postings_filter_by_skill(client, add_posting):
    add_posting(skills=["SQL", "dbt"])
    add_posting(skills=["Excel"])

    body = client.get("/postings", params={"skill": "DBT"}).json()
    assert body["total"] == 1
    assert body["items"][0]["skills"] == ["SQL", "dbt"]


def test_postings_pagination_newest_first(client, add_posting):
    for days in range(5):
        add_posting(days_ago=days, title=f"Posting {days}")

    first = client.get("/postings?page=1&page_size=2").json()
    assert first["total"] == 5
    assert first["pages"] == 3
    assert [p["title"] for p in first["items"]] == ["Posting 0", "Posting 1"]

    last = client.get("/postings?page=3&page_size=2").json()
    assert [p["title"] for p in last["items"]] == ["Posting 4"]

    beyond = client.get("/postings?page=4&page_size=2").json()
    assert beyond["items"] == []


def test_postings_filters_combine(client, add_posting):
    add_posting(role="Data Analyst", city="Austin", title="Data Analyst, Growth")
    add_posting(role="Data Analyst", city="Denver", title="Data Analyst, Growth")
    add_posting(role="Business Analyst", city="Austin", title="Business Analyst")

    body = client.get("/postings?role=Data Analyst&city=AUSTIN&q=growth").json()
    assert body["total"] == 1
    assert body["items"][0]["city"] == "Austin"


def test_postings_title_search_escapes_wildcards(client, add_posting):
    add_posting(title="Analyst 100% remote")
    add_posting(title="Analyst 1000 remote")
    assert client.get("/postings", params={"q": "100%"}).json()["total"] == 1


def test_postings_validation(client):
    assert client.get("/postings?page=0").status_code == 422
    assert client.get("/postings?page_size=101").status_code == 422
    assert client.get("/postings?q=a").status_code == 422
    resp = client.get("/postings?skill=cobol")
    assert resp.status_code == 422
    assert "Unknown skill" in resp.json()["detail"]


# /skills/gap -----------------------------------------------------------------


def test_skill_gap(client, add_posting):
    add_posting(skills=["SQL", "Python", "dbt"])
    add_posting(skills=["SQL", "Tableau"])
    add_posting(skills=["SQL", "dbt"])

    body = client.post(
        "/skills/gap", json={"skills": ["sql", "Tableau", "underwater basket weaving"]}
    ).json()
    assert body["total_postings"] == 3
    assert [s["skill"] for s in body["top_skills"]] == ["SQL", "dbt", "Python", "Tableau"]
    assert [s["skill"] for s in body["missing"]] == ["dbt", "Python"]
    assert body["coverage"] == 0.5
    assert body["unrecognized"] == ["underwater basket weaving"]


def test_skill_gap_by_role_and_top_n(client, add_posting):
    add_posting(skills=["dbt", "Snowflake"], role="Analytics Engineer")
    add_posting(skills=["Excel"], role="Business Analyst")

    body = client.post(
        "/skills/gap", json={"skills": [], "role": "Analytics Engineer", "top_n": 1}
    ).json()
    assert len(body["top_skills"]) == 1
    assert body["top_skills"][0]["skill"] in {"dbt", "Snowflake"}
    assert body["coverage"] == 0.0


def test_skill_gap_validation(client):
    assert client.post("/skills/gap", json={"skills": "SQL"}).status_code == 422
    assert client.post("/skills/gap", json={"skills": ["x"] * 61}).status_code == 422
    assert client.post("/skills/gap", json={"top_n": 0}).status_code == 422
    assert client.post("/skills/gap", json={"role": "wizard"}).status_code == 422


# /filters --------------------------------------------------------------------


def test_filters(client, add_posting):
    add_posting(role="Business Analyst", city="Austin")
    add_posting(role="Data Analyst", city="Austin")
    add_posting(role="Data Analyst", city="Denver")

    body = client.get("/filters").json()
    assert body["roles"] == ["Business Analyst", "Data Analyst"]
    assert body["states"] == ["Texas"]
    assert body["cities"] == [
        {"city": "Austin", "state": "Texas"},
        {"city": "Denver", "state": "Texas"},
    ]
    assert body["total_postings"] == 3
    assert body["last_ingested_at"] is not None


# State and work-setting scope --------------------------------------------------


def test_scope_filters_apply_to_every_view(client, add_posting):
    add_posting(skills=["SQL"], state="California", city="Los Angeles", work_mode="remote")
    add_posting(skills=["Excel"], state="Texas", work_mode="onsite")

    trending = client.get("/skills/trending?state=CA").json()  # abbreviation accepted
    assert [s["skill"] for s in trending["skills"]] == ["SQL"]

    postings = client.get("/postings?work_mode=remote").json()
    assert postings["total"] == 1
    assert postings["items"][0]["work_mode"] == "remote"
    assert postings["items"][0]["state"] == "California"

    gap = client.post("/skills/gap", json={"state": "texas"}).json()
    assert [s["skill"] for s in gap["top_skills"]] == ["Excel"]


def test_scope_validation(client):
    assert client.get("/postings?work_mode=moon").status_code == 422
    assert client.get("/postings?state=X").status_code == 422
    assert client.post("/skills/gap", json={"work_mode": "moon"}).status_code == 422


# /locations ------------------------------------------------------------------


def test_locations_by_state(client, add_posting):
    add_posting(
        state="California", city="Los Angeles", work_mode="remote", salary=(100_000, 100_000)
    )
    add_posting(state="California", city="San Diego", salary=(80_000, 80_000))
    add_posting(state="Texas", work_mode="hybrid")
    add_posting(state=None, city=None, work_mode="remote")  # no location: counted, not grouped

    body = client.get("/locations").json()
    assert body["group_by"] == "state"
    assert body["total_postings"] == 4
    modes = {m["work_mode"]: m for m in body["work_modes"]}
    assert (
        modes["remote"]["postings"],
        modes["hybrid"]["postings"],
        modes["onsite"]["postings"],
    ) == (2, 1, 1)
    assert modes["remote"]["share"] == 0.5
    ca, tx = body["groups"]
    assert ca == {
        "name": "California",
        "postings": 2,
        "share": 0.5,
        "remote_share": 0.5,
        "median_salary": 90_000,
        "salary_postings": 2,
    }
    assert tx["name"] == "Texas"
    assert tx["median_salary"] is None


def test_locations_drill_into_state_cities(client, add_posting):
    add_posting(state="California", city="Los Angeles")
    add_posting(state="California", city="Los Angeles")
    add_posting(state="California", city="San Diego")
    add_posting(state="Texas", city="Austin")

    body = client.get("/locations?state=California").json()
    assert body["group_by"] == "city"
    assert body["state"] == "California"
    assert [(g["name"], g["postings"]) for g in body["groups"]] == [
        ("Los Angeles", 2),
        ("San Diego", 1),
    ]


def test_locations_work_mode_filter(client, add_posting):
    add_posting(state="California", work_mode="remote")
    add_posting(state="Texas", work_mode="onsite")
    body = client.get("/locations?work_mode=remote").json()
    assert [g["name"] for g in body["groups"]] == ["California"]
    assert body["total_postings"] == 1
    # The split still shows every work setting for the other filters.
    assert [(m["work_mode"], m["share"]) for m in body["work_modes"]] == [
        ("remote", 0.5),
        ("hybrid", 0.0),
        ("onsite", 0.5),
    ]

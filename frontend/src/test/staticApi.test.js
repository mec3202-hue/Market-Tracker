import { describe, expect, it } from "vitest";
import { createStaticApi } from "../staticApi.js";

const NOW = Date.parse("2026-09-28T12:00:00Z");
const daysAgo = (d) => new Date(NOW - d * 86400000).toISOString();

let n = 0;
const posting = ({ skills = [], role = "Data Analyst", city = "Austin", days = 1, salary = [null, null], predicted = false, title } = {}) => ({
  id: `p-${n++}`,
  title: title ?? `${role} ${n}`,
  company: "Acme",
  location: `${city}, TX`,
  city,
  role,
  salary_min: salary[0],
  salary_max: salary[1],
  salary_is_predicted: predicted,
  url: null,
  posted_at: daysAgo(days),
  skills,
  snippet: "",
});

const SKILLS = [
  { name: "SQL", category: "Languages" },
  { name: "Python", category: "Languages" },
  { name: "dbt", category: "Data Engineering" },
  { name: "Tableau", category: "BI & Visualization" },
];

const make = (postings) =>
  createStaticApi({ meta: { roles: [] }, skills: SKILLS, postings }, { now: () => NOW });

describe("static API", () => {
  it("computes trending shares and change vs. the previous window", async () => {
    const api = make([
      posting({ skills: ["dbt"], days: 5 }),
      posting({ skills: ["SQL"], days: 5 }),
      posting({ skills: ["SQL"], days: 40 }),
    ]);
    const body = await api.trending({ days: 30 });
    expect(body.total_postings).toBe(2);
    expect(body.previous_total_postings).toBe(1);
    const bySkill = Object.fromEntries(body.skills.map((s) => [s.skill, s]));
    expect(bySkill.dbt.change).toBe(0.5);
    expect(bySkill.SQL.change).toBe(-0.5);
    expect(body.skills[0].skill).toBe("SQL"); // ties broken by name
  });

  it("filters trending by role", async () => {
    const api = make([
      posting({ skills: ["dbt"], role: "Analytics Engineer" }),
      posting({ skills: ["SQL"], role: "Business Analyst" }),
    ]);
    const body = await api.trending({ role: "Analytics Engineer" });
    expect(body.skills.map((s) => s.skill)).toEqual(["dbt"]);
  });

  it("groups salaries like the API", async () => {
    const api = make([
      posting({ role: "Data Analyst", salary: [60000, 80000] }),
      posting({ role: "Data Analyst", salary: [70000, 90000] }),
      posting({ role: "Analytics Engineer", salary: [110000, 130000] }),
      posting({ role: "Data Analyst", salary: [1, 1], predicted: true }),
      posting({ role: "Data Analyst" }),
    ]);
    const body = await api.salaries({ min_postings: 1 });
    expect(body.groups).toEqual([
      { group: "Analytics Engineer", postings: 1, avg_min: 110000, avg_max: 130000, median_mid: 120000 },
      { group: "Data Analyst", postings: 2, avg_min: 65000, avg_max: 85000, median_mid: 75000 },
    ]);
    const byCity = await api.salaries({ group_by: "city", city: "austin", min_postings: 1 });
    expect(byCity.groups[0].group).toBe("Austin");
  });

  it("paginates postings newest first with filters", async () => {
    const api = make([0, 1, 2, 3, 4].map((d) => posting({ days: d, title: `Posting ${d}`, skills: d % 2 ? ["dbt"] : [] })));
    const page = await api.postings({ page: 1, page_size: 2 });
    expect(page).toMatchObject({ total: 5, pages: 3 });
    expect(page.items.map((p) => p.title)).toEqual(["Posting 0", "Posting 1"]);
    expect(page.items[0]).not.toHaveProperty("postedMs");
    expect((await api.postings({ skill: "DBT" })).total).toBe(2);
    expect((await api.postings({ q: "posting 3" })).total).toBe(1);
  });

  it("computes the skill gap", async () => {
    const api = make([
      posting({ skills: ["SQL", "Python", "dbt"] }),
      posting({ skills: ["SQL", "Tableau"] }),
      posting({ skills: ["SQL", "dbt"] }),
    ]);
    const body = await api.skillGap({ skills: ["sql", "Tableau", "juggling"] });
    expect(body.top_skills.map((s) => s.skill)).toEqual(["SQL", "dbt", "Python", "Tableau"]);
    expect(body.missing.map((s) => s.skill)).toEqual(["dbt", "Python"]);
    expect(body.coverage).toBe(0.5);
    expect(body.unrecognized).toEqual(["juggling"]);
  });
});

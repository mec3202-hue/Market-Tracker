import { describe, expect, it } from "vitest";
import { createStaticApi, decodeFacts } from "../staticApi.js";

const NOW = Date.parse("2026-09-28T12:00:00Z");
const daysAgo = (d) => NOW - d * 86400000;

let n = 0;
const posting = ({
  skills = [],
  role = "Data Analyst",
  state = "Texas",
  city = "Austin",
  work_mode = "onsite",
  days = 1,
  salary = [null, null],
  predicted = false,
  title,
} = {}) => {
  n += 1;
  return {
    id: `p-${String(n).padStart(3, "0")}`,
    title: title ?? `${role} ${n}`,
    company: "Acme",
    location: `${city}, ${state}`,
    city,
    state,
    role,
    work_mode,
    salary_min: salary[0],
    salary_max: salary[1],
    salary_is_predicted: predicted,
    url: null,
    posted_at: new Date(daysAgo(days)).toISOString(),
    postedMs: daysAgo(days),
    skills,
    snippet: "",
  };
};

const SKILLS = [
  { name: "SQL", category: "Languages" },
  { name: "Python", category: "Languages" },
  { name: "dbt", category: "Data Engineering" },
  { name: "Tableau", category: "BI & Visualization" },
];

// The same rows serve as both chart facts and detailed postings in tests.
const make = (postings) =>
  createStaticApi(
    { meta: { roles: [] }, skills: SKILLS, facts: postings, postings },
    { now: () => NOW },
  );

describe("decodeFacts", () => {
  it("expands indexed rows", () => {
    const [row] = decodeFacts({
      fields: ["posted", "role", "state", "city", "work_mode", "salary_min", "salary_max", "salary_is_predicted", "skills"],
      dims: { roles: ["Data Analyst"], states: ["Texas"], cities: [], work_modes: ["remote"], skills: ["SQL", "dbt"] },
      rows: [[1790000000, 0, 0, -1, 0, 90000, null, 1, [1, 0]]],
    });
    expect(row).toEqual({
      postedMs: 1790000000000,
      role: "Data Analyst",
      state: "Texas",
      city: null,
      work_mode: "remote",
      salary_min: 90000,
      salary_max: null,
      salary_is_predicted: true,
      skills: ["dbt", "SQL"],
    });
  });
});

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
  });

  it("applies role, state, city, and work-setting scope", async () => {
    const api = make([
      posting({ skills: ["dbt"], role: "Analytics Engineer", state: "California", city: "Los Angeles", work_mode: "remote" }),
      posting({ skills: ["SQL"], role: "Business Analyst" }),
    ]);
    const skillsFor = async (scope) => (await api.trending(scope)).skills.map((s) => s.skill);
    expect(await skillsFor({ role: "Analytics Engineer" })).toEqual(["dbt"]);
    expect(await skillsFor({ state: "california" })).toEqual(["dbt"]);
    expect(await skillsFor({ city: "Austin" })).toEqual(["SQL"]);
    expect(await skillsFor({ work_mode: "remote" })).toEqual(["dbt"]);
    expect(await skillsFor({ role: "", state: "", city: "", work_mode: "" })).toHaveLength(2);
  });

  it("groups salaries by role, state, and work setting", async () => {
    const api = make([
      posting({ role: "Data Analyst", salary: [60000, 80000] }),
      posting({ role: "Data Analyst", salary: [70000, 90000], work_mode: "remote" }),
      posting({ role: "Analytics Engineer", state: "California", salary: [110000, 130000] }),
      posting({ role: "Data Analyst", salary: [1, 1], predicted: true }),
      posting({ role: "Data Analyst" }),
    ]);
    const body = await api.salaries({ min_postings: 1 });
    expect(body.groups).toEqual([
      { group: "Analytics Engineer", postings: 1, avg_min: 110000, avg_max: 130000, median_mid: 120000 },
      { group: "Data Analyst", postings: 2, avg_min: 65000, avg_max: 85000, median_mid: 75000 },
    ]);
    const byState = await api.salaries({ group_by: "state", min_postings: 1 });
    expect(byState.groups.map((g) => g.group)).toEqual(["California", "Texas"]);
    const byMode = await api.salaries({ group_by: "work_mode", min_postings: 1 });
    expect(byMode.groups.map((g) => [g.group, g.median_mid])).toEqual([["onsite", 95000], ["remote", 80000]]);
  });

  it("summarizes locations and work settings", async () => {
    const api = make([
      posting({ state: "California", city: "Los Angeles", work_mode: "remote", salary: [100000, 100000] }),
      posting({ state: "California", city: "San Diego", salary: [80000, 80000] }),
      posting({ state: "Texas", work_mode: "hybrid" }),
      posting({ state: null, city: null, work_mode: "remote" }),
    ]);
    const body = await api.locations({});
    expect(body.group_by).toBe("state");
    expect(body.work_modes).toEqual([
      { work_mode: "remote", postings: 2, share: 0.5 },
      { work_mode: "hybrid", postings: 1, share: 0.25 },
      { work_mode: "onsite", postings: 1, share: 0.25 },
    ]);
    expect(body.groups[0]).toEqual({
      name: "California",
      postings: 2,
      share: 0.5,
      remote_share: 0.5,
      median_salary: 90000,
      salary_postings: 2,
    });
    expect(body.groups[1]).toMatchObject({ name: "Texas", median_salary: null });

    const cities = await api.locations({ state: "California" });
    expect(cities.group_by).toBe("city");
    expect(cities.groups.map((g) => g.name)).toEqual(["Los Angeles", "San Diego"]);
  });

  it("paginates postings newest first with filters", async () => {
    const api = make(
      [0, 1, 2, 3, 4].map((d) =>
        posting({ days: d, title: `Posting ${d}`, skills: d % 2 ? ["dbt"] : [], work_mode: d === 0 ? "remote" : "onsite" }),
      ),
    );
    const page = await api.postings({ page: 1, page_size: 2 });
    expect(page).toMatchObject({ total: 5, pages: 3 });
    expect(page.items.map((p) => p.title)).toEqual(["Posting 0", "Posting 1"]);
    expect(page.items[0]).not.toHaveProperty("postedMs");
    expect((await api.postings({ skill: "DBT" })).total).toBe(2);
    expect((await api.postings({ q: "posting 3" })).total).toBe(1);
    expect((await api.postings({ work_mode: "remote" })).total).toBe(1);
  });

  it("computes the skill gap within the scope", async () => {
    const api = make([
      posting({ skills: ["SQL", "Python", "dbt"] }),
      posting({ skills: ["SQL", "Tableau"] }),
      posting({ skills: ["SQL", "dbt"] }),
      posting({ skills: ["Tableau"], state: "Ohio" }),
    ]);
    const body = await api.skillGap({ skills: ["sql", "Tableau", "juggling"], state: "Texas" });
    expect(body.top_skills.map((s) => s.skill)).toEqual(["SQL", "dbt", "Python", "Tableau"]);
    expect(body.missing.map((s) => s.skill)).toEqual(["dbt", "Python"]);
    expect(body.coverage).toBe(0.5);
    expect(body.unrecognized).toEqual(["juggling"]);
  });
});

describe("round", () => {
  it("matches Python's round()", async () => {
    const { round } = await import("../staticApi.js");
    // Expected values from Python 3.
    expect(round(75 / 96, 4)).toBe(0.7812); // exact tie -> even
    expect(round(0.78135, 4)).toBe(0.7813); // 0.78135 is stored just below the half
    expect(round(0.15625, 4)).toBe(0.1562);
    expect(round(0.1, 4)).toBe(0.1);
    expect(round(-0.0641, 4)).toBe(-0.0641);
    expect(round(-75 / 96, 4)).toBe(-0.7812);
    expect(round(2 / 3, 4)).toBe(0.6667);
    expect(round(83700.5, 0)).toBe(83700);
    expect(round(83701.5, 0)).toBe(83702);
    expect(round(83700.49999, 0)).toBe(83700);
    expect(round(1, 4)).toBe(1);
    expect(round(0, 4)).toBe(0);
  });
});

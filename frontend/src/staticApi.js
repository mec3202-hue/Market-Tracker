/**
 * The API, computed in the browser from JSON files exported by
 * `python -m app.export_static`. Used when the site is hosted without a
 * backend (e.g. GitHub Pages). Mirrors the FastAPI endpoints' logic and
 * response shapes, so components don't know which one they're talking to.
 */

const DAY_MS = 24 * 60 * 60 * 1000;

const round = (value, digits = 4) => Math.round(value * 10 ** digits) / 10 ** digits;
const sinceMs = (days, now) => now - days * DAY_MS;
const eqi = (a, b) => (a ?? "").toLowerCase() === (b ?? "").toLowerCase();

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

const mean = (values) => values.reduce((sum, v) => sum + v, 0) / values.length;

// Python-style round-half-to-even, to match the API's round() exactly.
function roundHalfEven(value) {
  const floor = Math.floor(value);
  const diff = value - floor;
  if (Math.abs(diff - 0.5) > 1e-9) return Math.round(value);
  return floor % 2 === 0 ? floor : floor + 1;
}

/** Build the API from already-loaded data. `now` is injectable for tests. */
export function createStaticApi({ meta, skills, postings }, { now = () => Date.now() } = {}) {
  const rows = postings.map((p) => ({ ...p, postedMs: Date.parse(p.posted_at) }));
  const categoryOf = new Map(skills.map((s) => [s.name, s.category]));
  const canonical = new Map(skills.map((s) => [s.name.toLowerCase(), s.name]));

  function skillCounts(startMs, endMs, role) {
    let total = 0;
    const counts = new Map();
    for (const p of rows) {
      if (p.postedMs < startMs || (endMs != null && p.postedMs >= endMs)) continue;
      if (role && p.role !== role) continue;
      total += 1;
      for (const s of p.skills) counts.set(s, (counts.get(s) ?? 0) + 1);
    }
    return { total, counts };
  }

  const byCountThenName = ([a, ca], [b, cb]) => cb - ca || (a < b ? -1 : a > b ? 1 : 0);

  return {
    filters: async () => meta,

    skills: async () => skills,

    trending: async ({ role = "", days = 30, limit = 20 } = {}) => {
      const t = now();
      const current = skillCounts(sinceMs(days, t), null, role);
      const previous = skillCounts(sinceMs(2 * days, t), sinceMs(days, t), role);
      const list = [...current.counts].sort(byCountThenName).slice(0, limit);
      return {
        days,
        role: role || null,
        total_postings: current.total,
        previous_total_postings: previous.total,
        skills: list.map(([skill, count]) => {
          const share = current.total ? count / current.total : 0;
          const prevShare = previous.total ? (previous.counts.get(skill) ?? 0) / previous.total : 0;
          return {
            skill,
            category: categoryOf.get(skill) ?? "Other",
            count,
            share: round(share),
            previous_share: round(prevShare),
            change: round(share - prevShare),
          };
        }),
      };
    },

    salaries: async ({
      role = "",
      city = "",
      group_by = "role",
      days = 90,
      include_predicted = false,
      min_postings = 3,
      limit = 20,
    } = {}) => {
      const start = sinceMs(days, now());
      const buckets = new Map();
      for (const p of rows) {
        if (p.postedMs < start || (p.salary_min == null && p.salary_max == null)) continue;
        if (role && p.role !== role) continue;
        if (city && !eqi(p.city, city)) continue;
        if (!include_predicted && p.salary_is_predicted) continue;
        const key = group_by === "role" ? p.role : p.city;
        if (key == null) continue;
        const lo = p.salary_min ?? p.salary_max;
        const hi = p.salary_max ?? p.salary_min;
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push([lo, hi]);
      }
      const groups = [...buckets]
        .filter(([, ranges]) => ranges.length >= min_postings)
        .map(([group, ranges]) => ({
          group,
          postings: ranges.length,
          avg_min: roundHalfEven(mean(ranges.map(([lo]) => lo))),
          avg_max: roundHalfEven(mean(ranges.map(([, hi]) => hi))),
          median_mid: roundHalfEven(median(ranges.map(([lo, hi]) => (lo + hi) / 2))),
        }))
        .sort((a, b) => b.median_mid - a.median_mid || (a.group < b.group ? -1 : 1))
        .slice(0, limit);
      return { group_by, role: role || null, city: city || null, include_predicted, groups };
    },

    postings: async ({ skill = "", role = "", city = "", q = "", page = 1, page_size = 20 } = {}) => {
      const needle = q.trim().toLowerCase();
      const matches = rows
        .filter(
          (p) =>
            (!skill || p.skills.includes(canonical.get(skill.toLowerCase()) ?? skill)) &&
            (!role || p.role === role) &&
            (!city || eqi(p.city, city)) &&
            (!needle || p.title.toLowerCase().includes(needle)),
        )
        .sort((a, b) => b.postedMs - a.postedMs || (a.id < b.id ? -1 : 1));
      const start = (page - 1) * page_size;
      return {
        total: matches.length,
        page,
        page_size,
        pages: Math.ceil(matches.length / page_size),
        items: matches.slice(start, start + page_size).map(({ postedMs: _, ...p }) => p),
      };
    },

    skillGap: async ({ skills: mine = [], role = null, days = 90, top_n = 15 } = {}) => {
      const have = new Set();
      const unrecognized = [];
      for (const raw of mine) {
        const name = canonical.get(raw.trim().toLowerCase());
        if (name) have.add(name);
        else if (raw.trim()) unrecognized.push(raw.trim().slice(0, 60));
      }
      const { total, counts } = skillCounts(sinceMs(days, now()), null, role);
      const top = [...counts]
        .sort(byCountThenName)
        .slice(0, top_n)
        .map(([skill, count]) => ({
          skill,
          category: categoryOf.get(skill) ?? "Other",
          share: total ? round(count / total) : 0,
          have: have.has(skill),
        }));
      return {
        role: role || null,
        total_postings: total,
        coverage: top.length ? round(top.filter((s) => s.have).length / top.length) : 0,
        top_skills: top,
        missing: top.filter((s) => !s.have),
        unrecognized,
      };
    },
  };
}

/** Lazily fetch the exported JSON once, then answer every call from memory. */
export function loadStaticApi(baseUrl) {
  let ready;
  const load = () => {
    ready ??= Promise.all(
      ["meta", "skills", "postings"].map((name) =>
        fetch(`${baseUrl}data/${name}.json`).then((res) => {
          if (!res.ok) throw new Error(`Couldn't load ${name}.json (${res.status})`);
          return res.json();
        }),
      ),
    ).then(([meta, skills, postings]) => createStaticApi({ meta, skills, postings }));
    return ready;
  };
  const method = (name) => async (params) => (await load())[name](params);
  return Object.fromEntries(
    ["filters", "skills", "trending", "salaries", "postings", "skillGap"].map((n) => [n, method(n)]),
  );
}

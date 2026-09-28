/**
 * The API, computed in the browser from JSON files exported by
 * `python -m app.export_static`. Used when the site is hosted without a
 * backend (e.g. GitHub Pages). Mirrors the FastAPI endpoints' logic and
 * response shapes, so components don't know which one they're talking to.
 */

const DAY_MS = 24 * 60 * 60 * 1000;
const WORK_MODES = ["remote", "hybrid", "onsite"];

/**
 * Python's round(): uses the float's exact decimal value, and sends exact
 * ties to the even digit (round(0.78125, 4) == 0.7812), so shares and
 * salaries match the API to the last digit.
 */
export function round(value, digits = 4) {
  if (!Number.isFinite(value)) return value;
  const exact = Math.abs(value).toFixed(100); // the double's exact decimal expansion
  const dot = exact.indexOf(".");
  const kept = exact.slice(0, dot + 1 + digits);
  const rest = exact.slice(dot + 1 + digits);
  const lastKept = Number(digits ? kept.at(-1) : exact[dot - 1]);
  const up =
    rest[0] > "5" ||
    (rest[0] === "5" && (/[1-9]/.test(rest.slice(1)) || lastKept % 2 === 1));
  const magnitude = Number(kept) + (up ? 10 ** -digits : 0);
  const result = Number(magnitude.toFixed(digits));
  return value < 0 ? -result : result;
}
const sinceMs = (days, now) => now - days * DAY_MS;
const eqi = (a, b) => (a ?? "").toLowerCase() === (b ?? "").toLowerCase();
const byName = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

const mean = (values) => values.reduce((sum, v) => sum + v, 0) / values.length;

const roundHalfEven = (value) => round(value, 0);

/** Expand facts.json's indexed rows into plain objects. */
export function decodeFacts({ fields, dims, rows }) {
  const at = Object.fromEntries(fields.map((f, i) => [f, i]));
  const pick = (list, i) => (i >= 0 ? list[i] : null);
  return rows.map((r) => ({
    postedMs: r[at.posted] * 1000,
    role: dims.roles[r[at.role]],
    state: pick(dims.states, r[at.state]),
    city: pick(dims.cities, r[at.city]),
    work_mode: pick(dims.work_modes, r[at.work_mode]),
    salary_min: r[at.salary_min],
    salary_max: r[at.salary_max],
    salary_is_predicted: Boolean(r[at.salary_is_predicted]),
    skills: r[at.skills].map((i) => dims.skills[i]),
  }));
}

/**
 * Build the API from already-loaded data.
 * `facts`: decoded rows for aggregates; `postings`: detailed rows for the list.
 * `now` is injectable for tests.
 */
export function createStaticApi({ meta, skills, facts, postings }, { now = () => Date.now() } = {}) {
  const details = postings.map((p) => ({ ...p, postedMs: Date.parse(p.posted_at) }));
  const categoryOf = new Map(skills.map((s) => [s.name, s.category]));
  const canonical = new Map(skills.map((s) => [s.name.toLowerCase(), s.name]));

  const inScope = (p, { role, state, city, work_mode }) =>
    (!role || eqi(p.role, role)) &&
    (!state || eqi(p.state, state)) &&
    (!city || eqi(p.city, city)) &&
    (!work_mode || p.work_mode === work_mode);

  const inWindow = (p, startMs, endMs) =>
    p.postedMs >= startMs && (endMs == null || p.postedMs < endMs);

  function skillCounts(startMs, endMs, scope) {
    let total = 0;
    const counts = new Map();
    for (const p of facts) {
      if (!inWindow(p, startMs, endMs) || !inScope(p, scope)) continue;
      total += 1;
      for (const s of p.skills) counts.set(s, (counts.get(s) ?? 0) + 1);
    }
    return { total, counts };
  }

  function salaryRanges(scope, days, includePredicted, groupBy) {
    const start = sinceMs(days, now());
    const buckets = new Map();
    for (const p of facts) {
      if (p.postedMs < start || (p.salary_min == null && p.salary_max == null)) continue;
      if (!inScope(p, scope) || (!includePredicted && p.salary_is_predicted)) continue;
      const key = p[groupBy];
      if (key == null) continue;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push([p.salary_min ?? p.salary_max, p.salary_max ?? p.salary_min]);
    }
    return buckets;
  }

  const medianMid = (ranges) => roundHalfEven(median(ranges.map(([lo, hi]) => (lo + hi) / 2)));
  const byCountThenName = ([a, ca], [b, cb]) => cb - ca || byName(a, b);

  return {
    filters: async () => meta,

    skills: async () => skills,

    trending: async ({ days = 30, limit = 20, ...scope } = {}) => {
      const t = now();
      const current = skillCounts(sinceMs(days, t), null, scope);
      const previous = skillCounts(sinceMs(2 * days, t), sinceMs(days, t), scope);
      const list = [...current.counts].sort(byCountThenName).slice(0, limit);
      return {
        days,
        role: scope.role || null,
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
      group_by = "role",
      days = 90,
      include_predicted = false,
      min_postings = 3,
      limit = 20,
      ...scope
    } = {}) => {
      const groups = [...salaryRanges(scope, days, include_predicted, group_by)]
        .filter(([, ranges]) => ranges.length >= min_postings)
        .map(([group, ranges]) => ({
          group,
          postings: ranges.length,
          avg_min: roundHalfEven(mean(ranges.map(([lo]) => lo))),
          avg_max: roundHalfEven(mean(ranges.map(([, hi]) => hi))),
          median_mid: medianMid(ranges),
        }))
        .sort((a, b) => b.median_mid - a.median_mid || byName(a.group, b.group))
        .slice(0, limit);
      return {
        group_by,
        role: scope.role || null,
        city: scope.city || null,
        include_predicted,
        groups,
      };
    },

    locations: async ({ days = 90, limit = 25, ...scope } = {}) => {
      const groupBy = scope.state ? "city" : "state";
      const start = sinceMs(days, now());
      // The work-setting split ignores the work_mode filter; the rest respects it.
      const splitScope = { ...scope, work_mode: "" };
      let total = 0;
      let splitTotal = 0;
      const modes = new Map();
      const perPlace = new Map();
      const remotePerPlace = new Map();
      for (const p of facts) {
        if (p.postedMs < start || !inScope(p, splitScope)) continue;
        splitTotal += 1;
        modes.set(p.work_mode, (modes.get(p.work_mode) ?? 0) + 1);
        if (!inScope(p, scope)) continue;
        total += 1;
        const place = p[groupBy];
        if (place == null) continue;
        perPlace.set(place, (perPlace.get(place) ?? 0) + 1);
        if (p.work_mode === "remote") remotePerPlace.set(place, (remotePerPlace.get(place) ?? 0) + 1);
      }
      const salaries = salaryRanges(scope, days, false, groupBy);
      return {
        days,
        group_by: groupBy,
        state: scope.state || null,
        total_postings: total,
        work_modes: WORK_MODES.map((mode) => ({
          work_mode: mode,
          postings: modes.get(mode) ?? 0,
          share: splitTotal ? round((modes.get(mode) ?? 0) / splitTotal) : 0,
        })),
        groups: [...perPlace]
          .sort(byCountThenName)
          .slice(0, limit)
          .map(([name, count]) => ({
            name,
            postings: count,
            share: total ? round(count / total) : 0,
            remote_share: round((remotePerPlace.get(name) ?? 0) / count),
            median_salary: salaries.get(name) ? medianMid(salaries.get(name)) : null,
            salary_postings: salaries.get(name)?.length ?? 0,
          })),
      };
    },

    postings: async ({ skill = "", q = "", page = 1, page_size = 20, ...scope } = {}) => {
      const needle = q.trim().toLowerCase();
      const wanted = skill ? (canonical.get(skill.toLowerCase()) ?? skill) : null;
      const matches = details
        .filter(
          (p) =>
            inScope(p, scope) &&
            (!wanted || p.skills.includes(wanted)) &&
            (!needle || p.title.toLowerCase().includes(needle)),
        )
        .sort((a, b) => b.postedMs - a.postedMs || byName(a.id, b.id));
      const start = (page - 1) * page_size;
      return {
        total: matches.length,
        page,
        page_size,
        pages: Math.ceil(matches.length / page_size),
        items: matches.slice(start, start + page_size).map(({ postedMs: _, ...p }) => p),
      };
    },

    skillGap: async ({ skills: mine = [], days = 90, top_n = 15, ...scope } = {}) => {
      const have = new Set();
      const unrecognized = [];
      for (const raw of mine) {
        const name = canonical.get(raw.trim().toLowerCase());
        if (name) have.add(name);
        else if (raw.trim()) unrecognized.push(raw.trim().slice(0, 60));
      }
      const { total, counts } = skillCounts(sinceMs(days, now()), null, scope);
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
        role: scope.role || null,
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
      ["meta", "skills", "facts", "postings"].map((name) =>
        fetch(`${baseUrl}data/${name}.json`).then((res) => {
          if (!res.ok) throw new Error(`Couldn't load ${name}.json (${res.status})`);
          return res.json();
        }),
      ),
    ).then(([meta, skills, facts, postings]) =>
      createStaticApi({ meta, skills, facts: decodeFacts(facts), postings }),
    );
    return ready;
  };
  const method = (name) => async (params) => (await load())[name](params);
  return Object.fromEntries(
    ["filters", "skills", "trending", "salaries", "locations", "postings", "skillGap"].map((n) => [
      n,
      method(n),
    ]),
  );
}

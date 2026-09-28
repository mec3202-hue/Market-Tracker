import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { formatPct } from "../format.js";
import { useApi } from "../useApi.js";
import { Select, Status } from "./Controls.jsx";

const STORAGE_KEY = "market-tracker:my-skills";

function loadSaved() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export default function SkillGap({ filters }) {
  const [mine, setMine] = useState(loadSaved);
  const [role, setRole] = useState("");
  const catalog = useApi(() => api.skills(), []);
  const gap = useApi(() => api.skillGap({ skills: mine, role: role || null, top_n: 15 }), [mine, role]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(mine));
    } catch {
      // storage unavailable; the checker still works for this visit
    }
  }, [mine]);

  const byCategory = useMemo(() => {
    const groups = new Map();
    for (const s of catalog.data ?? []) {
      if (!groups.has(s.category)) groups.set(s.category, []);
      groups.get(s.category).push(s.name);
    }
    return [...groups];
  }, [catalog.data]);

  const toggle = (name) =>
    setMine((cur) => (cur.includes(name) ? cur.filter((s) => s !== name) : [...cur, name]));

  const result = gap.data;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Skill gap checker</h2>
          <p className="muted">
            Pick the skills you have. We compare them with the 15 skills that show up most in
            recent postings.
          </p>
        </div>
        <div className="filters">
          <Select label="Target role" value={role} onChange={setRole} options={filters?.roles ?? []} allLabel="All roles" />
        </div>
      </div>

      <div className="gap-layout">
        <div className="skill-picker">
          <div className="picker-head">
            <h3>Your skills ({mine.length})</h3>
            {mine.length > 0 && (
              <button type="button" className="link" onClick={() => setMine([])}>
                Clear
              </button>
            )}
          </div>
          <Status loading={catalog.loading} error={catalog.error} />
          {byCategory.map(([category, names]) => (
            <fieldset key={category}>
              <legend>{category}</legend>
              <div className="chips">
                {names.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className={mine.includes(name) ? "chip selected" : "chip"}
                    aria-pressed={mine.includes(name)}
                    onClick={() => toggle(name)}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </fieldset>
          ))}
        </div>

        <div className="gap-result">
          <Status
            loading={gap.loading && !result}
            error={gap.error}
            empty={result && result.top_skills.length === 0}
          />
          {result && result.top_skills.length > 0 && (
            <>
              <div className="stat">
                <div className="stat-value">{formatPct(result.coverage)}</div>
                <div className="muted">
                  of the top {result.top_skills.length} skills
                  {result.role ? ` for ${result.role}` : ""} covered
                </div>
              </div>

              <h3>Learn next</h3>
              {result.missing.length === 0 ? (
                <p className="muted">You have every top skill. Nice.</p>
              ) : (
                <ol className="missing" aria-label="Skills to learn next">
                  {result.missing.map((s) => (
                    <li key={s.skill}>
                      <span>{s.skill}</span>
                      <span className="muted">in {formatPct(s.share)} of postings</span>
                      <button type="button" className="link" onClick={() => toggle(s.skill)}>
                        I have this
                      </button>
                    </li>
                  ))}
                </ol>
              )}

              <h3>Top skills in demand</h3>
              <ul className="top-skills">
                {result.top_skills.map((s) => (
                  <li key={s.skill} className={s.have ? "have" : ""}>
                    <span className="mark" aria-hidden="true">{s.have ? "✓" : "○"}</span>
                    <span className="name">
                      {s.skill}
                      <span className="sr-only">{s.have ? " (you have this)" : " (missing)"}</span>
                    </span>
                    <span className="meter" aria-hidden="true">
                      <span style={{ width: formatPct(s.share, 1) }} />
                    </span>
                    <span className="num">{formatPct(s.share)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

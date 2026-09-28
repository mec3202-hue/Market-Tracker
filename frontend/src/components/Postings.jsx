import { useEffect, useState } from "react";
import { api, isStatic } from "../api.js";
import { formatDate, formatSalaryRange } from "../format.js";
import { useApi } from "../useApi.js";
import { describeScope, Select, Status, WORK_MODE_LABELS } from "./Controls.jsx";

const PAGE_SIZE = 20;

function useDebounced(value, ms = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function Postings({ filters, scope }) {
  const [skill, setSkill] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounced(search.trim().length >= 2 ? search.trim() : "");
  const catalog = useApi(() => api.skills(), []);

  const { data, error, loading } = useApi(
    () => api.postings({ ...scope, skill, q, page, page_size: PAGE_SIZE }),
    [scope, skill, q, page],
  );

  // Back to page 1 whenever the shared filters change.
  const scopeKey = JSON.stringify(scope);
  const [lastScopeKey, setLastScopeKey] = useState(scopeKey);
  if (scopeKey !== lastScopeKey) {
    setLastScopeKey(scopeKey);
    setPage(1);
  }

  const update = (setter) => (value) => {
    setter(value);
    setPage(1);
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Postings</h2>
          <p className="muted">
            {data ? `${data.total.toLocaleString()} matching postings · ${describeScope(scope)}` : "\u00a0"}
            {isStatic && filters?.detail_limit && filters.total_postings > filters.detail_limit
              ? ` · searching the ${filters.detail_limit.toLocaleString()} most recent`
              : ""}
          </p>
        </div>
        <div className="filters">
          <Select
            label="Skill"
            value={skill}
            onChange={update(setSkill)}
            options={(catalog.data ?? []).map((s) => s.name)}
            allLabel="Any skill"
          />
          <label className="field">
            <span>Title search</span>
            <input
              type="search"
              value={search}
              maxLength={100}
              placeholder="e.g. senior"
              onChange={(e) => update(setSearch)(e.target.value)}
            />
          </label>
        </div>
      </div>

      <Status loading={loading && !data} error={error} empty={data && data.total === 0} emptyText="No postings match these filters." />

      {data && data.items.length > 0 && (
        <>
          <ul className="postings">
            {data.items.map((p) => (
              <li key={p.id} className="posting">
                <div className="posting-head">
                  <div>
                    <h3>{p.url ? <a href={p.url} target="_blank" rel="noreferrer">{p.title}</a> : p.title}</h3>
                    <div className="muted">
                      {[p.company, p.location].filter(Boolean).join(" · ")}
                    </div>
                  </div>
                  <div className="posting-meta">
                    {formatSalaryRange(p.salary_min, p.salary_max) && (
                      <div className="salary">
                        {formatSalaryRange(p.salary_min, p.salary_max)}
                        {p.salary_is_predicted && <span className="muted small"> est.</span>}
                      </div>
                    )}
                    <div className="muted small">{formatDate(p.posted_at)}</div>
                  </div>
                </div>
                <p className="snippet">{p.snippet}</p>
                <div className="chips">
                  <span className="chip role">{p.role}</span>
                  {p.work_mode && p.work_mode !== "onsite" && (
                    <span className={`chip mode ${p.work_mode}`}>{WORK_MODE_LABELS[p.work_mode]}</span>
                  )}
                  {p.skills.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={s === skill ? "chip selected" : "chip"}
                      onClick={() => update(setSkill)(s === skill ? "" : s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>

          <nav className="pager" aria-label="Pagination">
            <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ← Previous
            </button>
            <span className="muted">
              Page {data.page} of {data.pages}
            </span>
            <button type="button" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
              Next →
            </button>
          </nav>
        </>
      )}
    </section>
  );
}

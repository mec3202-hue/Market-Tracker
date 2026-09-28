import { useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDate, formatSalaryRange } from "../format.js";
import { useApi } from "../useApi.js";
import { Select, Status } from "./Controls.jsx";

const PAGE_SIZE = 20;

function useDebounced(value, ms = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function Postings({ filters }) {
  const [skill, setSkill] = useState("");
  const [role, setRole] = useState("");
  const [city, setCity] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounced(search.trim().length >= 2 ? search.trim() : "");
  const catalog = useApi(() => api.skills(), []);

  const { data, error, loading } = useApi(
    () => api.postings({ skill, role, city, q, page, page_size: PAGE_SIZE }),
    [skill, role, city, q, page],
  );

  const update = (setter) => (value) => {
    setter(value);
    setPage(1);
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Postings</h2>
          <p className="muted">{data ? `${data.total.toLocaleString()} matching postings` : " "}</p>
        </div>
        <div className="filters">
          <Select
            label="Skill"
            value={skill}
            onChange={update(setSkill)}
            options={(catalog.data ?? []).map((s) => s.name)}
            allLabel="Any skill"
          />
          <Select label="Role" value={role} onChange={update(setRole)} options={filters?.roles ?? []} allLabel="All roles" />
          <Select label="City" value={city} onChange={update(setCity)} options={filters?.cities ?? []} allLabel="All cities" />
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

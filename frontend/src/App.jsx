import { useState } from "react";
import { api } from "./api.js";
import { formatDate } from "./format.js";
import { useApi } from "./useApi.js";
import { EMPTY_SCOPE, ScopeBar } from "./components/Controls.jsx";
import TrendingSkills from "./components/TrendingSkills.jsx";
import Salaries from "./components/Salaries.jsx";
import Locations from "./components/Locations.jsx";
import SkillGap from "./components/SkillGap.jsx";
import Postings from "./components/Postings.jsx";

const TABS = [
  { id: "trending", label: "Trending skills", Component: TrendingSkills },
  { id: "salaries", label: "Salaries", Component: Salaries },
  { id: "locations", label: "Locations & remote", Component: Locations },
  { id: "gap", label: "Skill gap", Component: SkillGap },
  { id: "postings", label: "Postings", Component: Postings },
];

export default function App() {
  const [tab, setTab] = useState("trending");
  const [scope, setScope] = useState(EMPTY_SCOPE);
  const filters = useApi(() => api.filters(), []);
  const active = TABS.find((t) => t.id === tab);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Analytics Job Market Tracker</h1>
          <p className="muted">
            Skills, salaries, locations, and remote work in US analyst and data job postings.
          </p>
        </div>
        {filters.data && (
          <p className="freshness muted">
            {filters.data.total_postings.toLocaleString()} postings · updated{" "}
            {formatDate(filters.data.last_ingested_at)}
          </p>
        )}
      </header>

      <ScopeBar filters={filters.data} scope={scope} onChange={setScope} />

      <nav className="tabs" role="tablist" aria-label="Views">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? "tab active" : "tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main role="tabpanel" aria-label={active.label}>
        {filters.error ? (
          <div className="error">
            Couldn't reach the API: {filters.error.message}. Is the backend running?
          </div>
        ) : (
          <active.Component filters={filters.data} scope={scope} onScopeChange={setScope} />
        )}
      </main>

      <footer className="footer muted">
        Data from the Adzuna job search API. Skills and work settings are detected from posting
        text, so they reflect what postings mention. &ldquo;On-site / not stated&rdquo; includes
        postings that don&rsquo;t say.
      </footer>
    </div>
  );
}

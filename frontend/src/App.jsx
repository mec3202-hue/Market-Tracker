import { useState } from "react";
import { api } from "./api.js";
import { formatDate } from "./format.js";
import { useApi } from "./useApi.js";
import TrendingSkills from "./components/TrendingSkills.jsx";
import Salaries from "./components/Salaries.jsx";
import SkillGap from "./components/SkillGap.jsx";
import Postings from "./components/Postings.jsx";

const TABS = [
  { id: "trending", label: "Trending skills", Component: TrendingSkills },
  { id: "salaries", label: "Salaries", Component: Salaries },
  { id: "gap", label: "Skill gap", Component: SkillGap },
  { id: "postings", label: "Postings", Component: Postings },
];

export default function App() {
  const [tab, setTab] = useState("trending");
  const filters = useApi(() => api.filters(), []);
  const active = TABS.find((t) => t.id === tab);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Analytics Job Market Tracker</h1>
          <p className="muted">
            Skills, salaries, and roles in US analyst and data job postings.
          </p>
        </div>
        {filters.data && (
          <p className="freshness muted">
            {filters.data.total_postings.toLocaleString()} postings · updated{" "}
            {formatDate(filters.data.last_ingested_at)}
          </p>
        )}
      </header>

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
          <active.Component filters={filters.data} />
        )}
      </main>

      <footer className="footer muted">
        Data from the Adzuna job search API. Skills are matched from posting text, so counts
        reflect mentions, not requirements.
      </footer>
    </div>
  );
}

export function Select({ label, value, onChange, options, allLabel }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allLabel && <option value="">{allLabel}</option>}
        {options.map((opt) => {
          const { value: v, label: l } = typeof opt === "object" ? opt : { value: opt, label: opt };
          return (
            <option key={v} value={v}>
              {l}
            </option>
          );
        })}
      </select>
    </label>
  );
}

export function Segmented({ label, value, onChange, options }) {
  return (
    <div className="field">
      <span>{label}</span>
      <div className="segmented" role="radiogroup" aria-label={label}>
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={value === opt.value}
            className={value === opt.value ? "active" : ""}
            onClick={() => onChange(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Status({ loading, error, empty, emptyText = "No data for these filters yet." }) {
  if (error) return <div className="error">{error.message}</div>;
  if (loading) return <div className="placeholder muted">Loading…</div>;
  if (empty) return <div className="placeholder muted">{emptyText}</div>;
  return null;
}

export function ChartTooltip({ active, payload, render }) {
  if (!active || !payload?.length) return null;
  return <div className="tooltip">{render(payload[0].payload)}</div>;
}

export const WINDOW_OPTIONS = [
  { value: 7, label: "7d" },
  { value: 30, label: "30d" },
  { value: 90, label: "90d" },
];

export const WORK_MODE_LABELS = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site / not stated",
};

export const EMPTY_SCOPE = { role: "", state: "", city: "", work_mode: "" };

/** Filters shared by every view. */
export function ScopeBar({ filters, scope, onChange }) {
  const set = (patch) => onChange({ ...scope, ...patch });
  const cities = (filters?.cities ?? [])
    .filter((c) => !scope.state || c.state === scope.state)
    .map((c) => c.city);
  // Keep a selected city visible even if it isn't among the top cities.
  const cityOptions = [...new Set(scope.city ? [scope.city, ...cities] : cities)];
  const active = Object.values(scope).some(Boolean);

  return (
    <div className="scope-bar" role="group" aria-label="Filters for every view">
      <Select label="Role" value={scope.role} onChange={(role) => set({ role })} options={filters?.roles ?? []} allLabel="All roles" />
      <Select
        label="State"
        value={scope.state}
        onChange={(state) => {
          const city = filters?.cities.find((c) => c.city === scope.city);
          // Drop a city that isn't in the newly chosen state.
          set({ state, city: state && city && city.state !== state ? "" : scope.city });
        }}
        options={filters?.states ?? []}
        allLabel="All states"
      />
      <Select label="City" value={scope.city} onChange={(city) => set({ city })} options={cityOptions} allLabel={scope.state ? `All of ${scope.state}` : "All cities"} />
      <Segmented
        label="Work setting"
        value={scope.work_mode}
        onChange={(work_mode) => set({ work_mode })}
        options={[
          { value: "", label: "Any" },
          { value: "remote", label: "Remote" },
          { value: "hybrid", label: "Hybrid" },
          { value: "onsite", label: "On-site" },
        ]}
      />
      {active && (
        <button type="button" className="link reset" onClick={() => onChange(EMPTY_SCOPE)}>
          Clear filters
        </button>
      )}
    </div>
  );
}

/** One-line description of the current scope, e.g. "Remote · Data Analyst · Texas". */
export function describeScope(scope) {
  const parts = [
    scope.work_mode && WORK_MODE_LABELS[scope.work_mode],
    scope.role,
    scope.city ? `${scope.city}${scope.state ? `, ${scope.state}` : ""}` : scope.state,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "All postings";
}

/** Bars keep one thickness however many rows a chart has. */
export const BAR_SIZE = 18;
export const chartHeight = (rows, rowHeight) => Math.max(rows * rowHeight + 44, 110);

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

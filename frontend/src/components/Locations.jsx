import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { formatMoney, formatMoneyShort, formatPct, niceTicks } from "../format.js";
import { useApi } from "../useApi.js";
import {
  ChartTooltip,
  describeScope,
  Segmented,
  Status,
  WINDOW_OPTIONS,
  WORK_MODE_LABELS,
  BAR_SIZE,
  chartHeight,
} from "./Controls.jsx";

const ROW_HEIGHT = 28;
const LIMIT = 25;

export default function Locations({ scope, onScopeChange }) {
  const [days, setDays] = useState(90);
  const [asTable, setAsTable] = useState(false);
  const { data, error, loading } = useApi(
    () => api.locations({ ...scope, days, limit: LIMIT }),
    [scope, days],
  );

  const byCity = data?.group_by === "city";
  const groups = data?.groups ?? [];
  const place = byCity ? "City" : "State";
  const ticks = niceTicks(Math.max(0, ...groups.map((g) => g.postings)));

  // Clicking a state drills into its cities; clicking a city filters to it.
  const select = (name) =>
    onScopeChange(byCity ? { ...scope, city: name } : { ...scope, state: name, city: "" });

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{byCity ? `Cities in ${data.state}` : "Jobs by state"}</h2>
          <p className="muted">
            {describeScope(scope)}
            {data ? ` · ${data.total_postings.toLocaleString()} postings in the last ${days} days` : ""}
            {" · "}
            {byCity ? "click a city to filter to it" : "click a state to see its cities"}
          </p>
        </div>
        <div className="filters">
          {scope.state && (
            <button
              type="button"
              className="button"
              onClick={() => onScopeChange({ ...scope, state: "", city: "" })}
            >
              ← All states
            </button>
          )}
          <Segmented label="Window" value={days} onChange={setDays} options={WINDOW_OPTIONS} />
          <Segmented
            label="View"
            value={asTable}
            onChange={setAsTable}
            options={[
              { value: false, label: "Chart" },
              { value: true, label: "Table" },
            ]}
          />
        </div>
      </div>

      <Status loading={loading && !data} error={error} empty={data && data.total_postings === 0} />

      {data && data.total_postings > 0 && (
        <>
          <div className="tiles" aria-label="Work setting">
            {data.work_modes.map((m) => (
              <button
                type="button"
                key={m.work_mode}
                className={scope.work_mode === m.work_mode ? "tile selected" : "tile"}
                aria-pressed={scope.work_mode === m.work_mode}
                onClick={() =>
                  onScopeChange({
                    ...scope,
                    work_mode: scope.work_mode === m.work_mode ? "" : m.work_mode,
                  })
                }
              >
                <span className="tile-label">{WORK_MODE_LABELS[m.work_mode]}</span>
                <span className="tile-value">{formatPct(m.share)}</span>
                <span className="muted small">{m.postings.toLocaleString()} postings</span>
                <span className="meter" aria-hidden="true">
                  <span style={{ width: formatPct(m.share, 1) }} />
                </span>
              </button>
            ))}
          </div>

          {groups.length === 0 ? (
            <div className="placeholder muted">No location data for these filters.</div>
          ) : asTable ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>{place}</th>
                  <th className="num">Postings</th>
                  <th className="num">Share</th>
                  <th className="num">Remote</th>
                  <th className="num">Median salary</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr key={g.name}>
                    <td>
                      <button type="button" className="link" onClick={() => select(g.name)}>
                        {g.name}
                      </button>
                    </td>
                    <td className="num">{g.postings.toLocaleString()}</td>
                    <td className="num">{formatPct(g.share, 1)}</td>
                    <td className="num">{formatPct(g.remote_share)}</td>
                    <td className="num">
                      {g.median_salary == null ? "—" : formatMoney(g.median_salary)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="chart clickable" style={{ height: chartHeight(groups.length, ROW_HEIGHT) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={groups}
                  layout="vertical"
                  margin={{ top: 4, right: 56, bottom: 4, left: 8 }}
                  barCategoryGap={6}
                >
                  <CartesianGrid horizontal={false} className="grid" />
                  <XAxis
                    type="number"
                    domain={[0, ticks.at(-1)]}
                    ticks={ticks}
                    tickFormatter={(v) => v.toLocaleString()}
                    className="axis"
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis type="category" dataKey="name" width={130} className="axis" tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ className: "cursor" }}
                    content={
                      <ChartTooltip
                        render={(g) => (
                          <>
                            <strong>{g.name}</strong>
                            <div>
                              {g.postings.toLocaleString()} postings ({formatPct(g.share, 1)})
                            </div>
                            <div>{formatPct(g.remote_share)} remote</div>
                            <div className="muted">
                              {g.median_salary == null
                                ? "No posted salaries"
                                : `Median salary ${formatMoneyShort(g.median_salary)} (${g.salary_postings} posted)`}
                            </div>
                          </>
                        )}
                      />
                    }
                  />
                  <Bar
                    dataKey="postings"
                    className="series-1"
                    barSize={BAR_SIZE}
                    radius={[0, 4, 4, 0]}
                    isAnimationActive={false}
                    onClick={(entry) => select(entry.name ?? entry.payload?.name)}
                    label={{ position: "right", className: "bar-label", formatter: (v) => v.toLocaleString() }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="muted small note">
            Remote and hybrid are detected from each posting&rsquo;s text. Remote postings are
            counted under the location Adzuna lists, often the employer&rsquo;s office.
          </p>
        </>
      )}
    </section>
  );
}

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { formatChange, formatPct } from "../format.js";
import { useApi } from "../useApi.js";
import { BAR_SIZE, chartHeight, ChartTooltip, describeScope, Segmented, Status, WINDOW_OPTIONS } from "./Controls.jsx";

const ROW_HEIGHT = 28;
const LIMIT = 25;

export default function TrendingSkills({ scope }) {
  const [days, setDays] = useState(30);
  const [asTable, setAsTable] = useState(false);
  const { data, error, loading } = useApi(
    () => api.trending({ ...scope, days, limit: LIMIT }),
    [scope, days],
  );

  const skills = data?.skills ?? [];
  const movers =
    data?.previous_total_postings > 0
      ? [...skills].sort((a, b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, 5)
      : [];

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Most requested skills</h2>
          <p className="muted">
            Top {LIMIT} skills by share of postings · {describeScope(scope)}
            {data ? ` · ${data.total_postings.toLocaleString()} postings in the last ${days} days` : ""}
          </p>
        </div>
        <div className="filters">
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

      <Status loading={loading && !data} error={error} empty={!loading && !error && skills.length === 0} />

      {skills.length > 0 && (
        <div className="split">
          {asTable ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Category</th>
                  <th className="num">Postings</th>
                  <th className="num">Share</th>
                  <th className="num">vs. previous {days}d</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((s) => (
                  <tr key={s.skill}>
                    <td>{s.skill}</td>
                    <td className="muted">{s.category}</td>
                    <td className="num">{s.count.toLocaleString()}</td>
                    <td className="num">{formatPct(s.share)}</td>
                    <td className="num">{formatChange(s.change)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="chart" style={{ height: chartHeight(skills.length, ROW_HEIGHT) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={skills} layout="vertical" margin={{ top: 4, right: 48, bottom: 4, left: 8 }} barCategoryGap={6}>
                  <CartesianGrid horizontal={false} className="grid" />
                  <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => formatPct(v)} className="axis" tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="skill" width={120} className="axis" tickLine={false} axisLine={false} />
                  <Tooltip
                    cursor={{ className: "cursor" }}
                    content={
                      <ChartTooltip
                        render={(s) => (
                          <>
                            <strong>{s.skill}</strong>
                            <div>
                              {formatPct(s.share, 1)} of postings ({s.count.toLocaleString()})
                            </div>
                            <div className="muted">
                              {formatChange(s.change)} vs. previous {days} days
                            </div>
                          </>
                        )}
                      />
                    }
                  />
                  <Bar
                    dataKey="share"
                    className="series-1"
                    radius={[0, 4, 4, 0]}
                    barSize={BAR_SIZE}
                    isAnimationActive={false}
                    label={{ position: "right", className: "bar-label", formatter: (v) => formatPct(v) }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <aside className="movers">
            <h3>Biggest movers</h3>
            <p className="muted small">Change in share vs. the previous {days} days</p>
            {movers.length === 0 ? (
              <p className="muted small">Not enough history yet.</p>
            ) : (
              <ul>
                {movers.map((s) => (
                  <li key={s.skill}>
                    <span>{s.skill}</span>
                    <span className={s.change >= 0 ? "delta up" : "delta down"}>
                      <span aria-hidden="true">{s.change >= 0 ? "▲" : "▼"}</span> {formatChange(s.change)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}

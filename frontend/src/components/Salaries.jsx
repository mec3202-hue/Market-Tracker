import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { formatMoney, formatMoneyShort } from "../format.js";
import { useApi } from "../useApi.js";
import { BAR_SIZE, chartHeight, ChartTooltip, describeScope, Segmented, Status, WORK_MODE_LABELS } from "./Controls.jsx";

const ROW_HEIGHT = 32;
const GROUP_LABELS = { role: "role", state: "state", city: "city", work_mode: "work setting" };

export default function Salaries({ scope }) {
  const [groupBy, setGroupBy] = useState("role");
  const [includePredicted, setIncludePredicted] = useState(false);
  const [asTable, setAsTable] = useState(false);

  const { data, error, loading } = useApi(
    () =>
      api.salaries({
        ...scope,
        group_by: groupBy,
        include_predicted: includePredicted,
        limit: 25,
      }),
    [scope, groupBy, includePredicted],
  );

  const groups = (data?.groups ?? []).map((g) => ({
    ...g,
    group: groupBy === "work_mode" ? (WORK_MODE_LABELS[g.group] ?? g.group) : g.group,
    range: [g.avg_min, g.avg_max],
  }));
  // Ranges aren't measured from zero, so the axis hugs the data (in $20k steps).
  const STEP = 20000;
  const domain = [
    Math.max(0, Math.floor((Math.min(...groups.map((g) => g.avg_min)) * 0.95) / STEP) * STEP),
    Math.ceil((Math.max(...groups.map((g) => g.avg_max)) * 1.05) / STEP) * STEP,
  ];
  const ticks = [];
  for (let t = domain[0]; t <= domain[1]; t += STEP) ticks.push(t);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Salary by {GROUP_LABELS[groupBy]}</h2>
          <p className="muted">
            {describeScope(scope)} · bars span the average posted minimum to maximum; the tick
            marks the median midpoint.
          </p>
        </div>
        <div className="filters">
          <Segmented
            label="Group by"
            value={groupBy}
            onChange={setGroupBy}
            options={[
              { value: "role", label: "Role" },
              { value: "state", label: "State" },
              { value: "city", label: "City" },
              { value: "work_mode", label: "Work setting" },
            ]}
          />
          <label className="field checkbox">
            <input
              type="checkbox"
              checked={includePredicted}
              onChange={(e) => setIncludePredicted(e.target.checked)}
            />
            <span>Include estimated salaries</span>
          </label>
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

      <Status
        loading={loading && !data}
        error={error}
        empty={!loading && !error && groups.length === 0}
        emptyText="Not enough postings with salaries for these filters."
      />

      {groups.length > 0 &&
        (asTable ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>{GROUP_LABELS[groupBy][0].toUpperCase() + GROUP_LABELS[groupBy].slice(1)}</th>
                <th className="num">Postings</th>
                <th className="num">Avg. min</th>
                <th className="num">Avg. max</th>
                <th className="num">Median midpoint</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <tr key={g.group}>
                  <td>{g.group}</td>
                  <td className="num">{g.postings.toLocaleString()}</td>
                  <td className="num">{formatMoney(g.avg_min)}</td>
                  <td className="num">{formatMoney(g.avg_max)}</td>
                  <td className="num">{formatMoney(g.median_mid)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="chart" style={{ height: chartHeight(groups.length, ROW_HEIGHT) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={groups} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }} barCategoryGap={8}>
                <CartesianGrid horizontal={false} className="grid" />
                <XAxis
                  type="number"
                  allowDataOverflow
                  domain={domain}
                  ticks={ticks}
                  tickFormatter={formatMoneyShort}
                  className="axis"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis type="category" dataKey="group" width={150} className="axis" tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ className: "cursor" }}
                  content={
                    <ChartTooltip
                      render={(g) => (
                        <>
                          <strong>{g.group}</strong>
                          <div>
                            {formatMoney(g.avg_min)} – {formatMoney(g.avg_max)}
                          </div>
                          <div>Median midpoint {formatMoney(g.median_mid)}</div>
                          <div className="muted">{g.postings.toLocaleString()} postings</div>
                        </>
                      )}
                    />
                  }
                />
                <Bar dataKey="range" className="series-1" radius={4} barSize={BAR_SIZE}
                    isAnimationActive={false} shape={<RangeBar />} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
    </section>
  );
}

/** A floating bar from avg_min to avg_max with a tick at the median midpoint. */
function RangeBar({ x, y, width, height, payload }) {
  if (width == null || !payload) return null;
  const [lo, hi] = payload.range;
  const midX = hi === lo ? x : x + ((payload.median_mid - lo) / (hi - lo)) * width;
  return (
    <g>
      <rect x={x} y={y} width={Math.max(width, 2)} height={height} rx={4} className="range-fill" />
      <line x1={midX} x2={midX} y1={y - 3} y2={y + height + 3} className="range-median" />
    </g>
  );
}

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export const formatMoney = (value) => (value == null ? "—" : usd.format(value));

/** 95000 -> "$95k" */
export const formatMoneyShort = (value) =>
  value == null ? "—" : `$${Math.round(value / 1000).toLocaleString("en-US")}k`;

export const formatPct = (share, digits = 0) => `${(share * 100).toFixed(digits)}%`;

/** Change in share, in percentage points: 0.031 -> "+3.1 pts" */
export function formatChange(change) {
  const pts = change * 100;
  if (Math.abs(pts) < 0.05) return "±0.0 pts";
  return `${pts > 0 ? "+" : "−"}${Math.abs(pts).toFixed(1)} pts`;
}

export function formatSalaryRange(min, max) {
  if (min == null && max == null) return null;
  if (min == null || max == null || min === max) return formatMoney(min ?? max);
  return `${formatMoneyShort(min)} – ${formatMoneyShort(max)}`;
}

export function formatDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

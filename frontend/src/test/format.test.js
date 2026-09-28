import { describe, expect, it } from "vitest";
import { toQuery } from "../api.js";
import { formatChange, formatMoneyShort, formatPct, formatSalaryRange } from "../format.js";

describe("toQuery", () => {
  it("drops empty values", () => {
    expect(toQuery({ role: "", city: null, days: 30, skill: undefined })).toBe("?days=30");
    expect(toQuery({})).toBe("");
  });

  it("encodes values", () => {
    expect(toQuery({ role: "Data Analyst", q: "100%" })).toBe("?role=Data+Analyst&q=100%25");
  });
});

describe("formatters", () => {
  it("formats percentages and changes", () => {
    expect(formatPct(0.4567)).toBe("46%");
    expect(formatPct(0.4567, 1)).toBe("45.7%");
    expect(formatChange(0.031)).toBe("+3.1 pts");
    expect(formatChange(-0.1473)).toBe("−14.7 pts");
    expect(formatChange(0.0001)).toBe("±0.0 pts");
  });

  it("formats salary ranges", () => {
    expect(formatMoneyShort(95_400)).toBe("$95k");
    expect(formatSalaryRange(80_000, 100_000)).toBe("$80k – $100k");
    expect(formatSalaryRange(null, 100_000)).toBe("$100,000");
    expect(formatSalaryRange(null, null)).toBeNull();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SkillGap from "../components/SkillGap.jsx";

const CATALOG = [
  { name: "SQL", category: "Languages" },
  { name: "Python", category: "Languages" },
  { name: "dbt", category: "Data Engineering" },
];

function gapResponse(mine) {
  const top = [
    { skill: "SQL", category: "Languages", share: 0.8 },
    { skill: "dbt", category: "Data Engineering", share: 0.4 },
  ].map((s) => ({ ...s, have: mine.includes(s.skill) }));
  return {
    role: null,
    total_postings: 10,
    coverage: top.filter((s) => s.have).length / top.length,
    top_skills: top,
    missing: top.filter((s) => !s.have),
    unrecognized: [],
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, options) => {
      const body = url.endsWith("/skills") ? CATALOG : gapResponse(JSON.parse(options.body).skills);
      return { ok: true, json: async () => body };
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

describe("SkillGap", () => {
  it("shows missing skills and updates when a skill is selected", async () => {
    render(<SkillGap scope={{ role: "", state: "", city: "", work_mode: "" }} />);

    expect(await screen.findByText("0%")).toBeInTheDocument();
    const learnNext = screen.getByRole("list", { name: "Skills to learn next" });
    expect(learnNext).toHaveTextContent("SQL");
    expect(learnNext).toHaveTextContent("dbt");

    await userEvent.click(screen.getByRole("button", { name: "SQL" }));

    await waitFor(() => expect(screen.getByText("50%")).toBeInTheDocument());
    const updated = screen.getByRole("list", { name: "Skills to learn next" });
    expect(updated).not.toHaveTextContent("SQL");
    expect(JSON.parse(localStorage.getItem("market-tracker:my-skills"))).toEqual(["SQL"]);
    const lastCall = fetch.mock.calls.at(-1);
    expect(JSON.parse(lastCall[1].body)).toMatchObject({ skills: ["SQL"], top_n: 20, state: null });
  });
});

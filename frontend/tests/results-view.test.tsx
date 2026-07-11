import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { ResultsView } from "@/components/results/results-view";
import { resetMockApi } from "@/lib/api";
import { demoRun } from "@/tests/fixtures";
import type { ScreeningResults } from "@/types/api";

let results: ScreeningResults;

beforeEach(() => {
  resetMockApi();
  results = demoRun();
});

const ranked = () => [...demoRun().results].sort((a, b) => a.score.rank - b.score.rank);

test("ranks candidates the way the backend ranked them", async () => {
  const expected = ranked();
  render(<ResultsView projectId={results.project.id} api={{ getScreeningResults: async () => results }} />);

  const table = await screen.findByRole("table");
  expect(screen.getByText("Top score").nextElementSibling).toHaveTextContent(
    String(expected[0].score.overall_score),
  );
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent(expected[0].site.name);
});

test("sorts candidates by ascending score", async () => {
  const expected = ranked();
  const lowest = [...expected].sort((a, b) => a.score.overall_score - b.score.overall_score)[0];
  render(<ResultsView projectId={results.project.id} api={{ getScreeningResults: async () => results }} />);

  const table = await screen.findByRole("table");
  fireEvent.change(screen.getByRole("combobox", { name: "Sort candidates" }), { target: { value: "score_asc" } });
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent(lowest.site.name);
});

test("filters candidates by recommendation status", async () => {
  const rejected = ranked().filter((candidate) => candidate.score.recommendation_status === "reject");
  const kept = ranked().filter((candidate) => candidate.score.recommendation_status !== "reject");
  expect(rejected.length).toBeGreaterThan(0);

  render(<ResultsView projectId={results.project.id} api={{ getScreeningResults: async () => results }} />);
  const table = await screen.findByRole("table");
  fireEvent.change(screen.getByRole("combobox", { name: "Filter by status" }), { target: { value: "reject" } });

  for (const candidate of rejected) {
    expect(within(table).getByText(candidate.site.name)).toBeInTheDocument();
  }
  for (const candidate of kept) {
    expect(within(table).queryByText(candidate.site.name)).not.toBeInTheDocument();
  }
});

test("shows the next action the backend recommended, not one invented in the UI", async () => {
  const top = ranked()[0];
  render(<ResultsView projectId={results.project.id} api={{ getScreeningResults: async () => results }} />);

  const table = await screen.findByRole("table");
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent(top.recommended_next_action);
});

test("renders a stacked candidate list for mobile without relying on the wide table", async () => {
  render(<ResultsView projectId={results.project.id} api={{ getScreeningResults: async () => results }} />);
  const mobileList = await screen.findByTestId("mobile-candidate-list");
  expect(mobileList).toHaveClass("lg:hidden");
  expect(within(mobileList).getByText(ranked()[0].site.name)).toBeInTheDocument();
});

test("shows an error state, and stops loading, when the backend fails", async () => {
  render(
    <ResultsView
      projectId={results.project.id}
      api={{ getScreeningResults: async () => { throw new Error("Project has not been screened yet."); } }}
    />,
  );

  expect(await screen.findByRole("alert")).toHaveTextContent("Project has not been screened yet.");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

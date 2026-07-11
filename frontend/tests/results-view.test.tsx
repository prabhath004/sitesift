import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { ResultsView } from "@/components/results/results-view";
import { mockApi, resetMockApi } from "@/lib/api";
import { demoProject } from "@/lib/mock-data";
import type { ScreeningResults } from "@/types/api";

let results: ScreeningResults;

beforeEach(async () => {
  resetMockApi();
  results = await mockApi.seedDemoProject();
});

test("sorts candidates by ascending score", async () => {
  render(<ResultsView projectId={demoProject.id} api={{ getScreeningResults: async () => results }} />);
  const table = await screen.findByRole("table");
  expect(screen.getByText("Top score").nextElementSibling).toHaveTextContent("88");
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent("River Road");

  fireEvent.change(screen.getByRole("combobox", { name: "Sort candidates" }), { target: { value: "score_asc" } });
  expect(within(table).getAllByRole("row")[1]).toHaveTextContent("County Route 9");
});

test("filters candidates by recommendation status", async () => {
  render(<ResultsView projectId={demoProject.id} api={{ getScreeningResults: async () => results }} />);
  const table = await screen.findByRole("table");
  fireEvent.change(screen.getByRole("combobox", { name: "Filter by status" }), { target: { value: "high_risk" } });

  expect(within(table).getByText("Oak Parcel")).toBeInTheDocument();
  expect(within(table).getByText("Mill Farm")).toBeInTheDocument();
  expect(within(table).queryByText("River Road")).not.toBeInTheDocument();
});

test("renders a stacked candidate list for mobile without relying on the wide table", async () => {
  render(<ResultsView projectId={demoProject.id} api={{ getScreeningResults: async () => results }} />);
  const mobileList = await screen.findByTestId("mobile-candidate-list");
  expect(mobileList).toHaveClass("lg:hidden");
  expect(within(mobileList).getByText("River Road")).toBeInTheDocument();
});

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { Dashboard } from "@/components/dashboard/dashboard";
import { mockApi, resetMockApi } from "@/lib/api";
import { demoDashboard, demoProject } from "@/tests/fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

beforeEach(() => {
  resetMockApi();
  push.mockReset();
});

test("renders the dashboard rollups the backend computed", async () => {
  const items = demoDashboard();
  const item = items[0];
  render(<Dashboard api={{ getProjectDashboard: async () => items, seedDemoProject: () => mockApi.seedDemoProject() }} />);

  expect((await screen.findAllByText(item.project.name)).length).toBeGreaterThan(0);
  expect(screen.getByText("Candidate sites")).toBeInTheDocument();
  // The top score is whatever the backend said it was, not a number typed here.
  expect(
    screen.getAllByLabelText(`Overall score: ${item.top_score} out of 100`).length,
  ).toBeGreaterThan(0);
});

test("renders the empty project state", async () => {
  render(<Dashboard api={{ getProjectDashboard: async () => [], seedDemoProject: () => mockApi.seedDemoProject() }} />);
  expect(await screen.findByText("No screening projects yet.")).toBeInTheDocument();
});

test("renders a loading state while project data is pending", () => {
  render(<Dashboard api={{ getProjectDashboard: () => new Promise(() => undefined), seedDemoProject: () => mockApi.seedDemoProject() }} />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading screening projects");
});

test("the loading state terminates on failure, and the failure can be retried", async () => {
  const getProjectDashboard = vi
    .fn()
    .mockRejectedValueOnce(new Error("Backend unavailable"))
    .mockResolvedValueOnce([]);
  render(<Dashboard api={{ getProjectDashboard, seedDemoProject: () => mockApi.seedDemoProject() }} />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("No screening projects yet.")).toBeInTheDocument();
  expect(getProjectDashboard).toHaveBeenCalledTimes(2);
});

test("loads the seeded solar demo and opens its ranking", async () => {
  render(<Dashboard api={{ getProjectDashboard: async () => [], seedDemoProject: () => mockApi.seedDemoProject() }} />);
  await screen.findByText("No screening projects yet.");
  fireEvent.click(screen.getAllByRole("button", { name: "Load Sample Solar Project" })[0]);

  await vi.waitFor(() => expect(push).toHaveBeenCalledWith(`/projects/${demoProject().id}/results`));
});

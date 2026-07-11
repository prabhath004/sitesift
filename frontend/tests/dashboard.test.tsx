import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { Dashboard } from "@/components/dashboard/dashboard";
import { mockApi, resetMockApi } from "@/lib/api";
import { demoProject } from "@/lib/mock-data";
import type { ProjectDashboardItem } from "@/types/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const item: ProjectDashboardItem = {
  project: demoProject,
  candidate_count: 5,
  top_score: 88,
  high_risk_finding_count: 4,
  recommended_site_count: 1,
};

beforeEach(() => {
  resetMockApi();
  push.mockReset();
});

test("renders dashboard summary and project data", async () => {
  render(<Dashboard api={{ getProjectDashboard: async () => [item], seedDemoProject: () => mockApi.seedDemoProject() }} />);

  expect((await screen.findAllByText("Hudson Valley Community Solar")).length).toBeGreaterThan(0);
  expect(screen.getByText("Candidate sites")).toBeInTheDocument();
  expect(screen.getAllByLabelText("Overall score: 88 out of 100").length).toBeGreaterThan(0);
});

test("renders the empty project state", async () => {
  render(<Dashboard api={{ getProjectDashboard: async () => [], seedDemoProject: () => mockApi.seedDemoProject() }} />);
  expect(await screen.findByText("No screening projects yet.")).toBeInTheDocument();
});

test("renders a loading state while project data is pending", () => {
  render(<Dashboard api={{ getProjectDashboard: () => new Promise(() => undefined), seedDemoProject: () => mockApi.seedDemoProject() }} />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading screening projects");
});

test("renders and can retry an API failure state", async () => {
  const getProjectDashboard = vi.fn().mockRejectedValueOnce(new Error("Mock outage")).mockResolvedValueOnce([]);
  render(<Dashboard api={{ getProjectDashboard, seedDemoProject: () => mockApi.seedDemoProject() }} />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Mock outage");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByText("No screening projects yet.")).toBeInTheDocument();
  expect(getProjectDashboard).toHaveBeenCalledTimes(2);
});

test("loads the seeded solar demo and opens its ranking", async () => {
  render(<Dashboard api={{ getProjectDashboard: async () => [], seedDemoProject: () => mockApi.seedDemoProject() }} />);
  await screen.findByText("No screening projects yet.");
  fireEvent.click(screen.getAllByRole("button", { name: "Load Sample Solar Project" })[0]);

  await vi.waitFor(() => expect(push).toHaveBeenCalledWith(`/projects/${demoProject.id}/results`));
});

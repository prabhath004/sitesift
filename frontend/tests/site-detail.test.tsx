import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test } from "vitest";

import { SiteDetailView } from "@/components/sites/site-detail-view";
import { mockApi, resetMockApi } from "@/lib/api";
import { demoProject, demoSites } from "@/lib/mock-data";

beforeEach(() => resetMockApi());

test("displays the overall score, category breakdown, and complete deduction details", async () => {
  const detail = await mockApi.getSite(demoSites[0].id);
  render(<SiteDetailView siteId={detail.site.id} api={{ getSite: async () => detail }} />);

  expect(await screen.findByRole("heading", { name: "River Road" })).toBeInTheDocument();
  expect(screen.getByLabelText("Overall score: 88 out of 100")).toBeInTheDocument();
  expect(screen.getByText("24/25")).toBeInTheDocument();
  expect(screen.getAllByText("Pending document analysis").length).toBeGreaterThan(1);
  expect(screen.getAllByText("Actual value")).toHaveLength(4);
  expect(screen.getAllByText("Points awarded")).toHaveLength(4);
});

test("keeps the seeded score consistent across dashboard, ranking, and site detail data", async () => {
  await mockApi.seedDemoProject();
  const dashboard = await mockApi.getProjectDashboard();
  const ranking = await mockApi.getScreeningResults(demoProject.id);
  const detail = await mockApi.getSite(demoSites[0].id);
  const riverRoad = ranking.candidates.find((candidate) => candidate.site.id === demoSites[0].id);

  expect(dashboard[0].top_score).toBe(88);
  expect(riverRoad?.score.overall_score).toBe(88);
  expect(detail.score.overall_score).toBe(88);
  expect(detail.explanations.reduce((sum, explanation) => sum + explanation.points_awarded, 0)).toBe(88);
});

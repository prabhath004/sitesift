import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { SiteDetailView } from "@/components/sites/site-detail-view";
import { mockApi, resetMockApi } from "@/lib/api";
import { demoAnalysis, demoDashboard, demoRun, topSiteDetail } from "@/tests/fixtures";
import type { SiteDetail } from "@/types/api";

beforeEach(() => resetMockApi());

const stubApi = (detail: SiteDetail) => ({
  getSite: async () => detail,
  uploadDocument: mockApi.uploadDocument,
  analyzeDocument: mockApi.analyzeDocument,
  reviewFinding: mockApi.reviewFinding,
});

test("displays the overall score and every deduction the backend itemized", async () => {
  const detail = topSiteDetail();
  const score = detail.score!;
  render(<SiteDetailView siteId={detail.site.id} api={stubApi(detail)} />);

  expect(await screen.findByRole("heading", { name: detail.site.name })).toBeInTheDocument();
  expect(screen.getByLabelText(`Overall score: ${score.overall_score} out of 100`)).toBeInTheDocument();
  expect(screen.getAllByText(`${score.site_suitability_score}/25`).length).toBeGreaterThan(0);

  // Every rule the backend used is on the page, with its points.
  expect(screen.getAllByText("Points awarded")).toHaveLength(score.breakdown.length);
  for (const item of score.breakdown) {
    expect(screen.getByRole("heading", { name: item.rule })).toBeInTheDocument();
  }
});

test("the category scores add up to the overall score", () => {
  const score = topSiteDetail().score!;
  const sum =
    score.site_suitability_score +
    score.environmental_score +
    score.access_score +
    score.permitting_score;

  expect(sum).toBe(score.overall_score);
  expect(score.breakdown.reduce((total, item) => total + item.points_awarded, 0)).toBe(score.overall_score);
});

test("the same score appears in the dashboard, the ranking, and the site detail", () => {
  const run = demoRun();
  const top = [...run.results].sort((a, b) => a.score.rank - b.score.rank)[0];
  const dashboard = demoDashboard()[0];
  const detail = topSiteDetail();

  expect(dashboard.top_score).toBe(top.score.overall_score);
  expect(detail.score!.overall_score).toBe(top.score.overall_score);
  expect(detail.score!.recommendation_status).toBe(top.score.recommendation_status);
});

test("a fatal finding overrides the numeric score", () => {
  const rejected = demoRun().results.find((r) => r.score.recommendation_status === "reject");
  expect(rejected).toBeDefined();

  // The rejected site does not have the lowest score — it is rejected because a
  // fatal finding overrides the number, which is the behaviour spec §13 requires.
  const scores = demoRun().results.map((r) => r.score.overall_score);
  expect(rejected!.score.overall_score).toBeGreaterThan(Math.min(...scores) - 1);
  expect(rejected!.risks.some((finding) => finding.severity === "fatal")).toBe(true);
});

test("missing information is presented separately from confirmed risks", async () => {
  const detail = demoRun().results.map((r) => r.site.id).map((id) => id);
  expect(detail.length).toBe(5);

  const withGaps = topSiteDetail();
  render(<SiteDetailView siteId={withGaps.site.id} api={stubApi(withGaps)} />);
  await screen.findByRole("heading", { name: withGaps.site.name });

  const missing = screen.getByRole("heading", { name: "Missing information" }).closest("section")!;
  expect(within(missing).getByText(/An absent input is an unknown/)).toBeInTheDocument();
});

test("permitting requirements show page-level evidence and can be reviewed", async () => {
  const detail = topSiteDetail();
  const requirement = detail.permitting_requirements[0];
  expect(requirement).toBeDefined();
  expect(requirement.evidence.length).toBeGreaterThan(0);

  const reviewFinding = vi.fn().mockResolvedValue({ ...requirement, review_status: "approved" });
  render(
    <SiteDetailView
      siteId={detail.site.id}
      api={{ ...stubApi(detail), reviewFinding }}
    />,
  );

  await screen.findByRole("heading", { name: detail.site.name });

  // The claim is shown with the page and the verbatim excerpt it rests on.
  const evidence = requirement.evidence[0];
  expect(screen.getAllByText(new RegExp(`page ${evidence.page_number}`)).length).toBeGreaterThan(0);
  const excerpt = evidence.excerpt.slice(0, 30).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  expect(screen.getAllByText(new RegExp(excerpt)).length).toBeGreaterThan(0);

  fireEvent.click(screen.getAllByRole("button", { name: "Approve" })[0]);
  await vi.waitFor(() => expect(reviewFinding).toHaveBeenCalledWith(requirement.id, "approve", undefined));
});

test("document analysis produces findings that all carry evidence", () => {
  const analysis = demoAnalysis();
  expect(analysis.findings.length).toBeGreaterThan(0);

  for (const finding of analysis.findings) {
    expect(finding.evidence.length).toBeGreaterThan(0);
    expect(finding.source_type).toBe("document");
    expect(finding.review_status).toBe("pending");
    for (const evidence of finding.evidence) {
      expect(evidence.page_number).toBeGreaterThan(0);
      expect(evidence.excerpt.length).toBeGreaterThan(0);
    }
  }
});

test("permitting stays pending until a document is analyzed", () => {
  const unanalyzed = demoRun().results.find((r) => r.score.permitting_status === "not_analyzed");
  expect(unanalyzed).toBeDefined();
  expect(unanalyzed!.permitting_requirements).toHaveLength(0);
});

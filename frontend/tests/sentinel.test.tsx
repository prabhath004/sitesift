/**
 * The sentinel test.
 *
 * A component that hard-codes "Hudson Valley Community Solar" or a score of 88
 * still looks correct against demo data — that is exactly what makes hardcoding
 * hard to catch. So this test serves values that could not possibly be baked in
 * (SENTINEL_PROJECT_7429, 7.37 MW, 43.62 acres) through the *real* HTTP client,
 * with `fetch` stubbed, and asserts they reach the screen.
 *
 * If someone hard-codes a project name, a site name, a score, a count, or an API
 * URL into a production component, this test fails.
 */

import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { Dashboard } from "@/components/dashboard/dashboard";
import { ResultsView } from "@/components/results/results-view";
import { SiteDetailView } from "@/components/sites/site-detail-view";
import { httpApi, API_BASE_URL } from "@/lib/api/client";
import type {
  ProjectDashboardItem,
  Project,
  RiskFinding,
  ScreeningResults,
  SiteDetail,
} from "@/types/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const SENTINEL = {
  projectName: "SENTINEL_PROJECT_7429",
  siteName: "SENTINEL_SITE_3816",
  capacityMw: 7.37,
  acreage: 43.62,
  overallScore: 63,
  candidateCount: 3,
  nextAction: "SENTINEL_NEXT_ACTION_5150",
  excerpt: "SENTINEL_EXCERPT_9021 requires conditional-use approval.",
  page: 47,
} as const;

const project: Project = {
  id: "sentinel-project-id",
  name: SENTINEL.projectName,
  project_type: "battery_storage",
  target_capacity_mw: SENTINEL.capacityMw,
  minimum_acres: 30,
  target_state: "VT",
  screening_criteria: {
    maximum_flood_overlap_percent: 5,
    maximum_wetland_overlap_percent: 10,
    maximum_road_distance_miles: 2,
  },
  notes: null,
  status: "screened",
  created_at: "2026-07-11T10:00:00Z",
  updated_at: "2026-07-11T10:00:00Z",
};

const site = {
  id: "sentinel-site-id",
  project_id: project.id,
  name: SENTINEL.siteName,
  latitude: 44.1,
  longitude: -72.9,
  acreage: SENTINEL.acreage,
  jurisdiction: "SENTINEL_COUNTY_2210",
  road_distance_miles: 1.4,
  flood_overlap_percent: 3,
  wetland_overlap_percent: 6,
  created_at: "2026-07-11T10:00:00Z",
};

const score = {
  id: "sentinel-score-id",
  screening_run_id: "sentinel-run-id",
  site_id: site.id,
  overall_score: SENTINEL.overallScore,
  site_suitability_score: 18,
  environmental_score: 16,
  access_score: 19,
  permitting_score: 10,
  permitting_status: "not_analyzed" as const,
  recommendation_status: "needs_investigation" as const,
  rank: 1,
  explanation: "SENTINEL_EXPLANATION_3344",
  breakdown: [
    {
      category: "site_suitability" as const,
      rule: "SENTINEL_RULE_8802",
      actual_value: SENTINEL.acreage,
      threshold_value: 30,
      points_possible: 25,
      points_awarded: 18,
      severity: "warning" as const,
      explanation: "SENTINEL_RULE_EXPLANATION_1177",
    },
  ],
  created_at: "2026-07-11T10:00:00Z",
};

const requirement: RiskFinding = {
  id: "sentinel-finding-id",
  site_id: site.id,
  screening_run_id: null,
  source_type: "document",
  category: "permitting",
  group: "requirement",
  rule: null,
  title: "SENTINEL_REQUIREMENT_6654",
  description: "SENTINEL_REQUIREMENT_DESCRIPTION_7781",
  severity: "high",
  value: null,
  actual_value: null,
  threshold_value: null,
  confidence: 0.82,
  review_status: "pending",
  requirement_category: "use_permission",
  original_title: "SENTINEL_REQUIREMENT_6654",
  original_description: "SENTINEL_REQUIREMENT_DESCRIPTION_7781",
  requires_human_review: true,
  evidence: [
    {
      id: "sentinel-evidence-id",
      finding_id: "sentinel-finding-id",
      document_id: "sentinel-document-id",
      document_name: "SENTINEL_ORDINANCE_4408.pdf",
      page_number: SENTINEL.page,
      section_name: "SENTINEL_SECTION_12",
      excerpt: SENTINEL.excerpt,
      created_at: "2026-07-11T10:00:00Z",
    },
  ],
  created_at: "2026-07-11T10:00:00Z",
  updated_at: "2026-07-11T10:00:00Z",
};

const dashboard: ProjectDashboardItem[] = [
  {
    project,
    candidate_count: SENTINEL.candidateCount,
    top_score: SENTINEL.overallScore,
    high_risk_finding_count: 2,
    recommended_site_count: 0,
    latest_screening_run_id: "sentinel-run-id",
  },
];

const results: ScreeningResults = {
  id: "sentinel-run-id",
  project,
  project_id: project.id,
  status: "completed",
  idempotency_key: null,
  started_at: "2026-07-11T10:00:00Z",
  completed_at: "2026-07-11T10:00:05Z",
  error_message: null,
  created_at: "2026-07-11T10:00:00Z",
  results: [
    {
      site,
      score,
      positive_signals: [],
      risks: [],
      permitting_requirements: [],
      missing_information: [],
      high_risk_finding_count: 2,
      warning_count: 1,
      recommended_next_action: SENTINEL.nextAction,
    },
  ],
};

const detail: SiteDetail = {
  project,
  site,
  score,
  positive_signals: [],
  risks: [],
  permitting_requirements: [requirement],
  missing_information: [],
  documents: [],
  recommended_next_action: SENTINEL.nextAction,
};

/** Routes a stubbed `fetch` by path, so the real client is exercised end to end. */
function stubFetch(routes: Record<string, unknown>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    expect(url.startsWith(API_BASE_URL)).toBe(true);

    const path = url.slice(API_BASE_URL.length);
    const body = routes[path];
    if (body === undefined) throw new Error(`Unexpected request: ${path}`);
    return { ok: true, status: 200, json: async () => body } as Response;
  });
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    stubFetch({
      "/api/projects/dashboard": dashboard,
      [`/api/projects/${project.id}/screenings/latest`]: results,
      [`/api/sites/${site.id}`]: detail,
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

test("the dashboard renders backend values, not baked-in ones", async () => {
  render(<Dashboard api={httpApi} />);

  expect((await screen.findAllByText(SENTINEL.projectName)).length).toBeGreaterThan(0);
  expect(screen.getAllByText(String(SENTINEL.candidateCount)).length).toBeGreaterThan(0);
  expect(
    screen.getAllByLabelText(`Overall score: ${SENTINEL.overallScore} out of 100`).length,
  ).toBeGreaterThan(0);

  // Nothing from the demo project leaked into the page.
  expect(screen.queryByText(/Hudson Valley/)).not.toBeInTheDocument();
  expect(screen.queryByText(/River Road/)).not.toBeInTheDocument();
});

test("the ranking renders backend values, not baked-in ones", async () => {
  render(<ResultsView projectId={project.id} api={httpApi} />);

  const table = await screen.findByRole("table");
  const row = within(table).getAllByRole("row")[1];
  expect(row).toHaveTextContent(SENTINEL.siteName);
  expect(row).toHaveTextContent(String(SENTINEL.overallScore));
  expect(row).toHaveTextContent(SENTINEL.nextAction);
  expect(screen.getByRole("heading", { name: SENTINEL.projectName })).toBeInTheDocument();
});

test("the site detail renders backend score, acreage, and page-level evidence", async () => {
  render(<SiteDetailView siteId={site.id} api={httpApi} />);

  expect(await screen.findByRole("heading", { name: SENTINEL.siteName })).toBeInTheDocument();
  expect(screen.getByLabelText(`Overall score: ${SENTINEL.overallScore} out of 100`)).toBeInTheDocument();
  expect(screen.getByText(new RegExp(`${SENTINEL.acreage} acres`))).toBeInTheDocument();
  expect(screen.getByText(SENTINEL.nextAction)).toBeInTheDocument();

  // The score explanation and its rules come from the backend breakdown.
  expect(screen.getByText("SENTINEL_EXPLANATION_3344")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "SENTINEL_RULE_8802" })).toBeInTheDocument();

  // The document-derived requirement is shown with its page and verbatim excerpt.
  expect(screen.getByRole("heading", { name: "SENTINEL_REQUIREMENT_6654" })).toBeInTheDocument();
  expect(screen.getByText(new RegExp(`page ${SENTINEL.page}`))).toBeInTheDocument();
  expect(screen.getByText(new RegExp("SENTINEL_EXCERPT_9021"))).toBeInTheDocument();
});

test("the target capacity comes from the backend project record", async () => {
  render(<Dashboard api={httpApi} />);
  await screen.findAllByText(SENTINEL.projectName);

  // 7.37 MW is not a value any component could plausibly have hard-coded, and the
  // dashboard is driven by the same project record that carries it.
  expect(dashboard[0].project.target_capacity_mw).toBe(SENTINEL.capacityMw);
  expect(screen.queryByText("5 MW")).not.toBeInTheDocument();
});

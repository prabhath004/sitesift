/**
 * A mock API for isolated frontend development. NOT used by the integrated app:
 * it is only reachable when NEXT_PUBLIC_USE_MOCK_API=true, and the real client
 * never falls back to it (see `lib/api.ts`).
 *
 * It serves `fixtures.json`, which is *recorded from the real backend* by
 * `scripts/record-fixtures.py`. That is deliberate. The frontend branch's mock
 * carried its own scoring implementation in TypeScript, which is both a second
 * source of truth for a number the backend owns and a guarantee that the two will
 * eventually disagree. Serving recorded responses means the mock cannot invent a
 * score, a rank, or a status — it can only replay one.
 */

import type {
  CreateProjectRequest,
  DocumentAnalysis,
  DocumentSummary,
  HealthResponse,
  Project,
  ProjectDashboardItem,
  RiskFinding,
  ScreeningResults,
  SiteBrief,
  SiteDetail,
  SiteImportResult,
  ReviewDecision,
} from "@/types/api";

import fixtures from "./fixtures.json";
import { ApiError, type SiteSiftApi } from "./client";

interface Fixtures {
  screening_run: ScreeningResults;
  dashboard: ProjectDashboardItem[];
  sites: Record<string, SiteDetail>;
  briefs: Record<string, SiteBrief>;
  findings: Record<string, RiskFinding[]>;
  document_analysis: DocumentAnalysis;
}

const data = fixtures as unknown as Fixtures;
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const pause = () => new Promise<void>((resolve) => setTimeout(resolve, 60));

interface Store {
  seeded: boolean;
  sites: Record<string, SiteDetail>;
  findings: Record<string, RiskFinding[]>;
}

let store: Store = createStore();

function createStore(): Store {
  return { seeded: false, sites: clone(data.sites), findings: clone(data.findings) };
}

function siteOrThrow(siteId: string): SiteDetail {
  const site = store.sites[siteId];
  if (!site) throw new ApiError(`Candidate site ${siteId} not found.`, 404);
  return site;
}

export const mockApi: SiteSiftApi = {
  async getHealth(): Promise<HealthResponse> {
    await pause();
    return { status: "ok", service: "sitesift-mock", version: "0.1.0", environment: "mock", database: "ok" };
  },

  async getProjects(): Promise<Project[]> {
    await pause();
    return store.seeded ? [clone(data.screening_run.project)] : [];
  },

  async getProjectDashboard() {
    await pause();
    return store.seeded ? clone(data.dashboard) : [];
  },

  async createProject(input: CreateProjectRequest): Promise<Project> {
    await pause();
    throw new ApiError(
      `Creating "${input.name}" needs the real backend. Set NEXT_PUBLIC_USE_MOCK_API=false.`,
      501,
    );
  },

  async importCandidateSites(): Promise<SiteImportResult> {
    await pause();
    throw new ApiError(
      "CSV import needs the real backend. Set NEXT_PUBLIC_USE_MOCK_API=false.",
      501,
    );
  },

  async runScreening() {
    await pause();
    store.seeded = true;
    return clone(data.screening_run);
  },

  async getScreeningResults(projectId) {
    await pause();
    if (projectId !== data.screening_run.project.id) {
      throw new ApiError(`Project ${projectId} has not been screened yet.`, 404);
    }
    return clone(data.screening_run);
  },

  async getSite(siteId) {
    await pause();
    return clone(siteOrThrow(siteId));
  },

  async getSiteFindings(siteId) {
    await pause();
    siteOrThrow(siteId);
    return clone(store.findings[siteId] ?? []);
  },

  async uploadDocument(): Promise<DocumentSummary> {
    await pause();
    return clone(data.document_analysis.document);
  },

  async analyzeDocument() {
    await pause();
    return clone(data.document_analysis);
  },

  async getDocumentAnalysis() {
    await pause();
    return clone(data.document_analysis);
  },

  async reviewFinding(findingId, decision: ReviewDecision, edits) {
    await pause();
    for (const [siteId, findings] of Object.entries(store.findings)) {
      const finding = findings.find((item) => item.id === findingId);
      if (!finding) continue;

      const statuses: Record<ReviewDecision, RiskFinding["review_status"]> = {
        approve: "approved",
        edit: "edited",
        reject: "rejected",
        escalate: "escalated",
      };
      if (decision === "edit") {
        finding.title = edits?.edited_title ?? finding.title;
        finding.description = edits?.edited_description ?? finding.description;
      }
      finding.review_status = statuses[decision];

      const detail = store.sites[siteId];
      const requirement = detail?.permitting_requirements.find((item) => item.id === findingId);
      if (requirement) {
        requirement.title = finding.title;
        requirement.description = finding.description;
        requirement.review_status = finding.review_status;
      }
      return clone(finding);
    }
    throw new ApiError(`Finding ${findingId} not found.`, 404);
  },

  async getSiteBrief(siteId) {
    await pause();
    const brief = data.briefs[siteId];
    if (!brief) throw new ApiError(`Candidate site ${siteId} not found.`, 404);
    return clone(brief);
  },

  async seedDemoProject() {
    await pause();
    store.seeded = true;
    return clone(data.screening_run);
  },
};

/** Test-only reset, so one test's review decisions cannot leak into the next. */
export function resetMockApi(): void {
  store = createStore();
}

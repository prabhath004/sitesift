/**
 * The real SiteSift API client. Every method is one call to FastAPI, and every
 * response type comes from `generated.ts`, which is generated from the backend's
 * OpenAPI document.
 *
 * The client does not compute anything. Scores, ranks, recommendation statuses,
 * finding counts, and next actions are all read from the response — the backend
 * is the only place they are derived (CLAUDE.md, spec §9.1). If a value needs to
 * appear on a screen, it needs to come from here.
 */

import type {
  CreateProjectRequest,
  DocumentAnalysis,
  DocumentSummary,
  HealthResponse,
  Project,
  ProjectDashboardItem,
  ProjectId,
  ReviewDecision,
  RiskFinding,
  ScreeningResults,
  SiteBrief,
  SiteDetail,
  SiteImportResult,
} from "@/types/api";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** FastAPI's error shape: `{"detail": "..."}`, or a validation error list. */
interface ErrorBody {
  detail?: string | { msg?: string }[];
}

function errorMessage(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null) return fallback;
  const detail = (body as ErrorBody).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item.msg).filter((msg): msg is string => Boolean(msg));
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    // A network failure is a failure. It is never an invitation to serve mock
    // data: a fabricated score is worse than a visible error.
    throw new ApiError(`Could not reach the SiteSift API at ${API_BASE_URL}.`, 0);
  }

  if (response.status === 204) return undefined as T;

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      errorMessage(body, `Request to ${path} failed with status ${response.status}.`),
      response.status,
    );
  }
  return body as T;
}

function jsonRequest<T>(path: string, method: string, payload: unknown, headers?: HeadersInit) {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(payload),
  });
}

/** The operations the UI performs. Implemented for real here, faked in `mock.ts`. */
export interface SiteSiftApi {
  getHealth(): Promise<HealthResponse>;
  getProjects(): Promise<Project[]>;
  getProjectDashboard(): Promise<ProjectDashboardItem[]>;
  createProject(input: CreateProjectRequest): Promise<Project>;
  importCandidateSites(projectId: ProjectId, file: File): Promise<SiteImportResult>;
  runScreening(projectId: ProjectId, idempotencyKey?: string): Promise<ScreeningResults>;
  getScreeningResults(projectId: ProjectId): Promise<ScreeningResults>;
  getSite(siteId: string): Promise<SiteDetail>;
  getSiteFindings(siteId: string): Promise<RiskFinding[]>;
  uploadDocument(siteId: string, file: File): Promise<DocumentSummary>;
  analyzeDocument(documentId: string, idempotencyKey?: string): Promise<DocumentAnalysis>;
  getDocumentAnalysis(documentId: string): Promise<DocumentAnalysis>;
  reviewFinding(
    findingId: string,
    decision: ReviewDecision,
    edits?: { edited_title?: string; edited_description?: string; reviewer_note?: string },
  ): Promise<RiskFinding>;
  getSiteBrief(siteId: string): Promise<SiteBrief>;
  seedDemoProject(): Promise<ScreeningResults>;
}

export const httpApi: SiteSiftApi = {
  getHealth() {
    return request<HealthResponse>("/health");
  },

  getProjects() {
    return request<Project[]>("/api/projects");
  },

  getProjectDashboard() {
    return request<ProjectDashboardItem[]>("/api/projects/dashboard");
  },

  createProject(input) {
    return jsonRequest<Project>("/api/projects", "POST", input);
  },

  importCandidateSites(projectId, file) {
    const form = new FormData();
    form.append("file", file);
    return request<SiteImportResult>(`/api/projects/${projectId}/sites/import`, {
      method: "POST",
      body: form,
    });
  },

  runScreening(projectId, idempotencyKey) {
    // Spec §18: replaying the same key returns the existing run rather than
    // screening the project a second time.
    return request<ScreeningResults>(`/api/projects/${projectId}/screenings`, {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    });
  },

  getScreeningResults(projectId) {
    return request<ScreeningResults>(`/api/projects/${projectId}/screenings/latest`);
  },

  getSite(siteId) {
    return request<SiteDetail>(`/api/sites/${siteId}`);
  },

  getSiteFindings(siteId) {
    return request<RiskFinding[]>(`/api/sites/${siteId}/findings`);
  },

  uploadDocument(siteId, file) {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentSummary>(`/api/sites/${siteId}/documents`, {
      method: "POST",
      body: form,
    });
  },

  analyzeDocument(documentId, idempotencyKey) {
    return request<DocumentAnalysis>(`/api/documents/${documentId}/analyze`, {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    });
  },

  getDocumentAnalysis(documentId) {
    return request<DocumentAnalysis>(`/api/documents/${documentId}/analysis`);
  },

  reviewFinding(findingId, decision, edits) {
    return jsonRequest<RiskFinding>(`/api/findings/${findingId}/review`, "PATCH", {
      decision,
      edited_title: edits?.edited_title ?? null,
      edited_description: edits?.edited_description ?? null,
      reviewer_note: edits?.reviewer_note ?? null,
    });
  },

  getSiteBrief(siteId) {
    return request<SiteBrief>(`/api/sites/${siteId}/brief`);
  },

  async seedDemoProject() {
    // The seed is idempotent: it returns the existing demo on every call after
    // the first, and the response carries the completed run with its ranking.
    const seeded = await request<{ screening_run: ScreeningResults }>("/api/demo/seed", {
      method: "POST",
    });
    return seeded.screening_run;
  },
};

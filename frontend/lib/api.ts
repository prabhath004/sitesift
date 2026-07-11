/** Replaceable API boundary. Pages depend on SiteSiftApi, not mock internals. */

import { parseCandidateCsvFile } from "@/lib/csv";
import {
  DEMO_PROJECT_ID,
  demoFindings,
  demoProject,
  demoScores,
  demoScreeningRun,
  demoSiteDetails,
  demoSites,
  explanationsFor,
  nextActions,
} from "@/lib/mock-data";
import type {
  CandidateImportResponse,
  CandidateSite,
  CreateProjectRequest,
  HealthResponse,
  Project,
  ProjectDashboardItem,
  ProjectId,
  RankedCandidate,
  RecommendationStatus,
  RiskFinding,
  ScreeningResults,
  ScreeningRun,
  SiteDetail,
  SiteScore,
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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(`Could not reach the SiteSift API at ${API_BASE_URL}`, 0);
  }

  if (!response.ok) throw new ApiError(`Request to ${path} failed`, response.status);
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { cache: "no-store" });
}

export interface SiteSiftApi {
  getProjects(): Promise<Project[]>;
  getProjectDashboard(): Promise<ProjectDashboardItem[]>;
  createProject(input: CreateProjectRequest): Promise<Project>;
  importCandidateSites(projectId: ProjectId, file: File): Promise<CandidateImportResponse>;
  runScreening(projectId: ProjectId): Promise<ScreeningRun>;
  getScreeningResults(projectId: ProjectId): Promise<ScreeningResults>;
  getSite(siteId: string): Promise<SiteDetail>;
  seedDemoProject(): Promise<ScreeningResults>;
}

interface MockStore {
  projects: Map<string, Project>;
  sites: Map<string, CandidateSite>;
  runs: Map<string, ScreeningRun>;
  scores: Map<string, SiteScore>;
  findings: Map<string, RiskFinding>;
  details: Map<string, SiteDetail>;
  visibleProjectIds: Set<string>;
}

const createStore = (): MockStore => ({
  projects: new Map([[demoProject.id, demoProject]]),
  sites: new Map(demoSites.map((site) => [site.id, site])),
  runs: new Map([[demoScreeningRun.id, demoScreeningRun]]),
  scores: new Map(demoScores.map((score) => [score.id, score])),
  findings: new Map(demoFindings.map((finding) => [finding.id, finding])),
  details: new Map(demoSiteDetails.map((detail) => [detail.site.id, detail])),
  visibleProjectIds: new Set(),
});

let store = createStore();
let idCounter = 1;

const pause = () => new Promise<void>((resolve) => setTimeout(resolve, 90));
const now = () => new Date().toISOString();
const createId = () => `90000000-0000-4000-8000-${String(idCounter++).padStart(12, "0")}`;

function getProjectOrThrow(projectId: string): Project {
  const project = store.projects.get(projectId);
  if (!project) throw new ApiError("Project not found", 404);
  return project;
}

function rankForProject(projectId: string): RankedCandidate[] {
  const projectSites = [...store.sites.values()].filter((site) => site.project_id === projectId);
  return projectSites
    .map((site) => {
      const score = [...store.scores.values()].find((candidate) => candidate.site_id === site.id);
      if (!score) return null;
      const findings = [...store.findings.values()].filter((finding) => finding.site_id === site.id);
      return {
        site,
        score,
        rank: 0,
        high_risk_finding_count: findings.filter(
          (finding) => finding.severity === "high" || finding.severity === "fatal",
        ).length,
        warning_count: findings.filter((finding) => finding.severity === "warning").length,
        recommended_next_action:
          projectId === DEMO_PROJECT_ID
            ? nextActions[demoSites.findIndex((candidate) => candidate.id === site.id)]
            : nextActionFor(score.recommendation_status),
      } satisfies RankedCandidate;
    })
    .filter((candidate): candidate is RankedCandidate => candidate !== null)
    .sort((left, right) => right.score.overall_score - left.score.overall_score)
    .map((candidate, index) => ({ ...candidate, rank: index + 1 }));
}

function nextActionFor(status: RecommendationStatus): string {
  const actions: Record<RecommendationStatus, string> = {
    recommended: "Advance diligence",
    recommended_with_review: "Review flagged items",
    needs_investigation: "Resolve data gaps",
    high_risk: "Investigate key risks",
    reject: "Do not advance",
  };
  return actions[status];
}

function latestRun(projectId: string): ScreeningRun | undefined {
  return [...store.runs.values()]
    .filter((run) => run.project_id === projectId)
    .sort((left, right) => (right.started_at ?? "").localeCompare(left.started_at ?? ""))[0];
}

function statusFor(score: number, fatal: boolean): RecommendationStatus {
  if (fatal) return "reject";
  if (score >= 80) return "recommended";
  if (score >= 70) return "recommended_with_review";
  if (score >= 55) return "needs_investigation";
  return "high_risk";
}

function scoreSite(site: CandidateSite, project: Project, run: ScreeningRun): SiteScore {
  const acreageRatio = site.acreage / project.minimum_acres;
  const suitability = acreageRatio >= 1 ? 25 : acreageRatio >= 0.9 ? 15 : acreageRatio >= 0.75 ? 8 : 0;
  const flood = site.flood_overlap_percent;
  const wetland = site.wetland_overlap_percent;
  const floodPoints = flood === null ? 6 : flood <= project.screening_criteria.maximum_flood_overlap_percent ? 12 : flood <= project.screening_criteria.maximum_flood_overlap_percent * 1.5 ? 6 : 0;
  const wetlandPoints = wetland === null ? 7 : wetland <= project.screening_criteria.maximum_wetland_overlap_percent ? 13 : wetland <= project.screening_criteria.maximum_wetland_overlap_percent * 1.5 ? 7 : 0;
  const environmental = floodPoints + wetlandPoints;
  const road = site.road_distance_miles;
  const access = road === null ? 5 : road <= project.screening_criteria.maximum_road_distance_miles ? 25 : road <= project.screening_criteria.maximum_road_distance_miles * 1.5 ? 15 : 5;
  const permitting = 10;
  const overall = suitability + environmental + access + permitting;
  const fatal = acreageRatio < 0.75;

  return {
    id: createId(),
    screening_run_id: run.id,
    site_id: site.id,
    overall_score: overall,
    site_suitability_score: suitability,
    environmental_score: environmental,
    access_score: access,
    permitting_score: permitting,
    recommendation_status: statusFor(overall, fatal),
    explanation: "Deterministic category scores with permitting pending document analysis.",
    created_at: now(),
  };
}

function findingsFor(site: CandidateSite, project: Project, run: ScreeningRun): RiskFinding[] {
  const definitions: Array<[string, string, string, "warning" | "high" | "fatal"]> = [];
  if (site.acreage < project.minimum_acres) {
    definitions.push([
      "Site suitability",
      "Acreage is below the minimum",
      `${site.acreage} acres is below the ${project.minimum_acres}-acre requirement.`,
      site.acreage / project.minimum_acres < 0.75 ? "fatal" : "high",
    ]);
  }
  if (site.flood_overlap_percent === null) {
    definitions.push(["Environmental", "Flood overlap is missing", "Provide mapped flood overlap data.", "warning"]);
  } else if (site.flood_overlap_percent > project.screening_criteria.maximum_flood_overlap_percent) {
    definitions.push(["Environmental", "Flood overlap exceeds threshold", `${site.flood_overlap_percent}% exceeds the configured maximum.`, "high"]);
  }
  if (site.wetland_overlap_percent === null) {
    definitions.push(["Environmental", "Wetland overlap is missing", "Provide mapped wetland overlap data.", "warning"]);
  } else if (site.wetland_overlap_percent > project.screening_criteria.maximum_wetland_overlap_percent) {
    definitions.push(["Environmental", "Wetland overlap exceeds threshold", `${site.wetland_overlap_percent}% exceeds the configured maximum.`, "high"]);
  }
  if (site.road_distance_miles === null) {
    definitions.push(["Access", "Road distance is missing", "Provide a mapped road-distance value.", "warning"]);
  } else if (site.road_distance_miles > project.screening_criteria.maximum_road_distance_miles) {
    definitions.push(["Access", "Road distance exceeds threshold", `${site.road_distance_miles} miles exceeds the configured maximum.`, "high"]);
  }

  return definitions.map(([category, title, description, severity]) => ({
    id: createId(),
    site_id: site.id,
    screening_run_id: run.id,
    source_type: "deterministic",
    category,
    title,
    description,
    severity,
    value: null,
    confidence: null,
    review_status: "pending",
    evidence: [],
    created_at: now(),
    updated_at: now(),
  }));
}

function screeningResults(projectId: string): ScreeningResults {
  const project = getProjectOrThrow(projectId);
  const screeningRun = latestRun(projectId);
  if (!screeningRun) throw new ApiError("No screening run found", 404);
  return { project, screening_run: screeningRun, candidates: rankForProject(projectId) };
}

export const mockApi: SiteSiftApi = {
  async getProjects() {
    await pause();
    return [...store.projects.values()].filter((project) => store.visibleProjectIds.has(project.id));
  },

  async getProjectDashboard() {
    await pause();
    return [...store.projects.values()]
      .filter((project) => store.visibleProjectIds.has(project.id))
      .map((project) => {
        const candidates = rankForProject(project.id);
        return {
          project,
          candidate_count: candidates.length,
          top_score: candidates[0]?.score.overall_score ?? null,
          high_risk_finding_count: candidates.reduce(
            (count, candidate) => count + candidate.high_risk_finding_count,
            0,
          ),
          recommended_site_count: candidates.filter(
            (candidate) => candidate.score.recommendation_status === "recommended",
          ).length,
        };
      });
  },

  async createProject(input) {
    await pause();
    const project: Project = {
      id: createId(),
      ...input,
      status: "draft",
      created_at: now(),
      updated_at: now(),
    };
    store.projects.set(project.id, project);
    store.visibleProjectIds.add(project.id);
    return project;
  },

  async importCandidateSites(projectId, file) {
    await pause();
    getProjectOrThrow(projectId);
    const parsed = await parseCandidateCsvFile(file);
    const imported = parsed.rows.flatMap((row) => (row.candidate ? [row.candidate] : []));
    const sites = imported.map((row): CandidateSite => ({
      id: createId(),
      project_id: projectId,
      name: row.site_name,
      latitude: row.latitude,
      longitude: row.longitude,
      acreage: row.acreage,
      jurisdiction: row.jurisdiction,
      road_distance_miles: row.road_distance_miles,
      flood_overlap_percent: row.flood_overlap_percent,
      wetland_overlap_percent: row.wetland_overlap_percent,
      created_at: now(),
    }));
    sites.forEach((site) => store.sites.set(site.id, site));
    return { sites, imported_count: sites.length, rejected_count: parsed.invalid_count };
  },

  async runScreening(projectId) {
    await pause();
    const project = getProjectOrThrow(projectId);
    const run: ScreeningRun = {
      id: createId(),
      project_id: projectId,
      status: "completed",
      idempotency_key: createId(),
      started_at: now(),
      completed_at: now(),
      error_message: null,
    };
    store.runs.set(run.id, run);
    const sites = [...store.sites.values()].filter((site) => site.project_id === projectId);
    sites.forEach((site) => {
      const score = scoreSite(site, project, run);
      store.scores.set(score.id, score);
      const findings = findingsFor(site, project, run);
      findings.forEach((finding) => store.findings.set(finding.id, finding));
      const positives = [
        site.acreage >= project.minimum_acres ? `${site.acreage} acres meets the configured minimum` : null,
        site.flood_overlap_percent !== null && site.flood_overlap_percent <= project.screening_criteria.maximum_flood_overlap_percent ? "Flood overlap is within the configured threshold" : null,
        site.wetland_overlap_percent !== null && site.wetland_overlap_percent <= project.screening_criteria.maximum_wetland_overlap_percent ? "Wetland overlap is within the configured threshold" : null,
        site.road_distance_miles !== null && site.road_distance_miles <= project.screening_criteria.maximum_road_distance_miles ? "Road distance is within the configured threshold" : null,
      ].filter((value): value is string => value !== null);
      store.details.set(site.id, {
        project,
        site,
        score,
        rank: 0,
        positive_signals: positives,
        risks: findings,
        missing_information: ["Permitting pathway", "Site-control status", "Utility interconnection availability"],
        explanations: explanationsFor(site, score, project),
      });
    });
    store.projects.set(projectId, { ...project, status: "completed", updated_at: now() });
    return run;
  },

  async getScreeningResults(projectId) {
    await pause();
    return screeningResults(projectId);
  },

  async getSite(siteId) {
    await pause();
    const detail = store.details.get(siteId);
    if (!detail) throw new ApiError("Site not found", 404);
    const rank = rankForProject(detail.project.id).find((candidate) => candidate.site.id === siteId)?.rank ?? detail.rank;
    return { ...detail, rank };
  },

  async seedDemoProject() {
    await pause();
    store.visibleProjectIds.add(DEMO_PROJECT_ID);
    return screeningResults(DEMO_PROJECT_ID);
  },
};

export const siteSiftApi: SiteSiftApi = mockApi;

/** Test-only reset for deterministic state between browser-level flows. */
export function resetMockApi(): void {
  store = createStore();
  idCounter = 1;
}

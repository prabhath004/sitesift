/**
 * Shared wire types from docs/API_CONTRACT.md plus explicitly-labelled adapter
 * view models. JSON field names remain snake_case at the API boundary.
 */

export type ProjectId = string;
export type CandidateSiteId = string;
export type ScreeningRunId = string;
export type SiteScoreId = string;
export type RiskFindingId = string;
export type DocumentId = string;
export type EvidenceId = string;
export type ReviewId = string;

export type ProjectType =
  | "solar"
  | "community_solar"
  | "battery_storage"
  | "data_center"
  | "ev_charging"
  | "other";

export type ScreeningRunStatus =
  | "queued"
  | "screening"
  | "document_analysis"
  | "needs_review"
  | "completed"
  | "partially_completed"
  | "failed";

export type RecommendationStatus =
  | "recommended"
  | "recommended_with_review"
  | "needs_investigation"
  | "high_risk"
  | "reject";

export type FindingSourceType = "deterministic" | "document" | "human";
export type FindingSeverity = "info" | "warning" | "high" | "fatal";
export type ReviewStatus = "pending" | "approved" | "edited" | "rejected" | "escalated";
export type ReviewDecision = "approve" | "edit" | "reject" | "escalate";
export type DocumentProcessingStatus = "uploaded" | "processing" | "completed" | "failed";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  database: "ok" | "unavailable";
}

export interface ScreeningCriteria {
  maximum_flood_overlap_percent: number;
  maximum_wetland_overlap_percent: number;
  maximum_road_distance_miles: number;
}

export interface Project {
  id: ProjectId;
  name: string;
  project_type: ProjectType;
  target_capacity_mw: number;
  minimum_acres: number;
  target_state: string;
  screening_criteria: ScreeningCriteria;
  notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  project_type: ProjectType;
  target_capacity_mw: number;
  minimum_acres: number;
  target_state: string;
  screening_criteria: ScreeningCriteria;
  notes: string | null;
}

export interface CandidateSite {
  id: CandidateSiteId;
  project_id: ProjectId;
  name: string;
  latitude: number;
  longitude: number;
  acreage: number;
  jurisdiction: string;
  road_distance_miles: number | null;
  flood_overlap_percent: number | null;
  wetland_overlap_percent: number | null;
  created_at: string;
}

export interface CandidateSiteInput {
  site_name: string;
  latitude: number;
  longitude: number;
  acreage: number;
  jurisdiction: string;
  road_distance_miles: number | null;
  flood_overlap_percent: number | null;
  wetland_overlap_percent: number | null;
}

export interface CandidateImportResponse {
  sites: CandidateSite[];
  imported_count: number;
  rejected_count: number;
}

export interface ScreeningRun {
  id: ScreeningRunId;
  project_id: ProjectId;
  status: ScreeningRunStatus;
  idempotency_key: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface SiteScore {
  id: SiteScoreId;
  screening_run_id: ScreeningRunId;
  site_id: CandidateSiteId;
  overall_score: number;
  site_suitability_score: number;
  environmental_score: number;
  access_score: number;
  permitting_score: number;
  recommendation_status: RecommendationStatus;
  explanation: string;
  created_at: string;
}

export interface Evidence {
  id: EvidenceId;
  finding_id: RiskFindingId;
  document_id: DocumentId;
  document_name: string;
  page_number: number | null;
  section_name: string | null;
  excerpt: string;
  created_at: string;
}

export interface RiskFinding {
  id: RiskFindingId;
  site_id: CandidateSiteId;
  screening_run_id: ScreeningRunId | null;
  source_type: FindingSourceType;
  category: string;
  title: string;
  description: string;
  severity: FindingSeverity;
  value: string | null;
  confidence: number | null;
  review_status: ReviewStatus;
  evidence: Evidence[];
  created_at: string;
  updated_at: string;
}

/** Adapter-composed models. These are not additions to the backend contract. */
export interface ProjectDashboardItem {
  project: Project;
  candidate_count: number;
  top_score: number | null;
  high_risk_finding_count: number;
  recommended_site_count: number;
}

export interface ScoreExplanationItem {
  id: string;
  category: "Site suitability" | "Environmental" | "Access and proximity" | "Permitting readiness";
  rule: string;
  actual_value: string;
  threshold: string;
  points_possible: number;
  points_awarded: number;
  severity: FindingSeverity;
  explanation: string;
}

export interface RankedCandidate {
  site: CandidateSite;
  score: SiteScore;
  rank: number;
  high_risk_finding_count: number;
  warning_count: number;
  recommended_next_action: string;
}

export interface ScreeningResults {
  project: Project;
  screening_run: ScreeningRun;
  candidates: RankedCandidate[];
}

export interface SiteDetail {
  project: Project;
  site: CandidateSite;
  score: SiteScore;
  rank: number;
  positive_signals: string[];
  risks: RiskFinding[];
  missing_information: string[];
  explanations: ScoreExplanationItem[];
}

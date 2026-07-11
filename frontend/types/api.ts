/**
 * The API types the UI uses. Every one is an alias for a schema in
 * `lib/api/generated.ts`, which `npm run api:generate` generates from the
 * backend's OpenAPI document.
 *
 * Nothing here is hand-written any more. This file used to be a hand-maintained
 * mirror of `backend/app/schemas/common.py`, which meant the contract could drift
 * silently in either direction. Now a backend field change becomes a TypeScript
 * error the next time the types are regenerated. The aliases exist only to give
 * the generated schemas the names the components already use.
 */

import type { components } from "@/lib/api/generated";

type Schemas = components["schemas"];

export type ProjectId = string;
export type CandidateSiteId = string;
export type ScreeningRunId = string;
export type SiteScoreId = string;
export type RiskFindingId = string;
export type DocumentId = string;
export type EvidenceId = string;

// Status enums — defined once, in the backend.
export type ProjectType = Schemas["ProjectType"];
export type ProjectStatus = Schemas["ProjectStatus"];
export type ScreeningRunStatus = Schemas["ScreeningRunStatus"];
export type RecommendationStatus = Schemas["RecommendationStatus"];
export type FindingSourceType = Schemas["FindingSourceType"];
export type FindingSeverity = Schemas["FindingSeverity"];
export type FindingCategory = Schemas["FindingCategory"];
export type FindingGroup = Schemas["FindingGroup"];
export type RequirementCategory = Schemas["RequirementCategory"];
export type ReviewStatus = Schemas["ReviewStatus"];
export type ReviewDecision = Schemas["ReviewDecision"];
export type DocumentProcessingStatus = Schemas["DocumentProcessingStatus"];
export type PermittingAnalysisStatus = Schemas["PermittingAnalysisStatus"];

// Entities.
export type HealthResponse = Schemas["HealthResponse"];
export type ScreeningCriteria = Schemas["ScreeningCriteria"];
export type Project = Schemas["ProjectRead"];
export type CreateProjectRequest = Schemas["ProjectCreate"];
export type CandidateSite = Schemas["CandidateSiteRead"];
export type SiteScore = Schemas["SiteScoreRead"];
export type ScoreBreakdownItem = Schemas["ScoreBreakdownItem"];
export type RiskFinding = Schemas["RiskFindingRead"];
export type Evidence = Schemas["EvidenceResponse"];
export type WorkflowEvent = Schemas["WorkflowEventRead"];

// Composite responses. These are backend response schemas, not UI view models:
// the ranking, the counts, and the next action are computed server-side.
export type ProjectDashboardItem = Schemas["ProjectDashboardItem"];
export type RankedCandidate = Schemas["SiteScreeningResult"];
export type ScreeningRun = Schemas["ScreeningRunDetail"];
export type ScreeningResults = Schemas["ScreeningRunDetail"];
export type SiteDetail = Schemas["SiteDetail"];
export type SiteBrief = Schemas["SiteBriefRead"];
export type BriefRankingEntry = Schemas["BriefRankingEntry"];

// CSV import.
export type SiteImportResult = Schemas["SiteImportResult"];
export type ImportSummary = Schemas["ImportSummary"];
export type RowValidationError = Schemas["RowValidationError"];

// Documents, evidence, review.
export type DocumentSummary = Schemas["DocumentResponse"];
export type DocumentAnalysis = Schemas["DocumentAnalysisResponse"];
export type DocumentWorkflowEvent = Schemas["DocumentWorkflowEventResponse"];
export type ReviewFindingRequest = Schemas["ReviewFindingRequest"];

/**
 * One CSV row as the browser parses it for preview, before the file is uploaded.
 * The backend re-validates every row and is the authority on what is accepted;
 * this type exists so the preview can show the user what they are about to send.
 */
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

/**
 * Shared API types — contract v1 (draft).
 *
 * SHARED FILE. Every union below mirrors an enum in
 * `backend/app/schemas/common.py` exactly, member for member. Change one, change
 * both, and update `docs/API_CONTRACT.md` in the same commit.
 *
 * Entity shapes (Project, CandidateSite, SiteScore, ...) are not defined here
 * yet — the owning agent adds them as the endpoints land.
 */

// Identifiers are UUID strings on the wire.
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

/** Response of `GET /health`. */
export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  database: "ok" | "unavailable";
}

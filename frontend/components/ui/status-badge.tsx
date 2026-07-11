import type { RecommendationStatus, ScreeningRunStatus } from "@/types/api";

const labels: Record<RecommendationStatus | ScreeningRunStatus, string> = {
  recommended: "Recommended",
  recommended_with_review: "Recommended with review",
  needs_investigation: "Needs investigation",
  high_risk: "High risk",
  reject: "Reject",
  queued: "Queued",
  screening: "Screening",
  document_analysis: "Document analysis",
  needs_review: "Needs review",
  completed: "Completed",
  partially_completed: "Partially completed",
  failed: "Failed",
};

const styles: Record<RecommendationStatus | ScreeningRunStatus, string> = {
  recommended: "border-emerald-200 bg-emerald-50 text-emerald-800",
  recommended_with_review: "border-teal-200 bg-teal-50 text-teal-800",
  needs_investigation: "border-amber-200 bg-amber-50 text-amber-900",
  high_risk: "border-orange-200 bg-orange-50 text-orange-900",
  reject: "border-red-200 bg-red-50 text-red-800",
  queued: "border-slate-200 bg-slate-50 text-slate-700",
  screening: "border-blue-200 bg-blue-50 text-blue-800",
  document_analysis: "border-violet-200 bg-violet-50 text-violet-800",
  needs_review: "border-amber-200 bg-amber-50 text-amber-900",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  partially_completed: "border-amber-200 bg-amber-50 text-amber-900",
  failed: "border-red-200 bg-red-50 text-red-800",
};

export function StatusBadge({ status }: { status: RecommendationStatus | ScreeningRunStatus }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold ${styles[status]}`}>
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {labels[status]}
    </span>
  );
}

export function formatProjectType(type: string): string {
  return type
    .split("_")
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

"use client";

import { useState } from "react";

import { EmptyState } from "@/components/states";
import { RequirementCard } from "@/components/ui/requirement-card";
import type { SiteSiftApi } from "@/lib/api";
import type { DocumentAnalysis, ReviewDecision, SiteDetail } from "@/types/api";

type PermittingApi = Pick<SiteSiftApi, "uploadDocument" | "analyzeDocument" | "reviewFinding">;

/**
 * Permitting: upload an ordinance, run the analysis, and review what it extracted.
 *
 * The workflow trail shows the step, its status, and its duration — never model
 * reasoning (CLAUDE.md rule 6). Every extracted requirement is shown with the page
 * and the verbatim excerpt it rests on, and none of them is final until a reviewer
 * decides on it.
 */
export function PermittingPanel({
  detail,
  api,
  onReviewed,
}: {
  detail: SiteDetail;
  api: PermittingApi;
  onReviewed: () => void;
}) {
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null);
  const [busy, setBusy] = useState<null | "uploading" | "analyzing">(null);
  const [error, setError] = useState<string | null>(null);

  const requirements = analysis?.findings ?? detail.permitting_requirements;
  const documents = detail.documents;

  const upload = async (file: File) => {
    setBusy("uploading");
    setError(null);
    try {
      const uploaded = await api.uploadDocument(detail.site.id, file);
      setBusy("analyzing");
      setAnalysis(await api.analyzeDocument(uploaded.id, `analyze:${uploaded.id}`));
      onReviewed();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The document could not be analyzed.");
    } finally {
      setBusy(null);
    }
  };

  const review = async (findingId: string, decision: ReviewDecision, note?: string) => {
    setError(null);
    try {
      await api.reviewFinding(findingId, decision, note ? { reviewer_note: note } : undefined);
      setAnalysis(null);
      onReviewed();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The review could not be saved.");
    }
  };

  const pendingCount = requirements.filter((item) => item.review_status === "pending").length;

  return (
    <section aria-labelledby="permitting-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-forest">Permitting readiness</p>
          <h2 id="permitting-heading" className="mt-1 text-xl font-bold text-ink">
            {requirements.length === 0 ? "No ordinance analyzed yet" : `${requirements.length} extracted requirement${requirements.length === 1 ? "" : "s"}`}
          </h2>
        </div>
        {requirements.length > 0 ? (
          <span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">{pendingCount} pending review</span>
        ) : null}
      </div>

      <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
        <label className="block">
          <span className="text-sm font-semibold text-slate-700">Upload a zoning or permitting PDF</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={busy !== null}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
              event.target.value = "";
            }}
            className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-forest file:px-4 file:py-2 file:text-sm file:font-bold file:text-white hover:file:bg-[#123e39] disabled:cursor-wait"
          />
        </label>
        {busy ? <p role="status" className="mt-3 text-sm font-semibold text-slate-600">{busy === "uploading" ? "Uploading the document…" : "Analyzing the ordinance…"}</p> : null}
        {documents.length > 0 ? (
          <ul className="mt-3 space-y-1">
            {documents.map((document) => (
              <li key={document.id} className="font-mono text-xs text-slate-500">
                {document.filename} · {document.page_count} pages · {document.processing_status.replaceAll("_", " ")}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {error ? <p role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800">{error}</p> : null}

      <div className="mt-5">
        {requirements.length === 0 ? (
          <EmptyState
            title="Permitting is pending"
            description="No zoning or permitting document has been analyzed for this site, so the permitting category is provisional. It is not a permitting determination."
          />
        ) : (
          <ul className="space-y-3">
            {requirements.map((finding) => (
              <li key={finding.id}>
                <RequirementCard finding={finding} onReview={review} />
              </li>
            ))}
          </ul>
        )}
      </div>

      {analysis && analysis.workflow_events.length > 0 ? (
        <details className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <summary className="cursor-pointer text-sm font-bold text-slate-700">Workflow steps ({analysis.workflow_events.length})</summary>
          <ul className="mt-3 space-y-1">
            {analysis.workflow_events.map((event) => (
              <li key={event.id} className="flex items-center justify-between gap-3 font-mono text-xs text-slate-600">
                <span>{event.node_name}</span>
                <span className={event.status === "failed" ? "font-bold text-red-700" : "text-slate-500"}>{event.status} · {event.duration_ms}ms</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

"use client";

import { useState } from "react";

import type { ReviewDecision, ReviewStatus, RiskFinding } from "@/types/api";

const REVIEW_STYLES: Record<ReviewStatus, string> = {
  pending: "bg-amber-50 text-amber-900 border-amber-200",
  approved: "bg-emerald-50 text-emerald-900 border-emerald-200",
  edited: "bg-blue-50 text-blue-900 border-blue-200",
  rejected: "bg-red-50 text-red-900 border-red-200",
  escalated: "bg-purple-50 text-purple-900 border-purple-200",
};

const DECISIONS: { decision: ReviewDecision; label: string }[] = [
  { decision: "approve", label: "Approve" },
  { decision: "edit", label: "Edit" },
  { decision: "reject", label: "Reject" },
  { decision: "escalate", label: "Escalate" },
];

/**
 * One document-derived permitting requirement, with the evidence it rests on and
 * the reviewer's controls.
 *
 * The evidence is not optional decoration. A document-derived claim without a
 * page and a verbatim excerpt is invalid, so if evidence is somehow absent the
 * card says so rather than presenting the claim as if it were supported.
 */
export function RequirementCard({
  finding,
  onReview,
}: {
  finding: RiskFinding;
  onReview: (findingId: string, decision: ReviewDecision, note?: string) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const edited = finding.original_title !== null && finding.original_title !== finding.title;

  const decide = async (decision: ReviewDecision) => {
    setBusy(true);
    await onReview(finding.id, decision);
    setBusy(false);
  };

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">
          {(finding.requirement_category ?? finding.category).replaceAll("_", " ")}
        </span>
        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase ${REVIEW_STYLES[finding.review_status]}`}>
          {finding.review_status}
        </span>
        {finding.confidence !== null ? (
          <span className="font-mono text-[10px] text-slate-400">confidence {Math.round(finding.confidence * 100)}%</span>
        ) : null}
      </div>

      <h3 className="mt-2 text-sm font-bold text-ink">{finding.title}</h3>
      <p className="mt-1 text-sm leading-6 text-slate-600">{finding.description}</p>
      {finding.value ? <p className="mt-2 font-mono text-xs text-slate-500">{finding.value}</p> : null}

      {edited ? (
        <p className="mt-2 rounded bg-blue-50 p-2 text-xs text-blue-900">
          Edited by a reviewer. Originally extracted as: “{finding.original_title}”
        </p>
      ) : null}

      {finding.evidence.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {finding.evidence.map((evidence) => (
            <li key={evidence.id} className="rounded-md border-l-2 border-l-forest bg-slate-50 p-3">
              <p className="text-xs font-bold text-slate-600">
                {evidence.document_name} · page {evidence.page_number}
                {evidence.section_name ? ` · ${evidence.section_name}` : ""}
              </p>
              <blockquote className="mt-1 text-xs italic leading-5 text-slate-600">“{evidence.excerpt}”</blockquote>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs font-semibold text-red-800">
          No evidence is attached to this requirement, so it cannot be verified or approved.
        </p>
      )}

      {finding.requires_human_review ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {DECISIONS.map(({ decision, label }) => (
            <button
              key={decision}
              type="button"
              disabled={busy}
              onClick={() => void decide(decision)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
            >
              {label}
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}

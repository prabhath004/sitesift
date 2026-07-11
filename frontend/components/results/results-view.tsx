"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PageLayout } from "@/components/layout/page-layout";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { ScoreDisplay } from "@/components/ui/score-display";
import { StatusBadge } from "@/components/ui/status-badge";
import { SummaryCard } from "@/components/ui/summary-card";
import { siteSiftApi, type SiteSiftApi } from "@/lib/api";
import type { RankedCandidate, RecommendationStatus, ScreeningResults } from "@/types/api";

type ResultsApi = Pick<SiteSiftApi, "getScreeningResults">;
type SortKey = "rank" | "score_desc" | "score_asc" | "name" | "risk_desc";

export function ResultsView({ projectId, api = siteSiftApi }: { projectId: string; api?: ResultsApi }) {
  const [results, setResults] = useState<ScreeningResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<RecommendationStatus | "all">("all");
  const [sort, setSort] = useState<SortKey>("rank");

  const load = useCallback(async () => {
    setResults(null);
    setError(null);
    try {
      setResults(await api.getScreeningResults(projectId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Screening results could not be loaded.");
    }
  }, [api, projectId]);

  useEffect(() => {
    let active = true;
    void api.getScreeningResults(projectId).then(
      (nextResults) => { if (active) setResults(nextResults); },
      (caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Screening results could not be loaded.");
      },
    );
    return () => { active = false; };
  }, [api, projectId]);

  const candidates = useMemo(() => {
    if (!results) return [];
    const filtered = filter === "all" ? results.candidates : results.candidates.filter((candidate) => candidate.score.recommendation_status === filter);
    return [...filtered].sort(sortCandidates(sort));
  }, [filter, results, sort]);

  if (error) {
    return <PageLayout eyebrow="Screening results" title="Results unavailable"><ErrorState title="Could not load ranking" message={error} onRetry={() => void load()} /></PageLayout>;
  }
  if (!results) {
    return <PageLayout eyebrow="Screening results" title="Loading ranking"><LoadingState label="Loading ranked candidate sites…" /></PageLayout>;
  }

  const counts = countStatuses(results.candidates);
  return (
    <PageLayout
      eyebrow="Screening complete"
      title={results.project.name}
      description={`${results.candidates.length} candidate site${results.candidates.length === 1 ? "" : "s"} screened with deterministic rules. Select a site to inspect every deduction.`}
      actions={<Link href="/" className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">All projects</Link>}
    >
      <div className="space-y-7">
        <section aria-label="Result summary" className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <SummaryCard label="Top score" value={results.candidates[0]?.score.overall_score ?? "—"} detail="Matches the leading site" />
          <SummaryCard label="Recommended" value={counts.recommended} detail="Strongest candidates" />
          <SummaryCard label="Needs review" value={counts.review} detail="Advance with confirmation" />
          <SummaryCard label="High risk" value={counts.highRisk} detail="Material findings" />
          <SummaryCard label="Rejected" value={counts.reject} detail="Fatal threshold failures" />
        </section>

        <section aria-labelledby="ranking-heading" className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-4 border-b border-slate-200 px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
            <div><h2 id="ranking-heading" className="font-bold text-ink">Candidate ranking</h2><p className="mt-1 text-xs text-slate-500">Scores are out of 100 and use four 25-point categories.</p></div>
            <div className="grid grid-cols-2 gap-2 sm:flex">
              <label className="text-xs font-bold text-slate-600"><span className="sr-only">Filter by status</span><select aria-label="Filter by status" value={filter} onChange={(event) => setFilter(event.target.value as RecommendationStatus | "all")} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 sm:w-auto"><option value="all">All statuses</option><option value="recommended">Recommended</option><option value="recommended_with_review">Recommended with review</option><option value="needs_investigation">Needs investigation</option><option value="high_risk">High risk</option><option value="reject">Reject</option></select></label>
              <label className="text-xs font-bold text-slate-600"><span className="sr-only">Sort candidates</span><select aria-label="Sort candidates" value={sort} onChange={(event) => setSort(event.target.value as SortKey)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 sm:w-auto"><option value="rank">Rank</option><option value="score_desc">Score: high to low</option><option value="score_asc">Score: low to high</option><option value="name">Site name</option><option value="risk_desc">High risks</option></select></label>
            </div>
          </div>
          {candidates.length === 0 ? <div className="p-5"><EmptyState title="No sites match this filter" description="Choose another recommendation status to see candidate sites." /></div> : <CandidateRanking candidates={candidates} />}
        </section>
      </div>
    </PageLayout>
  );
}

function CandidateRanking({ candidates }: { candidates: RankedCandidate[] }) {
  return (
    <>
      <div className="hidden overflow-x-auto lg:block">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-4 py-3 text-center font-bold">Rank</th><th className="px-4 py-3 font-bold">Site name</th><th className="px-4 py-3 font-bold">Overall score</th><th className="px-4 py-3 font-bold">Recommendation</th><th className="px-4 py-3 text-center font-bold">High risk</th><th className="px-4 py-3 text-center font-bold">Warnings</th><th className="px-4 py-3 font-bold">Next action</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {candidates.map((candidate) => <tr key={candidate.site.id} className="hover:bg-slate-50"><td className="px-4 py-4 text-center font-mono text-lg font-bold text-slate-400">{candidate.rank}</td><td className="px-4 py-4"><Link href={`/sites/${candidate.site.id}`} className="font-bold text-forest hover:underline">{candidate.site.name}</Link><p className="mt-1 text-xs text-slate-500">{candidate.site.jurisdiction}</p></td><td className="px-4 py-4"><ScoreDisplay score={candidate.score.overall_score} compact /></td><td className="px-4 py-4"><StatusBadge status={candidate.score.recommendation_status} /></td><td className="px-4 py-4 text-center font-mono font-bold">{candidate.high_risk_finding_count}</td><td className="px-4 py-4 text-center font-mono font-bold">{candidate.warning_count}</td><td className="px-4 py-4 text-slate-600">{candidate.recommended_next_action}</td></tr>)}
          </tbody>
        </table>
      </div>
      <div data-testid="mobile-candidate-list" className="divide-y divide-slate-100 lg:hidden">
        {candidates.map((candidate) => (
          <article key={candidate.site.id} className="p-5">
            <div className="flex items-start gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-100 font-mono text-sm font-bold text-slate-500">{candidate.rank}</span><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-3"><div><Link href={`/sites/${candidate.site.id}`} className="font-bold text-forest hover:underline">{candidate.site.name}</Link><p className="mt-1 text-xs text-slate-500">{candidate.site.jurisdiction}</p></div><ScoreDisplay score={candidate.score.overall_score} compact /></div><div className="mt-3"><StatusBadge status={candidate.score.recommendation_status} /></div><dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3 text-xs"><div><dt className="text-slate-500">High-risk findings</dt><dd className="mt-1 font-mono font-bold text-ink">{candidate.high_risk_finding_count}</dd></div><div><dt className="text-slate-500">Warnings</dt><dd className="mt-1 font-mono font-bold text-ink">{candidate.warning_count}</dd></div><div className="col-span-2"><dt className="text-slate-500">Next action</dt><dd className="mt-1 font-semibold text-ink">{candidate.recommended_next_action}</dd></div></dl></div></div>
          </article>
        ))}
      </div>
    </>
  );
}

function sortCandidates(sort: SortKey): (left: RankedCandidate, right: RankedCandidate) => number {
  if (sort === "score_desc") return (left, right) => right.score.overall_score - left.score.overall_score;
  if (sort === "score_asc") return (left, right) => left.score.overall_score - right.score.overall_score;
  if (sort === "name") return (left, right) => left.site.name.localeCompare(right.site.name);
  if (sort === "risk_desc") return (left, right) => right.high_risk_finding_count - left.high_risk_finding_count;
  return (left, right) => left.rank - right.rank;
}

function countStatuses(candidates: RankedCandidate[]) {
  return {
    recommended: candidates.filter((candidate) => candidate.score.recommendation_status === "recommended").length,
    review: candidates.filter((candidate) => candidate.score.recommendation_status === "recommended_with_review" || candidate.score.recommendation_status === "needs_investigation").length,
    highRisk: candidates.filter((candidate) => candidate.score.recommendation_status === "high_risk").length,
    reject: candidates.filter((candidate) => candidate.score.recommendation_status === "reject").length,
  };
}

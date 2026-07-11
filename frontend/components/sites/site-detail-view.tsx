"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageLayout } from "@/components/layout/page-layout";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { FindingCard } from "@/components/ui/finding-card";
import { ScoreDisplay } from "@/components/ui/score-display";
import { StatusBadge } from "@/components/ui/status-badge";
import { siteSiftApi, type SiteSiftApi } from "@/lib/api";
import type { FindingSeverity, ScoreExplanationItem, SiteDetail } from "@/types/api";

type SiteApi = Pick<SiteSiftApi, "getSite">;

export function SiteDetailView({ siteId, api = siteSiftApi }: { siteId: string; api?: SiteApi }) {
  const [detail, setDetail] = useState<SiteDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setDetail(null);
    setError(null);
    try {
      setDetail(await api.getSite(siteId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Site detail could not be loaded.");
    }
  }, [api, siteId]);

  useEffect(() => {
    let active = true;
    void api.getSite(siteId).then(
      (nextDetail) => { if (active) setDetail(nextDetail); },
      (caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Site detail could not be loaded.");
      },
    );
    return () => { active = false; };
  }, [api, siteId]);

  if (error) return <PageLayout eyebrow="Site assessment" title="Site unavailable"><ErrorState title="Could not load site" message={error} onRetry={() => void load()} /></PageLayout>;
  if (!detail) return <PageLayout eyebrow="Site assessment" title="Loading site"><LoadingState label="Loading score evidence…" /></PageLayout>;

  return (
    <PageLayout
      eyebrow={`Ranked #${detail.rank} · ${detail.site.jurisdiction}`}
      title={detail.site.name}
      description={`Candidate for ${detail.project.name}. The score below is deterministic and every held point is itemized.`}
      actions={<Link href={`/projects/${detail.project.id}/results`} className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">Back to ranking</Link>}
    >
      <div className="space-y-7">
        <section className="grid gap-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:grid-cols-[auto_1fr] lg:p-7">
          <div className="flex flex-col items-center justify-center gap-4 border-b border-slate-200 pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-8">
            <ScoreDisplay score={detail.score.overall_score} />
            <StatusBadge status={detail.score.recommendation_status} />
          </div>
          <div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-bold text-ink">Score breakdown</h2><p className="mt-1 text-sm text-slate-500">Four categories, 25 points each</p></div><span className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">Permitting: Pending document analysis</span></div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <CategoryScore label="Site suitability" score={detail.score.site_suitability_score} />
              <CategoryScore label="Environmental" score={detail.score.environmental_score} />
              <CategoryScore label="Access and proximity" score={detail.score.access_score} />
              <CategoryScore label="Permitting readiness" score={detail.score.permitting_score} pending />
            </div>
          </div>
        </section>

        <section aria-labelledby="explainability-heading">
          <div className="mb-4"><p className="text-xs font-bold uppercase tracking-[0.16em] text-forest">Deterministic audit trail</p><h2 id="explainability-heading" className="mt-1 text-xl font-bold text-ink">How the score was awarded</h2><p className="mt-2 text-sm text-slate-600">Actual values, configured thresholds, and points are shown for every category. Any deduction is visible here.</p></div>
          <div className="grid gap-4 lg:grid-cols-2">{detail.explanations.map((item) => <ScoreRuleCard key={item.id} item={item} />)}</div>
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          <SignalSection title="Positive signals" count={detail.positive_signals.length} tone="positive">
            {detail.positive_signals.length > 0 ? <ul className="space-y-3">{detail.positive_signals.map((signal) => <li key={signal} className="flex gap-3 text-sm leading-6 text-slate-700"><span className="mt-0.5 font-bold text-emerald-700" aria-hidden="true">✓</span><span>{signal}</span></li>)}</ul> : <p className="text-sm text-slate-500">No positive signals are available.</p>}
          </SignalSection>
          <section aria-labelledby="risks-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
            <div className="mb-4 flex items-center justify-between"><h2 id="risks-heading" className="font-bold text-ink">Risks and findings</h2><span className="font-mono text-xs font-bold text-slate-500">{detail.risks.length}</span></div>
            {detail.risks.length > 0 ? <div className="grid gap-3 sm:grid-cols-2">{detail.risks.map((finding) => <FindingCard key={finding.id} finding={finding} />)}</div> : <EmptyState title="No deterministic risks found" description="Continue with permitting and site-control diligence." />}
          </section>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_1.25fr]">
          <SignalSection title="Missing information" count={detail.missing_information.length} tone="missing">
            <ul className="space-y-3">{detail.missing_information.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-slate-700"><span className="mt-0.5 font-bold text-amber-700" aria-hidden="true">?</span><span>{item}</span></li>)}</ul>
          </SignalSection>
          <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800">Permitting readiness</p>
            <h2 className="mt-2 text-xl font-bold text-amber-950">Pending document analysis</h2>
            <p className="mt-3 text-sm leading-6 text-amber-900">No zoning or permitting document has been analyzed for this site. The current mock category value is provisional and must not be interpreted as a permitting determination.</p>
            <button type="button" disabled title="Available after backend document integration" className="mt-5 cursor-not-allowed rounded-md bg-amber-900 px-4 py-2.5 text-sm font-bold text-white opacity-55">Upload permitting document</button>
          </section>
        </div>
      </div>
    </PageLayout>
  );
}

function CategoryScore({ label, score, pending = false }: { label: string; score: number; pending?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3"><span className="text-sm font-semibold text-slate-700">{label}</span><span className="font-mono text-sm font-bold text-ink">{score}/25</span></div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200"><span className="block h-full rounded-full bg-forest" style={{ width: `${score * 4}%` }} /></div>
      {pending ? <p className="mt-2 text-[10px] font-bold uppercase tracking-wide text-amber-700">Pending document analysis</p> : null}
    </div>
  );
}

function ScoreRuleCard({ item }: { item: ScoreExplanationItem }) {
  const deduction = item.points_possible - item.points_awarded;
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-forest">{item.category}</p><h3 className="mt-1 text-sm font-bold text-ink">{item.rule}</h3></div><SeverityPill severity={item.severity} /></div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 rounded-lg bg-slate-50 p-4 text-xs">
        <div><dt className="text-slate-500">Actual value</dt><dd className="mt-1 font-mono font-semibold text-ink">{item.actual_value}</dd></div>
        <div><dt className="text-slate-500">Threshold</dt><dd className="mt-1 font-mono font-semibold text-ink">{item.threshold}</dd></div>
        <div><dt className="text-slate-500">Points possible</dt><dd className="mt-1 font-mono font-semibold text-ink">{item.points_possible}</dd></div>
        <div><dt className="text-slate-500">Points awarded</dt><dd className="mt-1 font-mono font-semibold text-ink">{item.points_awarded} <span className={deduction > 0 ? "text-red-700" : "text-emerald-700"}>{deduction > 0 ? `(-${deduction})` : "(full)"}</span></dd></div>
      </dl>
      <p className="mt-4 text-sm leading-6 text-slate-600">{item.explanation}</p>
    </article>
  );
}

function SeverityPill({ severity }: { severity: FindingSeverity }) {
  const styles: Record<FindingSeverity, string> = { info: "bg-blue-50 text-blue-700", warning: "bg-amber-50 text-amber-800", high: "bg-orange-50 text-orange-800", fatal: "bg-red-50 text-red-800" };
  return <span className={`rounded px-2 py-1 text-[10px] font-bold uppercase ${styles[severity]}`}>{severity}</span>;
}

function SignalSection({ title, count, children, tone }: { title: string; count: number; children: React.ReactNode; tone: "positive" | "missing" }) {
  return <section className={`rounded-xl border bg-white p-5 shadow-sm ${tone === "positive" ? "border-emerald-200" : "border-amber-200"}`}><div className="mb-4 flex items-center justify-between"><h2 className="font-bold text-ink">{title}</h2><span className="font-mono text-xs font-bold text-slate-500">{count}</span></div>{children}</section>;
}

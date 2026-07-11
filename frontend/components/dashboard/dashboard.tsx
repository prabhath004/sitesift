"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageLayout } from "@/components/layout/page-layout";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { ScoreDisplay } from "@/components/ui/score-display";
import { formatProjectType } from "@/components/ui/status-badge";
import { SummaryCard } from "@/components/ui/summary-card";
import { siteSiftApi, type SiteSiftApi } from "@/lib/api";
import type { ProjectDashboardItem } from "@/types/api";

type DashboardApi = Pick<SiteSiftApi, "getProjectDashboard" | "seedDemoProject">;

export function Dashboard({ api = siteSiftApi }: { api?: DashboardApi }) {
  const router = useRouter();
  const [items, setItems] = useState<ProjectDashboardItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    setItems(null);
    try {
      setItems(await api.getProjectDashboard());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Project data could not be loaded.");
    }
  }, [api]);

  useEffect(() => {
    let active = true;
    void api.getProjectDashboard().then(
      (nextItems) => { if (active) setItems(nextItems); },
      (caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "Project data could not be loaded.");
      },
    );
    return () => { active = false; };
  }, [api]);

  const seedDemo = async () => {
    setSeeding(true);
    setError(null);
    try {
      const results = await api.seedDemoProject();
      router.push(`/projects/${results.project.id}/results`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The sample project could not be loaded.");
      setSeeding(false);
    }
  };

  const actions = (
    <>
      <button
        type="button"
        onClick={() => void seedDemo()}
        disabled={seeding}
        className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
      >
        {seeding ? "Loading sample…" : "Load Sample Solar Project"}
      </button>
      <Link href="/projects/new" className="rounded-md bg-forest px-4 py-2.5 text-center text-sm font-bold text-white shadow-sm hover:bg-[#123e39]">
        New Screening
      </Link>
    </>
  );

  return (
    <PageLayout
      eyebrow="Portfolio overview"
      title="Project dashboard"
      description="Screen candidate sites before expensive diligence. Compare transparent results and focus follow-up work where it matters."
      actions={actions}
    >
      {error ? <ErrorState title="Projects unavailable" message={error} onRetry={() => void load()} /> : null}
      {!error && items === null ? <LoadingState label="Loading screening projects…" /> : null}
      {!error && items !== null ? <DashboardContent items={items} actions={actions} /> : null}
    </PageLayout>
  );
}

function DashboardContent({ items, actions }: { items: ProjectDashboardItem[]; actions: React.ReactNode }) {
  const candidateCount = items.reduce((sum, item) => sum + item.candidate_count, 0);
  const highRiskCount = items.reduce((sum, item) => sum + item.high_risk_finding_count, 0);
  const recommendedCount = items.reduce((sum, item) => sum + item.recommended_site_count, 0);
  const activeCount = items.filter(
    (item) => item.project.status === "active" || item.project.status === "screening",
  ).length;

  return (
    <div className="space-y-7">
      <section aria-label="Portfolio summary" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <SummaryCard label="Active screenings" value={activeCount} detail="Projects in this workspace" icon="◫" />
        <SummaryCard label="Candidate sites" value={candidateCount} detail="Across all screenings" icon="⌖" />
        <SummaryCard label="High-risk findings" value={highRiskCount} detail="High and fatal severity" icon="!" />
        <SummaryCard label="Recommended sites" value={recommendedCount} detail="Ready for deeper review" icon="✓" />
      </section>

      {items.length === 0 ? (
        <EmptyState
          title="No screening projects yet."
          description="Upload candidate sites and generate an evidence-backed first-pass assessment."
          action={actions}
        />
      ) : (
        <ProjectsTable items={items} />
      )}
    </div>
  );
}

function ProjectsTable({ items }: { items: ProjectDashboardItem[] }) {
  return (
    <section aria-labelledby="projects-heading" className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
        <h2 id="projects-heading" className="font-bold text-ink">Screening projects</h2>
        <span className="text-xs font-medium text-slate-500">{items.length} total</span>
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-5 py-3 font-bold">Project name</th>
              <th className="px-4 py-3 font-bold">Project type</th>
              <th className="px-4 py-3 text-right font-bold">Candidates</th>
              <th className="px-4 py-3 text-right font-bold">Top score</th>
              <th className="px-4 py-3 font-bold">Status</th>
              <th className="px-5 py-3 font-bold">Updated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <tr key={item.project.id} className="hover:bg-slate-50/70">
                <td className="px-5 py-4"><Link className="font-bold text-forest hover:underline" href={`/projects/${item.project.id}/results`}>{item.project.name}</Link></td>
                <td className="px-4 py-4 text-slate-600">{formatProjectType(item.project.project_type)}</td>
                <td className="px-4 py-4 text-right font-mono font-semibold">{item.candidate_count}</td>
                <td className="px-4 py-4 text-right">{item.top_score === null ? "—" : <ScoreDisplay score={item.top_score} compact />}</td>
                <td className="px-4 py-4"><ProjectStatus status={item.project.status} /></td>
                <td className="px-5 py-4 text-slate-500">{formatDate(item.project.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-slate-100 md:hidden">
        {items.map((item) => (
          <article key={item.project.id} className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Link className="font-bold text-forest hover:underline" href={`/projects/${item.project.id}/results`}>{item.project.name}</Link>
                <p className="mt-1 text-xs text-slate-500">{formatProjectType(item.project.project_type)} · {item.candidate_count} candidates</p>
              </div>
              {item.top_score === null ? null : <ScoreDisplay score={item.top_score} compact />}
            </div>
            <div className="mt-4 flex items-center justify-between"><ProjectStatus status={item.project.status} /><span className="text-xs text-slate-500">{formatDate(item.project.updated_at)}</span></div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ProjectStatus({ status }: { status: string }) {
  return <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold capitalize text-emerald-800">{status.replaceAll("_", " ")}</span>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(new Date(value));
}

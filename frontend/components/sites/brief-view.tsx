"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageLayout } from "@/components/layout/page-layout";
import { ErrorState, LoadingState } from "@/components/states";
import { StatusBadge } from "@/components/ui/status-badge";
import { siteSiftApi, type SiteSiftApi } from "@/lib/api";
import type { RiskFinding, SiteBrief } from "@/types/api";

type BriefApi = Pick<SiteSiftApi, "getSiteBrief">;

/**
 * The printable diligence brief (spec §8.1G).
 *
 * Every value on this page is read from `GET /api/sites/{id}/brief`. Nothing is
 * recomputed here — a brief that recalculated a score could disagree with the
 * screen the reviewer approved it from.
 */
export function BriefView({ siteId, api = siteSiftApi }: { siteId: string; api?: BriefApi }) {
  const [brief, setBrief] = useState<SiteBrief | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBrief(null);
    setError(null);
    try {
      setBrief(await api.getSiteBrief(siteId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The brief could not be generated.");
    }
  }, [api, siteId]);

  useEffect(() => {
    let active = true;
    void api.getSiteBrief(siteId).then(
      (next) => { if (active) setBrief(next); },
      (caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : "The brief could not be generated.");
      },
    );
    return () => { active = false; };
  }, [api, siteId]);

  if (error) return <PageLayout eyebrow="Diligence brief" title="Brief unavailable"><ErrorState title="Could not generate the brief" message={error} onRetry={() => void load()} /></PageLayout>;
  if (!brief) return <PageLayout eyebrow="Diligence brief" title="Preparing brief"><LoadingState label="Generating the diligence brief…" /></PageLayout>;

  return (
    <PageLayout
      eyebrow="Diligence brief"
      title={brief.site.name}
      description={`${brief.project.name} · generated ${new Date(brief.generated_at).toUTCString()}`}
      actions={<Link href={`/sites/${brief.site.id}`} className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">Back to site</Link>}
    >
      <article className="space-y-7 rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:border-0 print:shadow-none">
        <Section title="Project summary">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <Field label="Project" value={brief.project.name} />
            <Field label="Type" value={brief.project.project_type.replaceAll("_", " ")} />
            <Field label="Target capacity" value={brief.project.target_capacity_mw === null ? "Not set" : `${brief.project.target_capacity_mw} MW`} />
            <Field label="Minimum acreage" value={`${brief.project.minimum_acres} acres`} />
            <Field label="Jurisdiction" value={brief.site.jurisdiction} />
            <Field label="Site acreage" value={`${brief.site.acreage} acres`} />
          </dl>
        </Section>

        <Section title="Selected site">
          {brief.score ? (
            <div className="flex flex-wrap items-center gap-4">
              <span className="font-mono text-3xl font-bold text-ink">{brief.score.overall_score}<span className="text-base text-slate-400">/100</span></span>
              <StatusBadge status={brief.score.recommendation_status} />
              <span className="text-sm text-slate-600">Rank #{brief.score.rank}</span>
            </div>
          ) : <p className="text-sm text-slate-500">This site has not been screened.</p>}
          {brief.score ? <p className="mt-3 text-sm leading-6 text-slate-600">{brief.score.explanation}</p> : null}
        </Section>

        <Section title="Candidate ranking">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-slate-500"><tr><th className="py-2 font-bold">Rank</th><th className="py-2 font-bold">Site</th><th className="py-2 text-right font-bold">Score</th><th className="py-2 font-bold">Recommendation</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {brief.candidate_ranking.map((entry) => (
                <tr key={entry.site_id} className={entry.is_selected_site ? "bg-slate-50 font-semibold" : ""}>
                  <td className="py-2 font-mono">{entry.rank}</td>
                  <td className="py-2">{entry.site_name}</td>
                  <td className="py-2 text-right font-mono">{entry.overall_score}</td>
                  <td className="py-2 text-slate-600">{entry.recommendation_status.replaceAll("_", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>

        <Section title="Positive signals"><FindingList findings={brief.positive_signals} empty="No positive signals were recorded." /></Section>
        <Section title="Major risks"><FindingList findings={brief.risks} empty="No risks were found." /></Section>

        <Section title="Permitting requirements">
          {brief.permitting_requirements.length === 0 ? (
            <p className="text-sm text-slate-500">No permitting document has been analyzed for this site.</p>
          ) : (
            <ul className="space-y-4">
              {brief.permitting_requirements.map((finding) => (
                <li key={finding.id} className="border-l-2 border-l-forest pl-4">
                  <p className="text-sm font-bold text-ink">{finding.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{finding.description}</p>
                  <p className="mt-1 text-xs font-bold uppercase text-slate-500">Review status: {finding.review_status}</p>
                  {finding.evidence.map((evidence) => (
                    <blockquote key={evidence.id} className="mt-2 bg-slate-50 p-3 text-xs italic leading-5 text-slate-600">
                      “{evidence.excerpt}”
                      <cite className="mt-1 block not-italic font-bold text-slate-500">{evidence.document_name}, page {evidence.page_number}{evidence.section_name ? `, ${evidence.section_name}` : ""}</cite>
                    </blockquote>
                  ))}
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Missing information"><FindingList findings={brief.missing_information} empty="Every screening input was supplied." /></Section>

        <Section title="Recommended next steps">
          <ol className="list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">
            {brief.recommended_next_steps.map((step) => <li key={step}>{step}</li>)}
          </ol>
        </Section>

        <Section title="Evidence references">
          {brief.documents.length === 0 ? (
            <p className="text-sm text-slate-500">No source documents have been uploaded.</p>
          ) : (
            <ul className="space-y-1 font-mono text-xs text-slate-600">
              {brief.documents.map((document) => (
                <li key={document.id}>{document.filename} · {document.page_count} pages · {document.processing_status.replaceAll("_", " ")}</li>
              ))}
            </ul>
          )}
        </Section>
      </article>
    </PageLayout>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-slate-100 pt-5 first:border-t-0 first:pt-0">
      <h2 className="mb-3 text-xs font-bold uppercase tracking-[0.16em] text-forest">{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-0.5 font-semibold capitalize text-ink">{value}</dd></div>;
}

function FindingList({ findings, empty }: { findings: RiskFinding[]; empty: string }) {
  if (findings.length === 0) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul className="space-y-2 text-sm leading-6 text-slate-700">
      {findings.map((finding) => (
        <li key={finding.id}>
          <strong className="font-semibold text-ink">{finding.title}.</strong> {finding.description}
        </li>
      ))}
    </ul>
  );
}

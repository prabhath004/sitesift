import type { RiskFinding } from "@/types/api";

const severityStyles: Record<RiskFinding["severity"], string> = {
  info: "border-l-blue-500",
  warning: "border-l-amber-500",
  high: "border-l-orange-600",
  fatal: "border-l-red-600",
};

export function FindingCard({ finding }: { finding: RiskFinding }) {
  return (
    <article className={`rounded-lg border border-slate-200 border-l-4 bg-white p-4 ${severityStyles[finding.severity]}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{finding.category}</span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-slate-600">{finding.severity}</span>
      </div>
      <h3 className="mt-2 text-sm font-bold text-ink">{finding.title}</h3>
      <p className="mt-1 text-sm leading-6 text-slate-600">{finding.description}</p>
      {finding.value ? <p className="mt-2 font-mono text-xs text-slate-500">Actual value: {finding.value}</p> : null}
      <p className="mt-3 text-xs text-slate-400">Deterministic screening finding</p>
    </article>
  );
}

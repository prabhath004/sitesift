import type { ReactNode } from "react";

export function SummaryCard({ label, value, detail, icon }: { label: string; value: ReactNode; detail?: string; icon?: ReactNode }) {
  return (
    <article className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p>
          <p className="mt-3 font-mono text-3xl font-bold tracking-tight text-ink">{value}</p>
        </div>
        {icon ? <span className="grid h-9 w-9 place-items-center rounded-lg bg-mint text-forest" aria-hidden="true">{icon}</span> : null}
      </div>
      {detail ? <p className="mt-3 text-xs leading-5 text-slate-500">{detail}</p> : null}
    </article>
  );
}

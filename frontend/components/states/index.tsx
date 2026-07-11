import type { ReactNode } from "react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="rounded-xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
      <span className="mx-auto mb-4 block h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-forest motion-reduce:animate-none" />
      <p className="text-sm font-medium text-slate-600">{label}</p>
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-sm">
      <span className="mx-auto mb-4 grid h-11 w-11 place-items-center rounded-full bg-mint text-forest" aria-hidden="true">＋</span>
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      {description ? <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, onRetry }: { title?: string; message?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-6 py-7">
      <p className="text-sm font-bold text-red-950">{title}</p>
      {message ? <p className="mt-2 text-sm leading-6 text-red-800">{message}</p> : null}
      {onRetry ? (
        <button type="button" onClick={onRetry} className="mt-4 rounded-md border border-red-300 bg-white px-3.5 py-2 text-sm font-semibold text-red-900 hover:bg-red-100">
          Try again
        </button>
      ) : null}
    </div>
  );
}

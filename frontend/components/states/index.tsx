import type { ReactNode } from "react";

/**
 * Loading, empty, and error placeholders.
 *
 * Every data-backed view is expected to use these three so that the product's
 * async states look the same everywhere (spec §20 — loading and failure states
 * are tested).
 */

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      role="status"
      className="rounded-md border border-slate-200 bg-white px-6 py-10 text-center text-sm text-slate-500"
    >
      {label}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <p className="text-sm font-medium text-slate-900">{title}</p>
      {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 px-6 py-6">
      <p className="text-sm font-medium text-red-900">{title}</p>
      {message ? <p className="mt-1 text-sm text-red-700">{message}</p> : null}
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded border border-red-300 bg-white px-3 py-1.5 text-sm text-red-900 hover:bg-red-100"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}

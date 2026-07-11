"use client";

import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/states";
import { API_BASE_URL, siteSiftApi } from "@/lib/api";
import type { HealthResponse } from "@/types/api";

type Status =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ok"; health: HealthResponse };

async function checkBackend(): Promise<Status> {
  try {
    return { kind: "ok", health: await siteSiftApi.getHealth() };
  } catch (caught) {
    return {
      kind: "error",
      message: caught instanceof Error ? caught.message : "Unknown error",
    };
  }
}

/**
 * Proves the frontend can reach the backend.
 *
 * The foundation's only piece of live data. It verifies the browser → API path
 * (including CORS) end to end, and doubles as the worked example of the
 * loading / error / loaded pattern for feature agents.
 */
export function BackendStatus() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    void checkBackend().then((next) => {
      if (!cancelled) {
        setStatus(next);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const retry = () => {
    setStatus({ kind: "loading" });
    void checkBackend().then(setStatus);
  };

  if (status.kind === "loading") {
    return <LoadingState label="Checking backend…" />;
  }

  if (status.kind === "error") {
    return (
      <ErrorState
        title="Backend unreachable"
        message={`${status.message}. Start it with: cd backend && uvicorn app.main:app --reload`}
        onRetry={retry}
      />
    );
  }

  const { health } = status;

  return (
    <div className="rounded-md border border-slate-200 bg-white px-6 py-5">
      <div className="flex items-center gap-2">
        <span aria-hidden className="h-2 w-2 rounded-full bg-emerald-500" />
        <p className="text-sm font-medium text-slate-900">Backend connected</p>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Service</dt>
          <dd className="font-medium text-slate-900">{health.service}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Version</dt>
          <dd className="font-medium text-slate-900">{health.version}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Environment</dt>
          <dd className="font-medium text-slate-900">{health.environment}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Database</dt>
          <dd className="font-medium text-slate-900">{health.database}</dd>
        </div>
      </dl>
      <p className="mt-4 font-mono text-xs text-slate-400">GET {API_BASE_URL}/health</p>
    </div>
  );
}

import { BackendStatus } from "@/components/backend-status";
import { PageLayout } from "@/components/layout/page-layout";
import { EmptyState } from "@/components/states";

/**
 * Dashboard placeholder.
 *
 * Foundation build: shows the empty state from the spec and proves the frontend
 * can reach the backend. The summary cards, projects table, and "New Screening"
 * flow belong to the frontend agent (docs/PARALLEL_TASKS.md).
 */
export default function DashboardPage() {
  return (
    <PageLayout title="SiteSift" description="Screen candidate sites before expensive diligence">
      <div className="space-y-6">
        <BackendStatus />

        <EmptyState
          title="No screening projects yet."
          description="Upload candidate sites and generate an evidence-backed first-pass assessment."
        />

        <p className="text-xs text-slate-400">
          Foundation build — project intake, screening, document analysis, human review, and the
          diligence brief are not implemented yet. See docs/PARALLEL_TASKS.md.
        </p>
      </div>
    </PageLayout>
  );
}

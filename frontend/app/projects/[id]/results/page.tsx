import { ResultsView } from "@/components/results/results-view";

export default async function ScreeningResultsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ResultsView projectId={id} />;
}

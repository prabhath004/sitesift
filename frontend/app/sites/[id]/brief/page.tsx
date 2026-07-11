import { BriefView } from "@/components/sites/brief-view";

export default async function SiteBriefPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <BriefView siteId={id} />;
}

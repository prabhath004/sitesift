import Link from "next/link";

import { NewScreeningForm } from "@/components/forms/new-screening-form";
import { PageLayout } from "@/components/layout/page-layout";

export default function NewScreeningPage() {
  return (
    <PageLayout
      eyebrow="New project"
      title="Create a screening"
      description="Define your project criteria, validate candidate rows, and run a transparent first-pass assessment."
      actions={<Link href="/" className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">Back to dashboard</Link>}
    >
      <NewScreeningForm />
    </PageLayout>
  );
}

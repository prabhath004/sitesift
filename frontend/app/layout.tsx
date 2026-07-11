import type { Metadata } from "next";

import { Nav } from "@/components/layout/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "SiteSift",
  description:
    "Evidence-backed site triage for renewable energy and power infrastructure projects.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <Nav />
        <main className="flex-1">{children}</main>
        <footer className="mx-auto w-full max-w-6xl px-6 py-10 text-xs text-slate-400">
          SiteSift provides an early-screening prototype. Results are not legal, environmental,
          engineering, utility, title, or investment advice and must be validated by qualified
          professionals.
        </footer>
      </body>
    </html>
  );
}

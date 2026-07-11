import type { Metadata } from "next";

import { Nav } from "@/components/layout/nav";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SiteSift", template: "%s · SiteSift" },
  description: "Evidence-backed site triage for renewable energy and power infrastructure projects.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <a
          href="#main-content"
          className="sr-only z-50 rounded bg-white px-4 py-2 text-sm font-semibold text-forest focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main-content" className="flex-1">{children}</main>
        <footer className="border-t border-slate-200/80 bg-white/70">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-5 py-7 text-xs leading-5 text-slate-500 sm:px-8 lg:flex-row lg:items-start lg:justify-between">
            <span className="font-semibold text-slate-700">SiteSift · Early screening</span>
            <p className="max-w-3xl">
              Results are not legal, environmental, engineering, utility, title, or investment
              advice and must be validated by qualified professionals.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

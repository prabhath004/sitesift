import Link from "next/link";

/**
 * Primary navigation. Routes beyond the dashboard do not exist yet; the
 * frontend agent adds them (see docs/PARALLEL_TASKS.md).
 */
const links = [{ href: "/", label: "Dashboard" }];

export function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-baseline gap-3">
          <span className="text-lg font-semibold tracking-tight text-slate-900">SiteSift</span>
          <span className="hidden text-sm text-slate-500 sm:inline">
            Screen candidate sites before expensive diligence
          </span>
        </Link>
        <nav className="flex gap-6 text-sm">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="text-slate-600 hover:text-slate-900">
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

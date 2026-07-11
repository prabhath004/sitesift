import Link from "next/link";

const links = [
  { href: "/", label: "Projects" },
  { href: "/projects/new", label: "New screening" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/90 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
        <Link href="/" className="group flex items-center gap-3" aria-label="SiteSift dashboard">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-forest text-white shadow-sm">
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path d="M4 6.5 12 3l8 3.5v11L12 21l-8-3.5v-11Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <path d="m4.5 7 7.5 3.3L19.5 7M12 10.3V20" fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
          <span>
            <span className="block text-base font-bold tracking-tight text-ink">SiteSift</span>
            <span className="hidden text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400 sm:block">
              Evidence-led screening
            </span>
          </span>
        </Link>
        <nav aria-label="Primary navigation" className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-ink"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

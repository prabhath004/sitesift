import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        {eyebrow ? <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-forest">{eyebrow}</p> : null}
        <h1 className="text-3xl font-bold tracking-[-0.03em] text-ink sm:text-4xl">{title}</h1>
        {description ? <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}

interface PageLayoutProps extends PageHeaderProps {
  children: ReactNode;
}

export function PageLayout({ children, ...header }: PageLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
      <PageHeader {...header} />
      {children}
    </div>
  );
}

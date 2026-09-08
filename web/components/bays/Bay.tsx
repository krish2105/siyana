import type { ReactNode } from "react";

/**
 * A bay is a solid, hairline-bordered panel with a placard title. Bays vary in size via the
 * grid-area they are given; they are never glass and never animate on their own.
 */
export function Bay({ title, eyebrow, area, children, actions, id }: { title: string; eyebrow?: string; area: string; children: ReactNode; actions?: ReactNode; id?: string }) {
  return (
    <section id={id} aria-labelledby={`${area}-title`} className="bay flex min-h-[220px] flex-col" style={{ gridArea: area }}>
      <header className="hairline-b flex items-start gap-3 px-4 py-3">
        <div className="min-w-0 flex-1">
          {eyebrow && <p className="placard text-ink-muted">{eyebrow}</p>}
          <h2 id={`${area}-title`} className="placard-lg text-[var(--step-1)] text-ink">{title}</h2>
        </div>
        {actions}
      </header>
      <div className="flex-1 px-4 py-3">{children}</div>
    </section>
  );
}

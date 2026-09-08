"use client";

import Link from "next/link";
import { useUiState } from "@/components/providers/UiState";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import type { Summary } from "@/lib/api";

/** Floating glass bar: wordmark, status strip, search (Cmd+K), demo, theme. One of two glass surfaces. */
export function CommandBar({ summary }: { summary: Summary | null }) {
  const { setPaletteOpen, setDemoStep, demoStep } = useUiState();
  const strip = summary
    ? [
        { label: "Tails", value: summary.tails, tone: "" },
        { label: "Open", value: summary.open_defects, tone: summary.open_defects > 0 ? "text-lamp" : "" },
        { label: "Recurring", value: summary.recurring_signatures, tone: summary.recurring_signatures > 0 ? "text-lamp" : "" },
        { label: "U/S", value: summary.unserviceable_tails, tone: summary.unserviceable_tails > 0 ? "text-tag-us" : "" },
        { label: "Drafts", value: summary.drafts_pending, tone: "" },
      ]
    : [];
  return (
    <header className="sticky top-3 z-40 mx-auto w-[min(100%-1.5rem,1400px)]">
      <div className="glass flex min-h-14 flex-wrap items-center gap-x-3 gap-y-2 rounded-[6px] px-3 py-2">
        <Link href="/" className="placard-lg flex items-baseline gap-2 text-ink" aria-label="SIYANA home">
          <span className="text-lg tracking-[0.18em]">SIYANA</span>
          <span className="placard hidden text-ink-muted sm:inline">Miraat control room</span>
        </Link>

        <dl className="hidden items-center gap-4 md:flex" aria-label="Fleet status">
          {strip.map((s) => (
            <div key={s.label} className="flex items-baseline gap-1.5">
              <dt className="placard text-ink-muted">{s.label}</dt>
              <dd className={`code text-sm ${s.tone}`}>{s.value}</dd>
            </div>
          ))}
        </dl>

        <nav aria-label="Pages" className="hidden items-center gap-1 lg:flex">
          <Link href="/inspect" className="placard rounded-[3px] px-2 py-2 text-ink-muted hover:text-ink">Inspect</Link>
          <Link href="/audit" className="placard rounded-[3px] px-2 py-2 text-ink-muted hover:text-ink">Audit</Link>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex h-9 items-center gap-2 rounded-[3px] border border-hairline bg-surface-2 px-3 text-sm text-ink-muted hover:text-ink"
            aria-keyshortcuts="Meta+K Control+K"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <span className="hidden sm:inline">Search or paste a snag</span>
            <kbd className="code hidden rounded-[2px] border border-hairline px-1 text-[0.66rem] sm:inline">⌘K</kbd>
          </button>
          <button
            type="button"
            onClick={() => setDemoStep(demoStep === null ? 0 : null)}
            aria-pressed={demoStep !== null}
            className="hidden h-9 items-center rounded-[3px] border border-hairline bg-surface-2 px-3 text-sm text-ink-muted hover:text-ink md:flex"
          >
            {demoStep === null ? "Run demo" : "Stop demo"}
          </button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

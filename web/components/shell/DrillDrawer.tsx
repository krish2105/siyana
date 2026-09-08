"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AirframePlan } from "@/components/hero/AirframePlan";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import { API_URL, type ChapterDrill, type Zone } from "@/lib/api";
import { formatDate } from "@/lib/severity";

/**
 * Drill-in drawer, driven by ?ata=NN so every chapter is a deep link. The second of the two
 * glass surfaces. Traps focus, closes on Escape, and returns focus to the element that opened it.
 */
export function DrillDrawer({ zones }: { zones: Zone[] }) {
  const params = useSearchParams();
  const chapter = params.get("ata");
  if (!chapter) return null;
  return <DrawerBody key={chapter} chapter={chapter} zones={zones} />;
}

function DrawerBody({ chapter, zones }: { chapter: string; zones: Zone[] }) {
  const router = useRouter();
  const [data, setData] = useState<ChapterDrill | null>(null);
  const [error, setError] = useState<string | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);

  useEffect(() => {
    opener.current = document.activeElement;
    fetch(`${API_URL}/fleet/ata/${chapter}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e: Error) => setError(e.message));
    const t = window.setTimeout(() => panel.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus(), 30);
    return () => window.clearTimeout(t);
  }, [chapter]);

  const close = () => {
    router.push("/", { scroll: false });
    const el = opener.current as HTMLElement | null;
    window.setTimeout(() => el?.focus?.(), 30);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab" && panel.current) {
        const focusables = panel.current.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])');
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter]);

  const zone = zones.find((z) => z.chapter === chapter);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="presentation">
      <button type="button" aria-label="Close chapter drawer" onClick={close} className="absolute inset-0 cursor-default" style={{ background: "var(--scrim)" }} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drill-title"
        className="glass relative flex h-full w-full max-w-[560px] flex-col overflow-hidden rounded-l-[6px] sm:w-[92vw]"
      >
        <div className="hairline-b flex items-start gap-3 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="placard text-ink-muted">ATA chapter</p>
            <h2 id="drill-title" className="placard-lg flex items-baseline gap-3 text-[var(--step-2)] text-ink">
              <span className="code">{chapter}</span>
              <span className="truncate">{data?.title ?? zone?.title ?? "Loading…"}</span>
            </h2>
          </div>
          <button type="button" data-autofocus onClick={close} className="flex h-10 w-10 items-center justify-center rounded-[3px] border border-hairline bg-surface-2 text-ink-muted hover:text-ink" aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scroll-thin px-4 pb-6">
          <div className="py-3">
            <AirframePlan zones={zones} highlight={chapter} compact animate={false} />
          </div>

          {error && <p className="text-sm text-tag-us">Could not load chapter: {error}. Is the API running on {API_URL}?</p>}
          {!data && !error && <p className="text-sm text-ink-muted">Loading chapter…</p>}

          {data && (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
                <span className={`tag ${zone && zone.max_severity_rank >= 3 ? "tag-us" : zone && zone.open_count > 0 ? "tag-lamp" : "tag-quiet"}`}>
                  {data.open_count} open
                </span>
                <span className="tag tag-quiet">{data.signatures.length} signatures</span>
                <span className="tag tag-quiet">{data.cards.length} cards</span>
              </div>

              {data.signatures.length > 0 && (
                <section aria-labelledby="drill-sigs" className="mb-5">
                  <h3 id="drill-sigs" className="placard mb-2 text-ink-muted">Recurring signatures</h3>
                  <ul className="space-y-2">
                    {data.signatures.map((s) => (
                      <li key={s.id} className="bay-raised p-3 text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-ink">{s.canonical}</p>
                          <EvidenceLink id={s.evidence_id} />
                        </div>
                        <p className="code mt-1 text-xs text-ink-muted">
                          ×{s.count} · {s.aircraft_type ?? "type n/a"} · last {formatDate(s.last_seen)}
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {data.cards.length > 0 && (
                <section aria-labelledby="drill-cards" className="mb-5">
                  <h3 id="drill-cards" className="placard mb-2 text-ink-muted">Rectification cards</h3>
                  <ul className="space-y-1">
                    {data.cards.map((c) => (
                      <li key={c.id} className="flex items-center justify-between gap-2 text-sm">
                        <Link href={`/?ata=${chapter}&card=${c.id}`} scroll={false} className="truncate text-ink underline-offset-2 hover:underline">{c.title}</Link>
                        <span className={`tag ${c.status === "DRAFT" ? "tag-lamp" : c.status === "APPROVED" ? "tag-serv" : "tag-quiet"}`}>{c.status}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <section aria-labelledby="drill-snags">
                <h3 id="drill-snags" className="placard mb-2 text-ink-muted">Open snags, newest first</h3>
                {data.snags.length === 0 ? (
                  <p className="text-sm text-ink-muted">No open snags in this chapter for the current window.</p>
                ) : (
                  <ul className="space-y-2">
                    {data.snags.map((s) => (
                      <li key={s.id} className="hairline-b pb-2 text-sm">
                        <div className="code flex flex-wrap gap-x-3 text-xs text-ink-muted">
                          <span className="text-ink">{s.tail ?? "—"}</span>
                          <span>{formatDate(s.occurred_at)}</span>
                          <span>{s.ata_code}</span>
                          <span>WO {s.work_order_id ?? "—"}</span>
                          {s.signature_id && <span className="text-lamp">recurring</span>}
                        </div>
                        <p className="mt-0.5 text-ink">{s.text}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useUiState } from "@/components/providers/UiState";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import { RAIL_CHAPTERS } from "@/lib/airframe";
import { API_URL, type JudgeResponse, type TailRow, type Zone } from "@/lib/api";
import { formatDate } from "@/lib/severity";

type Item = { id: string; group: "Chapters" | "Tails" | "Actions"; label: string; hint: string; run: () => void };

/**
 * Cmd+K. Jump to a chapter or a tail, or paste a free-text snag and DALEEL judges it live:
 * normalise, classify, retrieve k=20 neighbours, judge, and write the evidence row.
 */
export function CommandPalette({ zones, tails }: { zones: Zone[]; tails: TailRow[] }) {
  const { paletteOpen, setPaletteOpen } = useUiState();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
      if (e.key === "Escape" && paletteOpen) setPaletteOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [paletteOpen, setPaletteOpen]);

  if (!paletteOpen) return null;
  return <PaletteBody zones={zones} tails={tails} />;
}

function PaletteBody({ zones, tails }: { zones: Zone[]; tails: TailRow[] }) {
  const { setPaletteOpen, setFocusedTail } = useUiState();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [judging, setJudging] = useState(false);
  const [result, setResult] = useState<JudgeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();

  useEffect(() => {
    const t = window.setTimeout(() => input.current?.focus(), 20);
    return () => window.clearTimeout(t);
  }, []);

  const looksLikeSnag = q.trim().length > 25 && q.trim().split(/\s+/).length >= 4;

  const items: Item[] = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const out: Item[] = [];
    const byChapter = new Map(zones.map((z) => [z.chapter, z]));
    if (looksLikeSnag) {
      out.push({ id: "judge", group: "Actions", label: "Judge this snag with DALEEL", hint: "normalise → classify ATA → retrieve k=20 → judge", run: () => void judge() });
    }
    if (!looksLikeSnag) {
      RAIL_CHAPTERS.filter((c) => !needle || c.chapter.includes(needle) || c.title.toLowerCase().includes(needle))
        .slice(0, 8)
        .forEach((c) => {
          const z = byChapter.get(c.chapter);
          out.push({ id: `ch-${c.chapter}`, group: "Chapters", label: `${c.chapter} ${c.title}`, hint: z ? `${z.open_count} open · S${z.max_severity_rank}` : "no open defects", run: () => { setPaletteOpen(false); router.push(`/?ata=${c.chapter}`, { scroll: false }); } });
        });
      tails.filter((t) => !needle || t.registration.toLowerCase().includes(needle) || t.aircraft_type.toLowerCase().includes(needle))
        .slice(0, 8)
        .forEach((t) => {
          out.push({ id: `tail-${t.registration}`, group: "Tails", label: t.registration, hint: `${t.aircraft_type} · ${t.open_defects} open · ${t.status}`, run: () => { setFocusedTail(t.registration); setPaletteOpen(false); window.scrollTo({ top: 0, behavior: "smooth" }); } });
        });
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, zones, tails, looksLikeSnag]);

  async function judge() {
    setJudging(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${API_URL}/daleel/judge`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: q.trim() }) });
      if (!r.ok) throw new Error((await r.json()).detail ?? `HTTP ${r.status}`);
      setResult((await r.json()) as JudgeResponse);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setJudging(false);
    }
  }

  const activeId = items[active]?.id;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center px-3 pt-[10vh]" role="presentation">
      <button type="button" aria-label="Close search" onClick={() => setPaletteOpen(false)} className="absolute inset-0 cursor-default" style={{ background: "var(--scrim)" }} />
      <div role="dialog" aria-modal="true" aria-label="Search and snag judge" className="bay-raised relative w-full max-w-2xl overflow-hidden shadow-2xl">
        <div className="hairline-b flex items-center gap-2 px-3">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" className="text-ink-muted"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input
            ref={input}
            role="combobox"
            aria-expanded
            aria-controls={listId}
            aria-activedescendant={activeId}
            aria-autocomplete="list"
            value={q}
            onChange={(e) => { setQ(e.target.value); setActive(0); setResult(null); }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(items.length - 1, a + 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
              if (e.key === "Enter" && items[active]) { e.preventDefault(); items[active].run(); }
            }}
            placeholder="Type a tail, an ATA chapter, or paste a snag…"
            className="h-12 w-full bg-transparent text-ink outline-none placeholder:text-ink-muted"
          />
          <kbd className="code rounded-[2px] border border-hairline px-1 text-[0.66rem] text-ink-muted">esc</kbd>
        </div>

        <ul id={listId} role="listbox" className="max-h-[40vh] overflow-y-auto scroll-thin py-1">
          {items.length === 0 && <li className="px-3 py-2 text-sm text-ink-muted">No matches. Paste a longer snag to judge it.</li>}
          {(["Actions", "Chapters", "Tails"] as const).map((g) => {
            const group = items.filter((i) => i.group === g);
            if (group.length === 0) return null;
            return (
              <li key={g} role="presentation">
                <p className="placard px-3 pb-1 pt-2 text-ink-muted">{g}</p>
                <ul role="group" aria-label={g}>
                  {group.map((it) => {
                    const idx = items.indexOf(it);
                    return (
                      <li key={it.id} id={it.id} role="option" aria-selected={idx === active}>
                        <button type="button" tabIndex={-1} onMouseEnter={() => setActive(idx)} onClick={it.run} className={`flex min-h-11 w-full items-center justify-between gap-3 px-3 py-1.5 text-left text-sm ${idx === active ? "bg-surface-1 text-ink" : "text-ink"}`}>
                          <span className={it.group === "Tails" || it.group === "Chapters" ? "code" : ""}>{it.label}</span>
                          <span className="code text-xs text-ink-muted">{it.hint}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </li>
            );
          })}
        </ul>

        {(judging || result || error) && (
          <div className="hairline-b border-t px-3 py-3 text-sm" aria-live="polite">
            {judging && <p className="text-ink-muted">Judging… normalising, classifying, retrieving 20 neighbours, asking the judge.</p>}
            {error && <p className="text-tag-us">Judge failed: {error}</p>}
            {result && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`tag ${result.is_recurrence ? "tag-us" : "tag-serv"}`}>{result.is_recurrence ? "Recurrence" : "No recurrence"}</span>
                  <span className="tag tag-quiet">ATA {result.ata_code ?? "?"}{result.ata_confidence !== null ? ` · ${(result.ata_confidence * 100).toFixed(0)}%` : ""}</span>
                  <span className="tag tag-quiet">conf {result.confidence.toFixed(2)}</span>
                  <span className="ml-auto"><EvidenceLink id={result.evidence_id} /></span>
                </div>
                <p className="text-ink"><span className="placard text-ink-muted">Signature</span> {result.signature}</p>
                <p className="text-ink-muted">{result.reasoning}</p>
                <p className="code text-xs text-ink-muted">judge {result.judge_model} · normalised: {result.norm_text.slice(0, 120)}{result.norm_text.length > 120 ? "…" : ""}</p>
                <details>
                  <summary className="placard cursor-pointer text-ink-muted">{result.neighbours.length} neighbours shown to the judge</summary>
                  <ol className="mt-2 max-h-48 space-y-1.5 overflow-y-auto scroll-thin">
                    {result.neighbours.map((n) => (
                      <li key={n.id} className={`text-xs ${result.matched_ids.includes(n.id) ? "text-ink" : "text-ink-muted"}`}>
                        <span className="code">[{n.id}] {n.tail ?? "—"} · {formatDate(n.occurred_at)} · cos {n.similarity.toFixed(2)}{result.matched_ids.includes(n.id) ? " · matched" : ""}</span>
                        <span className="block">{n.text.slice(0, 180)}{n.text.length > 180 ? "…" : ""}</span>
                      </li>
                    ))}
                  </ol>
                </details>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

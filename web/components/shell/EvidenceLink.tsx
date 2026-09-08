"use client";

import { useEffect, useId, useRef, useState } from "react";
import { API_URL, type Evidence } from "@/lib/api";

/** "Why?" on every AI-derived value. Opens the evidence row: model, hash, confidence, sources. */
export function EvidenceLink({ id, label = "Why?" }: { id: number; label?: string }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Evidence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const popId = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || data) return;
    fetch(`${API_URL}/evidence/${id}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [open, data, id]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={popId}
        onClick={() => setOpen((o) => !o)}
        className="placard rounded-[2px] border border-hairline px-1.5 py-0.5 text-ink-muted hover:text-ink"
      >
        {label} <span className="code normal-case tracking-normal">#{id}</span>
      </button>
      {open && (
        <div id={popId} role="dialog" aria-label={`Evidence ${id}`} className="bay-raised absolute right-0 z-30 mt-1 w-[min(92vw,22rem)] p-3 text-left text-sm shadow-lg">
          {error && <p className="text-tag-us">Could not load evidence: {error}</p>}
          {!data && !error && <p className="text-ink-muted">Loading evidence…</p>}
          {data && (
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <dt className="placard text-ink-muted">Module</dt>
              <dd>{data.module}</dd>
              <dt className="placard text-ink-muted">Model</dt>
              <dd className="code break-all text-xs">{data.model_version}</dd>
              <dt className="placard text-ink-muted">Input hash</dt>
              <dd className="code break-all text-xs">{data.input_sha256.slice(0, 16)}…</dd>
              <dt className="placard text-ink-muted">Confidence</dt>
              <dd className="code">{data.confidence.toFixed(2)}</dd>
              <dt className="placard text-ink-muted">Recorded</dt>
              <dd className="code text-xs">{new Date(data.created_at).toLocaleString("en-GB")}</dd>
              <dt className="placard text-ink-muted">Sources</dt>
              <dd>
                {data.sources.length === 0 ? (
                  <span className="code text-xs">{data.source_ids.map(String).join(", ") || "none"}</span>
                ) : (
                  <ul className="max-h-40 space-y-1 overflow-y-auto scroll-thin">
                    {data.sources.map((s) => (
                      <li key={s.id} className="text-xs">
                        <span className="code text-ink-muted">{s.source.toUpperCase()} {s.source_doc_id}</span>
                        <span className="block text-ink">{s.text.slice(0, 140)}{s.text.length > 140 ? "…" : ""}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </dl>
          )}
        </div>
      )}
    </div>
  );
}

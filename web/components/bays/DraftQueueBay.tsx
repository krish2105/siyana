"use client";

import { useState } from "react";
import { Bay } from "@/components/bays/Bay";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import { API_URL, type Card } from "@/lib/api";

/** DALEEL drafts; a licensed engineer approves or rejects. The licence number is required and logged. */
export function DraftQueueBay({ cards: initial }: { cards: Card[] }) {
  const [cards, setCards] = useState(initial);
  const [openId, setOpenId] = useState<number | null>(initial[0]?.id ?? null);
  const [form, setForm] = useState({ engineer_name: "", licence_number: "", note: "" });
  const [busy, setBusy] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function decide(card: Card, decision: "APPROVED" | "REJECTED") {
    if (!form.licence_number.trim() || !form.engineer_name.trim()) {
      setMessage("Enter your name and licence number. Only a licensed engineer can approve or reject a card.");
      return;
    }
    setBusy(card.id);
    setMessage(null);
    try {
      const r = await fetch(`${API_URL}/daleel/cards/${card.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, decision }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? `HTTP ${r.status}`);
      setCards((cs) => cs.filter((c) => c.id !== card.id));
      setMessage(`Card ${card.id} ${decision.toLowerCase()} by ${form.engineer_name}, licence ${form.licence_number}. Logged in the audit trail.`);
    } catch (e) {
      setMessage(`Could not record decision: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Bay area="queue" eyebrow="DALEEL · awaiting engineer sign-off" title="Draft queue" id="bay-queue">
      {cards.length === 0 ? (
        <p className="text-sm text-ink-muted">Nothing awaiting approval.</p>
      ) : (
        <ul className="space-y-2">
          {cards.map((c) => {
            const open = openId === c.id;
            return (
              <li key={c.id} className="bay-raised">
                <button type="button" aria-expanded={open} onClick={() => setOpenId(open ? null : c.id)} className="flex w-full items-start gap-3 px-3 py-2.5 text-left">
                  <span className="tag tag-lamp mt-0.5 shrink-0">Draft</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-ink">{c.body.title}</span>
                    <span className="code block text-xs text-ink-muted">ATA {c.body.ata_code} · ×{c.body.recurrence_count} · {c.body.tails.join(" ")}</span>
                  </span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" className={`mt-1 shrink-0 text-ink-muted t-fast ${open ? "rotate-180" : ""}`}><path d="m6 9 6 6 6-6" /></svg>
                </button>
                {open && (
                  <div className="hairline-b border-t px-3 py-3 text-sm">
                    <div className="mb-2 rounded-[3px] border border-lamp/60 px-2 py-1.5 text-xs text-ink">
                      <span className="tag tag-lamp">Draft</span> {c.body.disclaimer}
                    </div>
                    <p className="text-ink">{c.body.proposed_action}</p>
                    <h3 className="placard mt-3 text-ink-muted">Source snags</h3>
                    <ul className="mt-1 space-y-1">
                      {c.body.source_snags.map((s) => (
                        <li key={s.id} className="text-xs">
                          <span className="code text-ink-muted">{s.tail ?? "—"} · {s.source.toUpperCase()} {s.source_doc_id}</span>
                          <span className="block text-ink">{s.text}</span>
                        </li>
                      ))}
                    </ul>
                    <h3 className="placard mt-3 text-ink-muted">Work orders</h3>
                    <p className="code text-xs text-ink">{c.body.work_order_ids.join("  ") || "—"}</p>
                    <h3 className="placard mt-3 text-ink-muted">References</h3>
                    <ul className="list-inside list-disc text-xs text-ink">
                      {c.body.references.map((r) => <li key={r}>{r}</li>)}
                    </ul>
                    <div className="mt-3 flex items-center justify-between gap-2">
                      <span className="code text-xs text-ink-muted">drafted by {c.body.drafted_by}</span>
                      <EvidenceLink id={c.evidence_id} />
                    </div>

                    <form className="mt-4 grid gap-2 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
                      <label className="text-xs text-ink-muted">
                        Engineer name
                        <input required value={form.engineer_name} onChange={(e) => setForm({ ...form, engineer_name: e.target.value })} className="mt-1 h-10 w-full rounded-[3px] border border-hairline bg-surface-1 px-2 text-sm text-ink" autoComplete="name" />
                      </label>
                      <label className="text-xs text-ink-muted">
                        Licence number <span aria-hidden="true">*</span>
                        <input required value={form.licence_number} onChange={(e) => setForm({ ...form, licence_number: e.target.value })} className="code mt-1 h-10 w-full rounded-[3px] border border-hairline bg-surface-1 px-2 text-sm text-ink" placeholder="DGCA-B1-00000" />
                      </label>
                      <label className="text-xs text-ink-muted sm:col-span-2">
                        Note
                        <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} className="mt-1 h-10 w-full rounded-[3px] border border-hairline bg-surface-1 px-2 text-sm text-ink" />
                      </label>
                      <div className="flex gap-2 sm:col-span-2">
                        <button type="button" disabled={busy === c.id} onClick={() => decide(c, "APPROVED")} className="tag-serv h-10 flex-1 rounded-[3px] bg-surface-1 px-3 text-sm font-medium text-ink disabled:opacity-50">
                          {busy === c.id ? "Recording…" : "Approve card"}
                        </button>
                        <button type="button" disabled={busy === c.id} onClick={() => decide(c, "REJECTED")} className="h-10 flex-1 rounded-[3px] border border-hairline bg-surface-1 px-3 text-sm text-ink disabled:opacity-50">
                          Reject
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
      {message && <p role="status" aria-live="polite" className="mt-3 text-sm text-ink">{message}</p>}
    </Bay>
  );
}

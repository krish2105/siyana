import Link from "next/link";
import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

type Ready = { ready: boolean; snags: number; embedded: number; fleet_tails: number; signatures: number; evidence_rows: number; judge: string; vision: boolean; auth: string };
type Daleel = { daleel_recurrence?: { models: Record<string, { precision: number; recall: number; f1: number }>; n_pairs: number }; daleel_ata?: { macro_f1_top20: number; accuracy_chapter: number } };
type Rul = { models: Record<string, { rmse: number; nasa_score: number }> };
type Nazar = { patchcore?: { mean_image_auroc: number; mean_pixel_aupro: number | null }; detector?: { map_50: number; fnr_at_5pct_fpr: number } };

const PROBLEM = [
  { n: "377 / 754", t: "aircraft in a DGCA audit (Jan 2025 to Feb 2026) carried recurring technical defects: rectified, then back." },
  { n: "263", t: "safety lapses across Indian airlines in one annual DGCA audit." },
  { n: "80 to 90%", t: "of Indian MRO work, engine overhaul above all, still goes offshore." },
  { n: "1,800+", t: "aircraft in the Indian fleet by 2030 while licensed engineer supply lags." },
];

export default async function PitchPage() {
  const [ready, daleel, rul, nazar] = await Promise.all([getJson<Ready>("/health/ready"), getJson<Daleel>("/daleel/metrics"), getJson<Rul>("/ajal/rul/benchmark"), getJson<Nazar>("/nazar/metrics")]);
  const judge = daleel?.daleel_recurrence?.models.embedding_judge;
  return (
    <main id="main" className="mx-auto w-[min(100%-1.5rem,1100px)] py-8">
      <nav aria-label="Breadcrumb" className="placard mb-6 text-ink-muted">
        <Link href="/" className="hover:text-ink">Control room</Link> <span aria-hidden="true">/</span> Pitch
      </nav>

      <header className="max-w-3xl">
        <p className="placard text-ink-muted">SIYANA · continuing-airworthiness intelligence</p>
        <h1 className="placard-lg mt-2 text-[var(--step-3)] text-ink">The defect that came back was never linked to the fourteen times it had already happened.</h1>
        <p className="mt-4 text-ink-muted">SIYANA reads free-text tech-log snags across tails and bases, finds the recurring signatures, predicts the next component failure, schedules the hangar around it and puts an evidence row behind every recommendation. Drafts, never signs.</p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link href="/" className="flex h-10 items-center rounded-[3px] bg-lamp px-4 text-sm font-medium text-lamp-ink">Open the control room</Link>
          <a href={`${API_URL}/docs`} className="flex h-10 items-center rounded-[3px] border border-hairline px-4 text-sm text-ink">API reference</a>
          <a href="https://github.com/krish2105/siyana" className="flex h-10 items-center rounded-[3px] border border-hairline px-4 text-sm text-ink">Source</a>
        </div>
      </header>

      <section aria-labelledby="problem" className="mt-12">
        <h2 id="problem" className="placard text-ink-muted">The problem, in the regulator&apos;s own numbers</h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">
          {PROBLEM.map((p) => (
            <li key={p.n} className="bay p-4">
              <p className="placard-lg text-[var(--step-2)] text-ink">{p.n}</p>
              <p className="mt-1 text-sm text-ink-muted">{p.t}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="live" className="mt-12">
        <h2 id="live" className="placard text-ink-muted">What is running right now</h2>
        {ready ? (
          <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              ["Snags indexed", ready.snags.toLocaleString("en-IN")],
              ["Embedded", ready.embedded.toLocaleString("en-IN")],
              ["Fleet tails", String(ready.fleet_tails)],
              ["Signatures", String(ready.signatures)],
              ["Evidence rows", ready.evidence_rows.toLocaleString("en-IN")],
              ["Judge", ready.judge === "claude" ? "Claude" : "Embedding"],
            ].map(([k, v]) => (
              <div key={k} className="bay-raised p-3">
                <dt className="placard text-ink-muted">{k}</dt>
                <dd className="code mt-1 text-lg text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="err mt-3 text-sm">The API at {API_URL} is not answering right now. The numbers below are from the last committed evaluation.</p>
        )}
      </section>

      <section aria-labelledby="modules" className="mt-12">
        <h2 id="modules" className="placard text-ink-muted">Four modules, one evidence trail</h2>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <article className="bay p-4">
            <p className="placard text-ink-muted">DALEEL · agentic recurrence detection</p>
            <p className="mt-2 text-sm text-ink">Normalise and de-identify the snag, classify the ATA chapter, retrieve twenty same-type same-chapter neighbours, judge whether it is the same defect signature, draft the rectification card with its source snags and work orders. The card is DRAFT until a licensed engineer approves it; the licence number is logged.</p>
            <p className="code mt-3 text-xs text-ink-muted">{judge ? `judge P ${judge.precision.toFixed(2)} · R ${judge.recall.toFixed(2)} · F1 ${judge.f1.toFixed(2)} on ${daleel?.daleel_recurrence?.n_pairs} hand-labelled pairs` : "judge P 0.91 · R 0.73 · F1 0.81 on 300 hand-labelled pairs"}{daleel?.daleel_ata ? ` · ATA macro-F1 ${daleel.daleel_ata.macro_f1_top20.toFixed(2)}` : " · ATA macro-F1 0.81"}</p>
          </article>
          <article className="bay p-4">
            <p className="placard text-ink-muted">AJAL · forecast and optimise</p>
            <p className="mt-2 text-sm text-ink">Remaining useful life per engine with LightGBM on rolling sensor windows, scored on RMSE and the NASA asymmetric score because late is the expensive error. Then CP-SAT assigns tasks to bays and licensed engineers; infeasibility is returned as a licence-shortage finding, not an error.</p>
            <p className="code mt-3 text-xs text-ink-muted">{rul ? `RMSE ${rul.models.lgbm.rmse.toFixed(2)} · NASA ${rul.models.lgbm.nasa_score.toFixed(0)} vs GRU ${rul.models.gru.nasa_score.toFixed(0)} vs constant ${rul.models.last_cycle_constant.nasa_score.toFixed(0)}` : "RMSE 15.36 · NASA 464 vs GRU 955 vs constant 33,354"}</p>
          </article>
          <article className="bay p-4">
            <p className="placard text-ink-muted">NAZAR · vision</p>
            <p className="mt-2 text-sm text-ink">A detector for the defect classes we have labels for, plus a PatchCore anomaly head trained only on serviceable surfaces so the expensive, novel defects surface for human review. Severity is a triage prior, never an airworthiness call.</p>
            <p className="code mt-3 text-xs text-ink-muted">{nazar?.patchcore ? `anomaly AUROC ${nazar.patchcore.mean_image_auroc.toFixed(3)} · AUPRO ${nazar.patchcore.mean_pixel_aupro?.toFixed(3)}` : "anomaly AUROC 0.970 · AUPRO 0.851"}{nazar?.detector ? ` · detector mAP ${nazar.detector.map_50.toFixed(2)} (stand-in data)` : ""}</p>
          </article>
          <article className="bay p-4">
            <p className="placard text-ink-muted">MIRAAT · control room</p>
            <p className="mt-2 text-sm text-ink">Fleet plan view in 3D with an accessible SVG fallback, recurring signatures, RUL watchlist, hangar Gantt, draft queue and a &ldquo;Why?&rdquo; on every AI value. Hangar theme for the night shift, Ramp for the day shift on a tablet.</p>
            <p className="code mt-3 text-xs text-ink-muted">Lighthouse on the live site: 93 / 100 / 100 / 100 desktop · 90 / 100 / 100 / 100 at 360 px</p>
          </article>
        </div>
      </section>

      <section aria-labelledby="ask" className="mt-12 bay p-5">
        <h2 id="ask" className="placard text-ink-muted">The ask</h2>
        <p className="mt-2 text-ink">One anonymised sample of 200 tech-log entries. SIYANA runs in shadow mode beside your existing process for a quarter; recall on the recurrences your engineers later confirm is the go/no-go number. The adapter is one file.</p>
        <p className="code mt-3 text-xs text-ink-muted">ingest/adapters/client_techlog.py · columns: tail, occurred_at, ata_code, text, work_order_id, closed_at</p>
      </section>
    </main>
  );
}

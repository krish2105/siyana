"use client";

import { useRef, useState } from "react";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import { API_URL } from "@/lib/api";

type Finding = { defect_type: string; bbox: [number, number, number, number]; confidence: number; severity: string; ata_hint: string | null; head: "detector" | "anomaly" };
type Result = { id: number; width: number; height: number; findings: Finding[]; model_version: string; evidence_id: number };

export function InspectPanel({ metrics }: { metrics: { patchcore?: { mean_image_auroc: number; mean_pixel_aupro: number | null; categories: Record<string, { image_auroc: number; fnr_at_5pct_fpr: number }> }; detector?: { map_50: number; fnr_at_5pct_fpr: number } } | null }) {
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    setPreview(URL.createObjectURL(file));
    try {
      const fd = new FormData();
      fd.append("image", file);
      const r = await fetch(`${API_URL}/nazar/inspect`, { method: "POST", body: fd });
      if (!r.ok) throw new Error((await r.json()).detail ?? `HTTP ${r.status}`);
      setResult((await r.json()) as Result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <section className="bay p-4" aria-labelledby="inspect-title">
        <h2 id="inspect-title" className="placard mb-3 text-ink-muted">Image</h2>
        <label className="block">
          <span className="sr-only">Choose an inspection image</span>
          <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} className="block w-full text-sm text-ink file:mr-3 file:h-10 file:rounded-[3px] file:border file:border-hairline file:bg-surface-2 file:px-3 file:text-ink" />
        </label>
        {preview && (
          <div className="relative mt-4 inline-block max-w-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={preview} alt="Uploaded inspection image" className="block max-h-[520px] w-auto max-w-full rounded-[3px] border border-hairline" />
            {result && (
              <svg viewBox={`0 0 ${result.width} ${result.height}`} className="absolute inset-0 h-full w-full" aria-hidden="true">
                {result.findings.map((f, i) => {
                  const [x1, y1, x2, y2] = f.bbox;
                  const colour = f.severity >= "S3" ? "var(--tag-us)" : "var(--lamp)";
                  return (
                    <g key={i}>
                      <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke={colour} strokeWidth={Math.max(2, result.width / 300)} strokeDasharray={f.head === "anomaly" ? "8 6" : undefined} />
                      <text x={x1 + 4} y={Math.max(14, y1 - 6)} fill={colour} fontSize={Math.max(12, result.width / 40)} fontFamily="var(--font-mono)">{f.defect_type} {f.severity}</text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        )}
        {busy && <p className="mt-3 text-sm text-ink-muted" aria-live="polite">Running detector and anomaly head…</p>}
        {error && <p className="mt-3 text-sm text-tag-us" role="alert">Inspection failed: {error}</p>}
      </section>

      <aside className="space-y-4">
        <section className="bay p-4" aria-labelledby="findings-title">
          <div className="flex items-start justify-between gap-2">
            <h2 id="findings-title" className="placard text-ink-muted">Findings</h2>
            {result && <EvidenceLink id={result.evidence_id} />}
          </div>
          {!result ? (
            <p className="mt-2 text-sm text-ink-muted">Upload an image to see findings.</p>
          ) : result.findings.length === 0 ? (
            <p className="mt-2 text-sm text-ink">No findings above threshold. The surface reads as serviceable to both heads.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {result.findings.map((f, i) => (
                <li key={i} className="bay-raised p-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`tag ${f.severity >= "S3" ? "tag-us" : "tag-lamp"}`}>{f.severity}</span>
                    <span className="text-ink">{f.defect_type}</span>
                    <span className="code ml-auto text-xs text-ink-muted">{(f.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <p className="code mt-1 text-xs text-ink-muted">
                    {f.head === "anomaly" ? "anomaly head · review required" : "detector"}{f.ata_hint ? ` · ATA ${f.ata_hint}` : ""} · box {f.bbox.map((v) => v.toFixed(0)).join(",")}
                  </p>
                </li>
              ))}
            </ul>
          )}
          {result && <p className="code mt-3 text-xs text-ink-muted">{result.model_version}</p>}
        </section>

        {metrics?.patchcore && (
          <section className="bay p-4" aria-labelledby="metrics-title">
            <h2 id="metrics-title" className="placard text-ink-muted">Benchmark · MVTec AD</h2>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
              <dt className="text-ink-muted">Image AUROC</dt><dd className="code text-right text-ink">{metrics.patchcore.mean_image_auroc.toFixed(3)}</dd>
              <dt className="text-ink-muted">Pixel AUPRO</dt><dd className="code text-right text-ink">{metrics.patchcore.mean_pixel_aupro?.toFixed(3) ?? "—"}</dd>
              {metrics.detector && (<><dt className="text-ink-muted">Detector mAP@0.5</dt><dd className="code text-right text-ink">{metrics.detector.map_50.toFixed(3)}</dd><dt className="text-ink-muted">Detector FNR @5% FPR</dt><dd className="code text-right text-ink">{metrics.detector.fnr_at_5pct_fpr.toFixed(3)}</dd></>)}
            </dl>
            <ul className="mt-2 space-y-0.5 text-xs text-ink-muted">
              {Object.entries(metrics.patchcore.categories).map(([c, v]) => (
                <li key={c} className="code flex justify-between"><span>{c}</span><span>AUROC {v.image_auroc.toFixed(3)} · FNR {v.fnr_at_5pct_fpr.toFixed(3)}</span></li>
              ))}
            </ul>
          </section>
        )}
      </aside>
    </div>
  );
}

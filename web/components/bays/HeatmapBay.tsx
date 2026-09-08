import Link from "next/link";
import { Bay } from "@/components/bays/Bay";
import type { Heatmap } from "@/lib/api";

/** Tails as rows, ATA chapters as columns. Intensity = defects in the window; a dot marks confirmed recurrence. */
export function HeatmapBay({ heat }: { heat: Heatmap }) {
  const max = Math.max(1, ...heat.cells.map((c) => c.count));
  const lookup = new Map(heat.cells.map((c) => [`${c.tail}|${c.chapter}`, c]));
  return (
    <Bay area="heat" eyebrow="Fleet · last 12 months" title="Recurrence heatmap" id="bay-heatmap">
      {heat.tails.length === 0 ? (
        <p className="text-sm text-ink-muted">No fleet activity to map yet.</p>
      ) : (
        <div className="overflow-x-auto scroll-thin">
          <table className="border-separate border-spacing-[2px] text-xs">
            <caption className="sr-only">Defect counts per tail and ATA chapter over the last {heat.window_days} days</caption>
            <thead>
              <tr>
                <th scope="col" className="sr-only">Tail</th>
                {heat.chapters.map((ch) => (
                  <th key={ch} scope="col" className="code px-1 pb-1 font-medium text-ink-muted">
                    <Link href={`/?ata=${ch}`} scroll={false} className="hover:text-ink">{ch}</Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heat.tails.map((t) => (
                <tr key={t}>
                  <th scope="row" className="code pr-2 text-left font-medium text-ink">{t}</th>
                  {heat.chapters.map((ch) => {
                    const c = lookup.get(`${t}|${ch}`);
                    const n = c?.count ?? 0;
                    const alpha = n === 0 ? 0 : 0.18 + 0.72 * (n / max);
                    const recurring = (c?.recurring ?? 0) > 0;
                    return (
                      <td key={ch} className="p-0">
                        <Link
                          href={`/?ata=${ch}`}
                          scroll={false}
                          aria-label={`${t} ATA ${ch}: ${n} defects${recurring ? ", recurring" : ""}`}
                          className="relative flex h-7 w-7 items-center justify-center rounded-[2px] border border-hairline"
                          style={{ background: n === 0 ? "transparent" : `color-mix(in oklab, ${recurring ? "var(--tag-us)" : "var(--lamp)"} ${Math.round(alpha * 100)}%, var(--surface-1))` }}
                        >
                          {n > 0 && <span className="code text-[0.62rem] text-ink">{n}</span>}
                          {recurring && <span aria-hidden="true" className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-ink" />}
                        </Link>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Bay>
  );
}

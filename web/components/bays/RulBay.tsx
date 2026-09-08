"use client";

import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import { Bay } from "@/components/bays/Bay";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import type { WatchRow } from "@/lib/api";

function Spark({ series, band }: { series: WatchRow["series"]; band: WatchRow["band"] }) {
  const colour = band === "critical" ? "var(--tag-us)" : band === "watch" ? "var(--lamp)" : "var(--ink-muted)";
  return (
    <div className="h-8 w-24" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 2, right: 0, bottom: 2, left: 0 }} accessibilityLayer={false}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line type="monotone" dataKey="s11" stroke={colour} strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RulBay({ rows, benchmark }: { rows: WatchRow[]; benchmark: { rmse: number; nasa_score: number } | null }) {
  return (
    <Bay
      area="rul"
      eyebrow="AJAL"
      title="RUL watchlist"
      id="bay-rul"
      actions={
        benchmark && (
          <p className="code text-right text-xs text-ink-muted" title="LightGBM on C-MAPSS FD001 test set">
            RMSE {benchmark.rmse.toFixed(1)}
            <br />
            NASA {benchmark.nasa_score.toFixed(0)}
          </p>
        )
      }
    >
      {rows.length === 0 ? (
        <p className="text-sm text-ink-muted">No predictions stored. Run the RUL benchmark, then persist the watchlist.</p>
      ) : (
        <table className="w-full text-sm">
          <caption className="sr-only">Engines ranked by predicted remaining useful life in cycles, with the last 30 cycles of core speed sensor 11</caption>
          <thead className="sr-only">
            <tr><th scope="col">Tail</th><th scope="col">Engine</th><th scope="col">Trend</th><th scope="col">Predicted RUL</th><th scope="col">Evidence</th></tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {rows.map((r) => (
              <tr key={`${r.tail}-${r.engine_pos}`}>
                <td className="code py-1.5 pr-2 text-ink">{r.tail}</td>
                <td className="code whitespace-nowrap py-1.5 pr-2 text-ink-muted">ENG {r.engine_pos}</td>
                <td className="py-1.5 pr-2"><Spark series={r.series} band={r.band} /></td>
                <td className="py-1.5 pr-2 text-right">
                  <span className={`code ${r.band === "critical" ? "attn-us" : r.band === "watch" ? "attn" : "text-ink"}`}>{r.predicted_rul.toFixed(0)}</span>
                  <span className="ml-1 text-xs text-ink-muted">cyc</span>
                  <span className="sr-only"> {r.band}</span>
                </td>
                <td className="py-1.5 text-right"><EvidenceLink id={r.evidence_id} label="" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Bay>
  );
}

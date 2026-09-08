import Link from "next/link";
import type { Zone } from "@/lib/api";
import { severityLabel } from "@/lib/severity";

/** The text equivalent of the plan view. Visible, not hidden: engineers scan tables too. */
export function ZoneTable({ zones, windowDays }: { zones: Zone[]; windowDays: number }) {
  return (
    <div className="overflow-x-auto scroll-thin">
      <table className="w-full min-w-[520px] text-sm">
        <caption className="placard px-1 pb-2 text-left text-ink-muted">
          Open defects by ATA chapter, last {windowDays} days of the corpus
        </caption>
        <thead>
          <tr className="hairline-b text-left text-ink-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Chapter</th>
            <th scope="col" className="py-1.5 pr-3 font-medium">System</th>
            <th scope="col" className="py-1.5 pr-3 text-right font-medium">Open</th>
            <th scope="col" className="py-1.5 pr-3 text-right font-medium">Recurring</th>
            <th scope="col" className="py-1.5 pr-3 font-medium">Max severity</th>
            <th scope="col" className="py-1.5 font-medium">Tails</th>
          </tr>
        </thead>
        <tbody>
          {zones.length === 0 ? (
            <tr>
              <td colSpan={6} className="py-3 text-ink-muted">No open defects in this window. Run the SDRS ingest and fleet selection to populate the picture.</td>
            </tr>
          ) : (
            zones.map((z) => (
              <tr key={z.chapter} className="hairline-b">
                <td className="py-1.5 pr-3">
                  <Link href={`/?ata=${z.chapter}`} scroll={false} className="code text-ink underline-offset-2 hover:underline">{z.chapter}</Link>
                </td>
                <td className="py-1.5 pr-3">{z.title}</td>
                <td className="code py-1.5 pr-3 text-right">{z.open_count}</td>
                <td className="code py-1.5 pr-3 text-right">{z.recurring}</td>
                <td className="py-1.5 pr-3">
                  <span className={`tag ${z.max_severity_rank >= 3 ? "tag-us" : "tag-lamp"}`}>S{z.max_severity_rank}</span>
                  <span className="sr-only"> {severityLabel(z.max_severity_rank)}</span>
                </td>
                <td className="code py-1.5 text-ink-muted">{z.tails.slice(0, 4).join(" ")}{z.tails.length > 4 ? ` +${z.tails.length - 4}` : ""}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

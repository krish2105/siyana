"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RAIL_CHAPTERS } from "@/lib/airframe";
import type { Zone } from "@/lib/api";
import { severityToken, severityVar } from "@/lib/severity";

/**
 * The left rail is numbered because ATA chapters are a real numbered taxonomy: the number is
 * the information, not decoration. Below 1024px it becomes a horizontal strip under the bar.
 */
export function AtaRail({ zones }: { zones: Zone[] }) {
  const params = useSearchParams();
  const current = params.get("ata");
  const byChapter = new Map(zones.map((z) => [z.chapter, z]));
  return (
    <nav aria-label="ATA chapters" className="bay lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto scroll-thin">
      <p className="placard hairline-b px-3 py-2 text-ink-muted">ATA chapters</p>
      <ul className="flex gap-1 overflow-x-auto p-2 lg:flex-col lg:overflow-visible">
        {RAIL_CHAPTERS.map(({ chapter, title }) => {
          const z = byChapter.get(chapter);
          const open = z?.open_count ?? 0;
          const active = current === chapter;
          return (
            <li key={chapter} className="shrink-0">
              <Link
                href={`/?ata=${chapter}`}
                scroll={false}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center gap-2 rounded-[3px] px-2 py-1.5 text-sm t-fast hover:bg-surface-2 ${active ? "bg-surface-2 text-ink" : "text-ink-muted"}`}
              >
                <span className="code w-6 text-ink">{chapter}</span>
                <span className="hidden truncate lg:inline">{title}</span>
                {open > 0 ? (
                  <span
                    className={`code ml-auto rounded-[2px] px-1 text-[0.72rem] font-medium leading-4 ${severityToken(z?.max_severity_rank ?? 1) === "tag-us" ? "text-white" : "text-lamp-ink"}`}
                    style={{ background: severityVar(z?.max_severity_rank ?? 1) }}
                    aria-label={`${open} open defects`}
                  >
                    {open}
                  </span>
                ) : (
                  <span className="sr-only">no open defects</span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

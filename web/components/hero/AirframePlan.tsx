"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { AIRFRAME_OUTLINE, VIEWBOX, ZONE_ANCHORS } from "@/lib/airframe";
import type { Zone } from "@/lib/api";
import { severityVar, staggerDelay } from "@/lib/severity";

const DRAW_SECONDS = 0.9;

/**
 * The signature moment. The airframe outline draws itself once on mount (~900ms), then defect
 * zones fade in ordered by SEVERITY, critical first. Zones are real links into the ATA chapter.
 * With prefers-reduced-motion both the draw and the stagger are instant.
 */
export function AirframePlan({
  zones,
  highlight,
  compact = false,
  animate = true,
}: {
  zones: Zone[];
  highlight?: string | null;
  compact?: boolean;
  animate?: boolean;
}) {
  const reduce = useReducedMotion();
  const instant = reduce || !animate;
  const byChapter = new Map(zones.map((z) => [z.chapter, z]));
  return (
    <svg
      viewBox={`0 0 ${VIEWBOX.w} ${VIEWBOX.h}`}
      role="img"
      aria-labelledby="airframe-title airframe-desc"
      className="h-full w-full"
      style={{ maxHeight: compact ? 220 : 520 }}
    >
      <title id="airframe-title">Aircraft plan view with open defects by ATA chapter</title>
      <desc id="airframe-desc">
        {zones.length === 0
          ? "No open defects in the current window."
          : zones.map((z) => `Chapter ${z.chapter} ${z.title}: ${z.open_count} open, severity ${z.max_severity_rank} of 4`).join(". ")}
      </desc>
      <motion.path
        d={AIRFRAME_OUTLINE}
        fill="none"
        stroke="var(--hairline)"
        strokeWidth={1.6}
        strokeLinejoin="round"
        initial={instant ? false : { pathLength: 0, opacity: 0.4 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={instant ? { duration: 0 } : { duration: DRAW_SECONDS, ease: [0.16, 1, 0.3, 1] }}
      />
      <path d={AIRFRAME_OUTLINE} fill="var(--surface-2)" fillOpacity={0.35} stroke="none" pointerEvents="none" />

      {Object.entries(ZONE_ANCHORS).map(([chapter, a]) => {
        const z = byChapter.get(chapter);
        const rank = z?.max_severity_rank ?? 0;
        const open = z?.open_count ?? 0;
        const isHl = highlight === chapter;
        if (open === 0 && !isHl) return null;
        const colour = open === 0 ? "var(--ink-muted)" : severityVar(rank);
        const r = open > 4 ? 15 : open > 1 ? 12 : 9;
        return (
          <motion.g
            key={chapter}
            initial={instant ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={instant ? { duration: 0 } : { delay: staggerDelay(rank, DRAW_SECONDS), duration: 0.3 }}
          >
            <Link href={`/?ata=${chapter}`} scroll={false} aria-label={`ATA ${chapter} ${z?.title ?? a.label}: ${open} open defects. Open chapter.`}>
              <g className="cursor-pointer">
                <circle cx={a.x} cy={a.y} r={r + 8} fill={colour} fillOpacity={isHl ? 0.28 : 0.14} />
                <circle cx={a.x} cy={a.y} r={r} fill={colour} fillOpacity={0.35} stroke={colour} strokeWidth={isHl ? 2 : 1.2} />
                <text
                  x={a.x}
                  y={a.y + 3.5}
                  textAnchor="middle"
                  className="code"
                  fontSize={10.5}
                  fontWeight={600}
                  fill="var(--ink)"
                >
                  {chapter}
                </text>
              </g>
            </Link>
          </motion.g>
        );
      })}
    </svg>
  );
}

/** Severity rank 1..4 -> semantic colour token. Amber = attention, red = unserviceable, never decorative. */
export function severityToken(rank: number): "hairline" | "lamp" | "tag-us" {
  if (rank >= 3) return "tag-us";
  if (rank >= 1) return "lamp";
  return "hairline";
}

export function severityVar(rank: number): string {
  return `var(--${severityToken(rank)})`;
}

export function severityLabel(rank: number): string {
  return ["No open defects", "Open", "Aged or S2", "Recurring or S3", "Recurring and aged, or S4"][Math.max(0, Math.min(4, rank))];
}

/** Zones fade in by severity, critical first. Rank 4 -> 0ms after the draw, rank 1 -> 240ms. */
export function staggerDelay(rank: number, drawSeconds = 0.9): number {
  return drawSeconds + (4 - Math.max(1, rank)) * 0.08;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

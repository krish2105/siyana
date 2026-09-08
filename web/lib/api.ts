/** Typed client for the SIYANA gateway. Server components call these with no-store caching. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Summary = {
  tails: number;
  open_defects: number;
  recurring_signatures: number;
  drafts_pending: number;
  unserviceable_tails: number;
  open_window_days: number;
  corpus_as_of: string | null;
};

export type Zone = {
  chapter: string;
  title: string;
  open_count: number;
  max_severity_rank: number;
  recurring: number;
  tails: string[];
};

export type TailRow = {
  registration: string;
  aircraft_type: string;
  status: "serviceable" | "unserviceable";
  open_defects: number;
  max_severity_rank: number;
  bay_id: string | null;
  chapters: string[];
};

export type Heatmap = {
  tails: string[];
  chapters: string[];
  cells: { tail: string; chapter: string; count: number; recurring: number }[];
  window_days: number;
};

export type Signature = {
  id: number;
  ata_code: string;
  aircraft_type: string | null;
  canonical: string;
  count: number;
  member_snag_ids: number[];
  tails: string[];
  first_seen: string | null;
  last_seen: string | null;
  evidence_id: number;
  card_id: number | null;
  card_status: string | null;
};

export type Card = {
  id: number;
  signature_id: number;
  status: "DRAFT" | "APPROVED" | "REJECTED";
  body: {
    title: string;
    ata_code: string;
    ata_title: string | null;
    aircraft_type: string | null;
    signature: string;
    recurrence_count: number;
    tails: string[];
    source_snags: { id: number; tail: string | null; occurred_at: string | null; text: string; source: string; source_doc_id: string }[];
    work_order_ids: string[];
    proposed_action: string;
    references: string[];
    drafted_by: string;
    disclaimer: string;
  };
  evidence_id: number;
  created_at: string;
};

export type WatchRow = {
  tail: string;
  engine_pos: number;
  unit_id: number;
  dataset: string;
  predicted_rul: number;
  band: "critical" | "watch" | "healthy";
  series: { cycle: number; s11: number }[];
  evidence_id: number;
};

export type Assignment = { task_id: string; bay_id: string; engineer_id: string; start: number; end: number; tail?: string; ata?: string; licence?: string; description?: string; due_by?: number };

export type ScheduleRun = {
  id: number;
  status: "optimal" | "feasible" | "infeasible";
  objective: number | null;
  solve_seconds: number;
  horizon_hours: number;
  assignments: Assignment[];
  licence_shortage: { licence: string; tasks: string[]; hours_required: number; hours_available: number; day?: string; message?: string }[];
  baseline: { name?: string; status?: string; weighted_lateness?: number; cp_sat_weighted_lateness?: number; bays?: { id: string; name: string }[]; engineers?: { id: string; name: string; licences: string[] }[] };
  evidence_id: number;
  created_at: string;
};

export type ChapterDrill = {
  chapter: string;
  title: string;
  open_count: number;
  snags: { id: number; tail: string | null; occurred_at: string | null; text: string; ata_code: string | null; defect_type: string | null; severity: string | null; severity_rank: number; work_order_id: string | null; signature_id: number | null; source: string; source_doc_id: string }[];
  signatures: { id: number; canonical: string; count: number; aircraft_type: string | null; member_snag_ids: number[]; evidence_id: number; last_seen: string | null }[];
  cards: { id: number; signature_id: number; status: string; title: string; evidence_id: number }[];
};

export type Evidence = {
  id: number;
  module: string;
  model_version: string;
  input_sha256: string;
  confidence: number;
  source_ids: (number | string)[];
  created_at: string;
  sources: { id: number; text: string; tail: string | null; source: string; source_doc_id: string }[];
};

export type JudgeResponse = {
  norm_text: string;
  ata_code: string | null;
  ata_confidence: number | null;
  aircraft_type: string | null;
  is_recurrence: boolean;
  matched_ids: number[];
  signature: string;
  reasoning: string;
  confidence: number;
  judge_model: string;
  neighbours: { id: number; text: string; tail: string | null; occurred_at: string | null; work_order_id: string | null; ata_code: string | null; similarity: number }[];
  evidence_id: number;
};

async function get<T>(path: string, fallback: T): Promise<T> {
  try {
    const r = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    if (!r.ok) return fallback;
    return (await r.json()) as T;
  } catch {
    return fallback;
  }
}

export const api = {
  summary: () => get<Summary | null>("/fleet/summary", null),
  zones: () => get<Zone[]>("/fleet/zones", []),
  tails: () => get<TailRow[]>("/fleet/tails", []),
  heatmap: () => get<Heatmap>("/fleet/heatmap", { tails: [], chapters: [], cells: [], window_days: 365 }),
  signatures: (limit = 12) => get<Signature[]>(`/daleel/signatures?limit=${limit}`, []),
  cards: (status = "DRAFT") => get<Card[]>(`/daleel/cards?status=${status}`, []),
  watchlist: () => get<WatchRow[]>("/ajal/rul/watchlist", []),
  schedule: () => get<ScheduleRun | null>("/ajal/schedule/latest", null),
  drill: (chapter: string) => get<ChapterDrill | null>(`/fleet/ata/${chapter}`, null),
  evidence: (id: number) => get<Evidence | null>(`/evidence/${id}`, null),
  approvals: () => get<{ id: number; card_id: number; card_title: string; engineer_name: string; licence_number: string; decision: string; note: string | null; created_at: string; evidence_id: number }[]>("/audit/approvals", []),
};

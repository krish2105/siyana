import { Bay } from "@/components/bays/Bay";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import type { ScheduleRun } from "@/lib/api";

const LICENCE_TONE: Record<string, string> = { "B1.1": "bg-surface-2 text-ink", B2: "bg-ink-muted/20 text-ink", "B1.3": "bg-surface-2 text-ink" };

/** Bays as rows, hours as columns. CP-SAT output rendered as blocks; a licence shortage is a hatched slot. */
export function GanttBay({ run }: { run: ScheduleRun | null }) {
  if (!run) {
    return (
      <Bay area="gantt" eyebrow="AJAL · CP-SAT" title="Hangar schedule" id="bay-gantt">
        <p className="text-sm text-ink-muted">No schedule solved yet. Post to the scheduler to assign open tasks to bays and licensed engineers.</p>
      </Bay>
    );
  }
  const bays = run.baseline.bays ?? Array.from(new Set(run.assignments.map((a) => a.bay_id))).map((id) => ({ id, name: id }));
  const hours = run.horizon_hours;
  const days = Math.ceil(hours / 24);
  const status = run.status === "infeasible" ? { cls: "tag-us", text: "Infeasible: licence shortage" } : run.status === "optimal" ? { cls: "tag-serv", text: "Optimal" } : { cls: "tag-lamp", text: "Feasible" };
  return (
    <Bay
      area="gantt"
      eyebrow="AJAL · CP-SAT"
      title="Hangar schedule"
      id="bay-gantt"
      actions={
        <div className="flex flex-col items-end gap-1">
          <span className={`tag ${status.cls}`}>{status.text}</span>
          <EvidenceLink id={run.evidence_id} />
        </div>
      }
    >
      <div className="overflow-x-auto scroll-thin">
        <div className="min-w-[640px]">
          <div className="grid" style={{ gridTemplateColumns: `7rem repeat(${days}, minmax(0, 1fr))` }} aria-hidden="true">
            <div />
            {Array.from({ length: days }, (_, d) => (
              <div key={d} className="placard hairline-b py-1 text-ink-muted">Day {d + 1}</div>
            ))}
          </div>
          <ol className="divide-y divide-hairline">
            {bays.map((b) => {
              const items = run.assignments.filter((a) => a.bay_id === b.id);
              const gaps = run.licence_shortage.filter((s) => (s as { bay_id?: string }).bay_id === b.id);
              return (
                <li key={b.id} className="grid items-center py-1.5" style={{ gridTemplateColumns: "7rem 1fr" }}>
                  <span className="placard text-ink">{b.name}</span>
                  <div className="relative h-9" role="list" aria-label={`${b.name} assignments`}>
                    {Array.from({ length: days - 1 }, (_, d) => (
                      <span key={d} aria-hidden="true" className="absolute top-0 h-full border-l border-hairline" style={{ left: `${((d + 1) / days) * 100}%` }} />
                    ))}
                    {items.map((a) => (
                      <div
                        key={a.task_id}
                        role="listitem"
                        title={`${a.task_id} ${a.tail ?? ""} ATA ${a.ata ?? ""} ${a.licence ?? ""} h${a.start}-${a.end}`}
                        className={`code absolute top-1 flex h-7 items-center overflow-hidden rounded-[2px] border border-hairline px-1.5 text-[0.68rem] ${LICENCE_TONE[a.licence ?? ""] ?? "bg-surface-2 text-ink"}`}
                        style={{ left: `${(a.start / hours) * 100}%`, width: `${Math.max(1.5, ((a.end - a.start) / hours) * 100)}%` }}
                      >
                        <span className="truncate">{a.tail ?? a.task_id} · {a.ata ?? ""} · {a.licence ?? ""}</span>
                      </div>
                    ))}
                    {gaps.map((g, i) => (
                      <div key={i} role="listitem" className="hatched absolute top-1 h-7 rounded-[2px] border border-tag-us" style={{ left: `${(((g as { start?: number }).start ?? 0) / hours) * 100}%`, width: `${((((g as { end?: number }).end ?? 8) - ((g as { start?: number }).start ?? 0)) / hours) * 100}%` }} title={g.message ?? `Short ${g.licence}`} />
                    ))}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
      {run.licence_shortage.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm" aria-label="Licence shortage findings">
          {run.licence_shortage.map((s, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="tag tag-us mt-0.5">Short</span>
              <span className="text-ink">
                {s.message ?? `${s.licence}: ${s.hours_required}h required, ${s.hours_available}h available`}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="code mt-3 text-xs text-ink-muted">
        {run.assignments.length} tasks · solved in {run.solve_seconds.toFixed(1)}s
        {run.baseline.weighted_lateness !== undefined && run.baseline.cp_sat_weighted_lateness !== undefined
          ? ` · weighted lateness ${run.baseline.cp_sat_weighted_lateness} vs greedy ${run.baseline.weighted_lateness}`
          : ""}
      </p>
    </Bay>
  );
}

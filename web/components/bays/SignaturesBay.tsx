import Link from "next/link";
import { Bay } from "@/components/bays/Bay";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import type { Signature } from "@/lib/api";
import { formatDate } from "@/lib/severity";

export function SignaturesBay({ signatures }: { signatures: Signature[] }) {
  return (
    <Bay area="sig" eyebrow="DALEEL" title="Recurring signatures" id="bay-signatures">
      {signatures.length === 0 ? (
        <p className="text-sm text-ink-muted">No signatures yet. Run the recurrence scan to judge the fleet&apos;s recent snags.</p>
      ) : (
        <ol className="divide-y divide-hairline">
          {signatures.map((s) => (
            <li key={s.id} className="grid grid-cols-[auto_1fr_auto] items-start gap-3 py-2.5 text-sm">
              <Link href={`/?ata=${s.ata_code.slice(0, 2)}`} scroll={false} className="code mt-0.5 rounded-[2px] bg-surface-2 px-1.5 py-0.5 text-ink" aria-label={`ATA ${s.ata_code}`}>
                {s.ata_code}
              </Link>
              <div className="min-w-0">
                <p className="text-ink">{s.canonical}</p>
                <p className="code mt-0.5 text-xs text-ink-muted">
                  <span className="attn">×{s.count}</span> · {s.aircraft_type ?? "type n/a"} · {s.tails.slice(0, 3).join(" ")}{s.tails.length > 3 ? ` +${s.tails.length - 3}` : ""} · last {formatDate(s.last_seen)}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <EvidenceLink id={s.evidence_id} />
                {s.card_status && <span className={`tag ${s.card_status === "DRAFT" ? "tag-lamp" : s.card_status === "APPROVED" ? "tag-serv" : "tag-quiet"}`}>{s.card_status}</span>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Bay>
  );
}

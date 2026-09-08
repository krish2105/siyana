import Link from "next/link";
import { EvidenceLink } from "@/components/shell/EvidenceLink";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/severity";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const rows = await api.approvals();
  return (
    <main id="main" className="mx-auto w-[min(100%-1.5rem,1100px)] py-6">
      <nav aria-label="Breadcrumb" className="placard mb-3 text-ink-muted">
        <Link href="/" className="hover:text-ink">Control room</Link> <span aria-hidden="true">/</span> Audit trail
      </nav>
      <header className="mb-4">
        <p className="placard text-ink-muted">Approvals log</p>
        <h1 className="placard-lg text-[var(--step-3)] text-ink">Who signed what</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">Every rectification card leaves DRAFT only through a decision recorded here with the engineer&apos;s licence number. Each decision links to the evidence row behind the card.</p>
      </header>
      <section className="bay overflow-x-auto scroll-thin">
        <table className="w-full min-w-[720px] text-sm">
          <caption className="sr-only">Card approvals and rejections, newest first</caption>
          <thead>
            <tr className="hairline-b text-left text-ink-muted">
              <th scope="col" className="px-4 py-2 font-medium">When</th>
              <th scope="col" className="px-4 py-2 font-medium">Card</th>
              <th scope="col" className="px-4 py-2 font-medium">Decision</th>
              <th scope="col" className="px-4 py-2 font-medium">Engineer</th>
              <th scope="col" className="px-4 py-2 font-medium">Licence</th>
              <th scope="col" className="px-4 py-2 font-medium">Note</th>
              <th scope="col" className="px-4 py-2 font-medium">Evidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {rows.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-4 text-ink-muted">No decisions recorded yet. Approve or reject a draft from the control room&apos;s draft queue.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id}>
                  <td className="code px-4 py-2 text-ink-muted">{formatDate(r.created_at)} {new Date(r.created_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</td>
                  <td className="px-4 py-2 text-ink"><span className="code text-ink-muted">#{r.card_id}</span> {r.card_title}</td>
                  <td className="px-4 py-2"><span className={`tag ${r.decision === "APPROVED" ? "tag-serv" : "tag-quiet"}`}>{r.decision}</span></td>
                  <td className="px-4 py-2 text-ink">{r.engineer_name}</td>
                  <td className="code px-4 py-2 text-ink">{r.licence_number}</td>
                  <td className="px-4 py-2 text-ink-muted">{r.note ?? "—"}</td>
                  <td className="px-4 py-2"><EvidenceLink id={r.evidence_id} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}

import Link from "next/link";
import { InspectPanel } from "@/components/inspect/InspectPanel";
import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function InspectPage() {
  const metrics = await fetch(`${API_URL}/nazar/metrics`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  return (
    <main id="main" className="mx-auto w-[min(100%-1.5rem,1100px)] py-6">
      <nav aria-label="Breadcrumb" className="placard mb-3 text-ink-muted">
        <Link href="/" className="hover:text-ink">Control room</Link> <span aria-hidden="true">/</span> NAZAR inspection
      </nav>
      <header className="mb-4">
        <p className="placard text-ink-muted">NAZAR · vision</p>
        <h1 className="placard-lg text-[var(--step-3)] text-ink">Inspect an image</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Two heads run on every upload: a detector for known classes (crack, corrosion, dent, delamination, missing fastener) and an anomaly head trained only on serviceable surfaces, so novel damage surfaces for review. Severity is a triage prior, not an airworthiness determination.
        </p>
      </header>
      <InspectPanel metrics={metrics} />
    </main>
  );
}

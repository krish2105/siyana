import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="mx-auto w-[min(100%-1.5rem,720px)] py-16">
      <p className="placard text-ink-muted">Not found</p>
      <h1 className="placard-lg mt-1 text-[var(--step-3)] text-ink">No placard at this address</h1>
      <p className="mt-3 text-sm text-ink-muted">The page you asked for does not exist. Chapters are deep-linked as <span className="code">/?ata=72</span>.</p>
      <Link href="/" className="mt-6 inline-flex h-10 items-center rounded-[3px] bg-lamp px-4 text-sm font-medium text-lamp-ink">Back to the fleet picture</Link>
    </main>
  );
}

"use client";

import Link from "next/link";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="main" className="mx-auto w-[min(100%-1.5rem,720px)] py-16">
      <p className="placard text-ink-muted">Something failed</p>
      <h1 className="placard-lg mt-1 text-[var(--step-3)] text-ink">The control room could not render this view</h1>
      <p className="err mt-4 text-sm">{error.message}{error.digest ? ` · ref ${error.digest}` : ""}</p>
      <div className="mt-6 flex gap-2">
        <button type="button" onClick={reset} className="h-10 rounded-[3px] bg-lamp px-4 text-sm font-medium text-lamp-ink">Try again</button>
        <Link href="/" className="flex h-10 items-center rounded-[3px] border border-hairline px-4 text-sm text-ink">Back to the fleet picture</Link>
      </div>
    </main>
  );
}

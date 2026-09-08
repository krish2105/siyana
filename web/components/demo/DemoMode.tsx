"use client";

import { useRouter } from "next/navigation";
import { useUiState } from "@/components/providers/UiState";

type Step = { title: string; say: string; act: (ctx: { router: ReturnType<typeof useRouter>; toggleTheme: () => void; theme: string }) => void };

const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

/**
 * The six-minute pitch as a stepper. Every step runs on a button press, so the one-signature-motion
 * rule holds: nothing here animates on its own.
 */
const STEPS: Step[] = [
  { title: "Fleet picture", say: "This is one operator's fleet, right now. Zones glow by open-defect severity; amber needs attention, red is unserviceable.", act: () => window.scrollTo({ top: 0, behavior: "smooth" }) },
  { title: "Drill into ATA 72", say: "Click the engine zone. Every open snag in the chapter, and the signatures DALEEL found across tails that nobody flagged.", act: ({ router }) => router.push("/?ata=72", { scroll: false }) },
  { title: "Recurring signatures", say: "The same defect written five different ways by five engineers. Semantic retrieval plus a judge catches what keyword search cannot.", act: ({ router }) => { router.push("/", { scroll: false }); window.setTimeout(() => scrollTo("bay-signatures"), 150); } },
  { title: "Draft, never signed", say: "The rectification card cites its source snags and work orders, and it stays DRAFT until a licensed engineer approves it. The licence number is logged.", act: () => scrollTo("bay-queue") },
  { title: "RUL watchlist", say: "Engines ranked by predicted remaining life. Late predictions are penalised harder than early ones, because optimism is the expensive error.", act: () => scrollTo("bay-rul") },
  { title: "Hangar schedule", say: "CP-SAT assigns tasks to bays and licensed engineers. When it proves infeasible, that is a finding: you are short a licence category before the week starts.", act: () => scrollTo("bay-gantt") },
  { title: "Day shift", say: "Toggle to Ramp. Day shift uses it on a tablet on the floor.", act: ({ toggleTheme, theme }) => { if (theme === "hangar") toggleTheme(); window.scrollTo({ top: 0, behavior: "smooth" }); } },
  { title: "Your data", say: "This runs on public FAA data today. Point it at your tech-log export and it runs on yours. What would you want it to catch first?", act: () => undefined },
];

export function DemoMode() {
  const { demoStep, setDemoStep, toggleTheme, theme } = useUiState();
  const router = useRouter();
  if (demoStep === null) return null;
  const step = STEPS[demoStep];
  const go = (n: number) => {
    const next = Math.max(0, Math.min(STEPS.length - 1, n));
    setDemoStep(next);
    STEPS[next].act({ router, toggleTheme, theme });
  };
  return (
    <aside aria-label="Guided demo" className="bay-raised fixed bottom-4 left-1/2 z-40 w-[min(100%-1.5rem,36rem)] -translate-x-1/2 px-4 py-3 shadow-2xl">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="placard text-ink-muted">Demo · step {demoStep + 1} of {STEPS.length} · {step.title}</p>
          <p className="mt-1 text-sm text-ink" aria-live="polite">{step.say}</p>
        </div>
        <button type="button" onClick={() => setDemoStep(null)} className="placard rounded-[2px] border border-hairline px-2 py-1 text-ink-muted hover:text-ink">Stop</button>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" disabled={demoStep === 0} onClick={() => go(demoStep - 1)} className="h-10 rounded-[3px] border border-hairline bg-surface-1 px-3 text-sm text-ink disabled:opacity-40">Back</button>
        {demoStep < STEPS.length - 1 ? (
          <button type="button" onClick={() => go(demoStep + 1)} className="h-10 flex-1 rounded-[3px] bg-lamp px-3 text-sm font-medium text-lamp-ink">Next</button>
        ) : (
          <button type="button" onClick={() => setDemoStep(null)} className="h-10 flex-1 rounded-[3px] bg-lamp px-3 text-sm font-medium text-lamp-ink">Finish</button>
        )}
      </div>
    </aside>
  );
}

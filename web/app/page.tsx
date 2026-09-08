import { Suspense } from "react";
import { DraftQueueBay } from "@/components/bays/DraftQueueBay";
import { GanttBay } from "@/components/bays/GanttBay";
import { HeatmapBay } from "@/components/bays/HeatmapBay";
import { RulBay } from "@/components/bays/RulBay";
import { SignaturesBay } from "@/components/bays/SignaturesBay";
import { DemoMode } from "@/components/demo/DemoMode";
import { HeroSwitch } from "@/components/hero/HeroSwitch";
import { ZoneTable } from "@/components/hero/ZoneTable";
import { CommandPalette } from "@/components/palette/CommandPalette";
import { AtaRail } from "@/components/shell/AtaRail";
import { CommandBar } from "@/components/shell/CommandBar";
import { DrillDrawer } from "@/components/shell/DrillDrawer";
import { API_URL, api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ControlRoom() {
  const [summary, zones, tails, heat, signatures, cards, watchlist, schedule, bench] = await Promise.all([
    api.summary(),
    api.zones(),
    api.tails(),
    api.heatmap(),
    api.signatures(10),
    api.cards("DRAFT"),
    api.watchlist(),
    api.schedule(),
    fetch(`${API_URL}/ajal/rul/benchmark`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]);
  const lgbm = bench?.models?.lgbm ?? null;

  return (
    <>
      <Suspense fallback={null}>
        <CommandBar summary={summary} />
      </Suspense>
      <main id="main" className="mx-auto w-[min(100%-1.5rem,1400px)] pb-16 pt-4">
        {!summary && (
          <p role="alert" className="mb-4 rounded-[3px] border border-lamp px-3 py-2 text-sm text-ink">
            The API at <span className="code">{API_URL}</span> is not answering. Start it with <span className="code">uvicorn services.gateway.main:app</span> and reload.
          </p>
        )}
        <div className="grid gap-4 lg:grid-cols-[13rem_1fr]">
          <Suspense fallback={null}>
            <AtaRail zones={zones} />
          </Suspense>

          <div className="min-w-0 space-y-4">
            <section aria-labelledby="hero-title" className="bay">
              <div className="hairline-b flex flex-wrap items-end justify-between gap-2 px-4 py-3">
                <div>
                  <p className="placard text-ink-muted">Fleet airworthiness picture</p>
                  <h1 id="hero-title" className="placard-lg text-[var(--step-3)] text-ink">
                    {summary ? `${summary.tails} tails · ${summary.open_defects} open defects` : "Control room"}
                  </h1>
                </div>
                {summary?.corpus_as_of && (
                  <p className="code text-xs text-ink-muted">
                    corpus as of {new Date(summary.corpus_as_of).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })} · open = last {summary.open_window_days} days
                  </p>
                )}
              </div>
              <div className="px-2 py-2 sm:px-4">
                <HeroSwitch zones={zones} tails={tails} watchlist={watchlist} schedule={schedule} />
              </div>
              <div className="px-4 pb-4">
                <ZoneTable zones={zones} windowDays={summary?.open_window_days ?? 90} />
              </div>
            </section>

            <div className="bays-grid grid gap-4">
              <SignaturesBay signatures={signatures} />
              <RulBay rows={watchlist} benchmark={lgbm} />
              <GanttBay run={schedule} />
              <HeatmapBay heat={heat} />
              <DraftQueueBay cards={cards} />
            </div>
          </div>
        </div>
      </main>
      <Suspense fallback={null}>
        <DrillDrawer zones={zones} />
      </Suspense>
      <CommandPalette zones={zones} tails={tails} />
      <DemoMode />
    </>
  );
}

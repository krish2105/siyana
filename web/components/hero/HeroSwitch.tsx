"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { AirframePlan } from "@/components/hero/AirframePlan";
import type { TailRow, WatchRow, Zone, ScheduleRun } from "@/lib/api";

const HangarScene = dynamic(() => import("@/components/hero/HangarScene").then((m) => m.HangarScene), {
  ssr: false,
  loading: () => null,
});

/**
 * Progressive enhancement gate. The SVG plan view renders immediately and stays the hero on
 * small screens, reduced motion, no WebGL, or low-core devices. Otherwise the 3D hangar takes over.
 */
export function HeroSwitch({ zones, tails, watchlist, schedule }: { zones: Zone[]; tails: TailRow[]; watchlist: WatchRow[]; schedule: ScheduleRun | null }) {
  const reduce = useReducedMotion();
  const [mode, setMode] = useState<"svg" | "3d">("svg");
  const [forceSvg, setForceSvg] = useState(false);

  useEffect(() => {
    const decide = () => {
      if (reduce || forceSvg) {
        setMode("svg");
        return;
      }
      let ok = false;
      try {
        const c = document.createElement("canvas");
        const gl = c.getContext("webgl2") || c.getContext("webgl");
        const cores = navigator.hardwareConcurrency ?? 4;
        ok = Boolean(gl) && cores > 2 && window.innerWidth >= 768;
      } catch {
        ok = false;
      }
      setMode(ok ? "3d" : "svg");
    };
    queueMicrotask(decide);
    window.addEventListener("resize", decide);
    return () => window.removeEventListener("resize", decide);
  }, [reduce, forceSvg]);

  return (
    <div className="relative aspect-[2/1] min-h-[300px] max-h-[520px] w-full">
      {mode === "3d" ? (
        <HangarScene zones={zones} tails={tails} watchlist={watchlist} schedule={schedule} onUnavailable={() => setForceSvg(true)} />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <AirframePlan zones={zones} />
        </div>
      )}
      {mode === "3d" && (
        <button
          type="button"
          onClick={() => setForceSvg(true)}
          className="placard absolute right-3 top-3 rounded-[3px] border border-hairline bg-surface-1 px-2 py-1 text-ink-muted hover:text-ink"
        >
          Plan view
        </button>
      )}
      {forceSvg && (
        <button
          type="button"
          onClick={() => setForceSvg(false)}
          className="placard absolute right-3 top-3 rounded-[3px] border border-hairline bg-surface-1 px-2 py-1 text-ink-muted hover:text-ink"
        >
          3D hangar
        </button>
      )}
    </div>
  );
}

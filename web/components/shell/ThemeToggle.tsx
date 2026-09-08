"use client";

import { motion, useReducedMotion } from "motion/react";
import { useUiState } from "@/components/providers/UiState";

/**
 * A two-position maintenance-tag switch. The knob is an inspection lamp: lit amber on the
 * HANGAR side (night shift), unlit on RAMP (day shift). Only transform animates.
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useUiState();
  const reduce = useReducedMotion();
  const hangar = theme === "hangar";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={hangar}
      aria-label={`Theme: ${hangar ? "Hangar" : "Ramp"}. Switch to ${hangar ? "Ramp" : "Hangar"}.`}
      onClick={toggleTheme}
      className="group relative flex h-9 items-center gap-2 rounded-[3px] border border-hairline bg-surface-2 px-1.5 text-ink-muted"
    >
      <span className={`placard px-1 ${hangar ? "text-ink" : ""}`}>Hangar</span>
      <span className="relative block h-5 w-11 rounded-full border border-hairline bg-surface-0" aria-hidden="true">
        <motion.span
          className="absolute top-[2px] left-[2px] block h-[14px] w-[14px] rounded-full"
          style={{
            background: hangar ? "var(--lamp)" : "var(--ink-muted)",
            boxShadow: hangar ? "0 0 10px 2px color-mix(in oklab, var(--lamp) 55%, transparent)" : "none",
          }}
          animate={{ x: hangar ? 0 : 22 }}
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 520, damping: 34 }}
        />
      </span>
      <span className={`placard px-1 ${hangar ? "" : "text-ink"}`}>Ramp</span>
    </button>
  );
}

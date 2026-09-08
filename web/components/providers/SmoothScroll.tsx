"use client";

import { ReactLenis } from "lenis/react";
import { useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/** Lenis gives the page its weighted glide. Reduced-motion users get native scroll. */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();
  if (reduce) return <>{children}</>;
  return (
    <ReactLenis root options={{ lerp: 0.12, duration: 1.1, smoothWheel: true }}>
      {children}
    </ReactLenis>
  );
}

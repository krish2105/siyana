"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { setTheme as persistTheme, type Theme } from "@/app/actions";

type UiState = {
  theme: Theme;
  toggleTheme: () => void;
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
  demoStep: number | null;
  setDemoStep: (step: number | null) => void;
  focusedTail: string | null;
  setFocusedTail: (tail: string | null) => void;
};

const Ctx = createContext<UiState | null>(null);

export function UiStateProvider({ children, initialTheme }: { children: ReactNode; initialTheme: Theme }) {
  const [theme, setThemeState] = useState<Theme>(initialTheme);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [demoStep, setDemoStep] = useState<number | null>(null);
  const [focusedTail, setFocusedTail] = useState<string | null>(null);

  const toggleTheme = useCallback(() => {
    const next: Theme = theme === "hangar" ? "ramp" : "hangar";
    setThemeState(next);
    document.documentElement.dataset.theme = next;
    void persistTheme(next);
  }, [theme]);

  const value = useMemo(
    () => ({ theme, toggleTheme, paletteOpen, setPaletteOpen, demoStep, setDemoStep, focusedTail, setFocusedTail }),
    [theme, toggleTheme, paletteOpen, demoStep, focusedTail],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useUiState(): UiState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useUiState must be used inside UiStateProvider");
  return v;
}

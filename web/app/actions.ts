"use server";

import { cookies } from "next/headers";

export type Theme = "hangar" | "ramp";

export async function setTheme(theme: Theme): Promise<void> {
  const jar = await cookies();
  jar.set("theme", theme, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
}

import { describe, expect, it } from "vitest";
import { AIRFRAME_OUTLINE, RAIL_CHAPTERS, VIEWBOX, ZONE_ANCHORS, planTo3D } from "@/lib/airframe";

describe("airframe geometry", () => {
  it("places every rail chapter that has a zone inside the viewBox", () => {
    for (const [chapter, a] of Object.entries(ZONE_ANCHORS)) {
      expect(a.x).toBeGreaterThan(0);
      expect(a.x).toBeLessThan(VIEWBOX.w);
      expect(a.y).toBeGreaterThan(0);
      expect(a.y).toBeLessThan(VIEWBOX.h);
      expect(chapter).toMatch(/^\d{2}$/);
    }
  });
  it("maps the plan view onto the 3D axes with the nose at negative z", () => {
    const [lat, y, z] = planTo3D(90, VIEWBOX.cy);
    expect(lat).toBeCloseTo(0, 5);
    expect(y).toBe(0);
    expect(z).toBeLessThan(0);
    expect(planTo3D(730, VIEWBOX.cy)[2]).toBeGreaterThan(0);
  });
  it("has a single combined outline path and a numbered rail", () => {
    expect(AIRFRAME_OUTLINE.startsWith("M ")).toBe(true);
    expect(RAIL_CHAPTERS.length).toBeGreaterThan(30);
    expect(new Set(RAIL_CHAPTERS.map((c) => c.chapter)).size).toBe(RAIL_CHAPTERS.length);
  });
});

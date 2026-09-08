import { describe, expect, it } from "vitest";
import { formatDate, severityLabel, severityToken, staggerDelay } from "@/lib/severity";

describe("severity mapping", () => {
  it("uses red only for rank 3 and 4, amber for 1 and 2, hairline for none", () => {
    expect(severityToken(4)).toBe("tag-us");
    expect(severityToken(3)).toBe("tag-us");
    expect(severityToken(2)).toBe("lamp");
    expect(severityToken(1)).toBe("lamp");
    expect(severityToken(0)).toBe("hairline");
  });
  it("staggers by severity: critical zones appear first", () => {
    expect(staggerDelay(4)).toBeLessThan(staggerDelay(1));
    expect(staggerDelay(4)).toBeCloseTo(0.9, 5);
    expect(staggerDelay(1)).toBeCloseTo(0.9 + 0.24, 5);
  });
  it("labels every rank and formats dates", () => {
    for (let r = 0; r <= 4; r++) expect(severityLabel(r).length).toBeGreaterThan(3);
    expect(formatDate(null)).toBe("—");
    expect(formatDate("2025-12-22T00:00:00Z")).toMatch(/2025/);
  });
});

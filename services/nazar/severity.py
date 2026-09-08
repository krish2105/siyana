"""Severity triage prior from defect class and relative area. Not an airworthiness determination:
the certifying engineer always makes the final call."""
from __future__ import annotations

BASE = {"crack": 3, "corrosion": 2, "dent": 1, "delamination": 1, "missing-fastener": 2, "anomaly": 2}
LARGE_AREA_FRACTION = 0.05

ATA_HINT: dict[str, str | None] = {
    "crack": "5300",
    "corrosion": "5300",
    "dent": "5300",
    "delamination": "5700",
    "missing-fastener": "5300",
    "anomaly": None,
}


def severity(defect_type: str, bbox: tuple[float, float, float, float], image_size: tuple[int, int]) -> str:
    x1, y1, x2, y2 = bbox
    w, h = image_size
    area_frac = max(0.0, (x2 - x1)) * max(0.0, (y2 - y1)) / max(1.0, float(w * h))
    base = BASE.get(defect_type, 1)
    bump = 1 if area_frac > LARGE_AREA_FRACTION else 0
    return f"S{min(base + bump, 4)}"

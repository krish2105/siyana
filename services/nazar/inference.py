"""NAZAR inference: supervised detector for known defect classes plus the PatchCore anomaly head
for everything the detector was never taught. Anomaly regions that overlap a detection are
suppressed; the rest surface as 'anomaly' findings for human review.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from services.common.config import settings
from services.nazar.patchcore import PatchCore
from services.nazar.severity import ATA_HINT, severity

DETECTOR_DIR = settings.models_dir / "rtdetr_defects"
ANOMALY_BANKS = sorted(settings.models_dir.glob("patchcore_*.pt"))


@dataclass
class Finding:
    defect_type: str
    bbox: tuple[float, float, float, float]
    confidence: float
    severity: str
    ata_hint: str | None
    head: str  # 'detector' | 'anomaly'


class Nazar:
    def __init__(self, detector_dir: Path = DETECTOR_DIR, anomaly_bank: Path | None = None, anomaly_margin: float = 1.25):
        self.detector = None
        self.detector_version = "detector/none"
        if (detector_dir / "meta.json").exists():
            from services.nazar.detector import RTDetrDetector

            self.detector = RTDetrDetector(detector_dir)
            self.detector_version = self.detector.model_version
        bank = anomaly_bank or (ANOMALY_BANKS[0] if ANOMALY_BANKS else None)
        self.anomaly = PatchCore.load(bank) if bank else None
        self.anomaly_version = f"{self.anomaly.model_version}@{bank.stem}" if self.anomaly else "anomaly/none"
        self.anomaly_margin = anomaly_margin
        self.model_version = f"{self.detector_version}; {self.anomaly_version}"

    def _patch_anomalies(self, img: Image.Image) -> list[tuple[tuple[float, float, float, float], float]]:
        if self.anomaly is None or self.anomaly.threshold is None:
            return []
        score, heat = self.anomaly.score(img)
        thr = self.anomaly.threshold * self.anomaly_margin
        lab, n = ndimage.label(heat >= thr)
        out = []
        for r in range(1, n + 1):
            ys, xs = np.where(lab == r)
            if len(xs) < 64:
                continue
            region_score = float(heat[lab == r].max())
            conf = float(min(0.99, region_score / (thr * 2.0)))
            out.append(((float(xs.min()), float(ys.min()), float(xs.max()) + 1, float(ys.max()) + 1), conf))
        return out

    @staticmethod
    def _iou(a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix, iy = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
        inter = ix * iy
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return inter / union if union > 0 else 0.0

    def predict(self, img: Image.Image) -> list[Finding]:
        findings: list[Finding] = []
        if self.detector is not None:
            for cls, box, conf in self.detector.detect(img):
                findings.append(Finding(cls, box, conf, severity(cls, box, img.size), ATA_HINT.get(cls), "detector"))
        for box, score in self._patch_anomalies(img):
            if any(self._iou(box, f.bbox) > 0.3 for f in findings):
                continue
            findings.append(Finding("anomaly", box, score, severity("anomaly", box, img.size), None, "anomaly"))
        return findings

    @staticmethod
    def to_json(findings: list[Finding]) -> list[dict]:
        return [asdict(f) for f in findings]


if __name__ == "__main__":
    import sys

    n = Nazar()
    for p in sys.argv[1:]:
        print(p, json.dumps(Nazar.to_json(n.predict(Image.open(p))), indent=1))

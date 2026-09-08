"""Fit PatchCore per MVTec category on train/good only, then score the test split.

Metrics: image-level AUROC (good vs defective) and pixel-level AUPRO (per-region overlap
integrated up to a 30% false-positive rate, the standard MVTec protocol) using the ground-truth
masks. Also records the score threshold at 5% image false-positive rate, which the inference
service uses to decide what goes to a human.

Run: .venv/bin/python -m services.nazar.eval [--categories metal_nut screw grid tile]
  -> data/models/patchcore_<category>.pt, data/metrics/nazar.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve

from services.common.config import settings
from services.nazar.patchcore import PatchCore

MVTEC_ROOT = settings.raw_dir / "mvtec"
METRICS_PATH = settings.metrics_dir / "nazar.json"


def aupro(heatmaps: list[np.ndarray], masks: list[np.ndarray], max_fpr: float = 0.3, steps: int = 40) -> float:
    """Per-region overlap curve vs false-positive rate on good pixels, integrated to max_fpr, normalised."""
    all_scores = np.concatenate([h.ravel() for h in heatmaps])
    thresholds = np.quantile(all_scores, np.linspace(0.5, 0.9999, steps))
    neg = np.concatenate([h[m == 0].ravel() for h, m in zip(heatmaps, masks, strict=True)])
    from scipy import ndimage

    regions = []
    for h, m in zip(heatmaps, masks, strict=True):
        lab, n = ndimage.label(m > 0)
        for r in range(1, n + 1):
            regions.append(h[lab == r])
    fprs, pros = [], []
    for t in thresholds:
        fpr = float((neg >= t).mean()) if len(neg) else 0.0
        pro = float(np.mean([(r >= t).mean() for r in regions])) if regions else 0.0
        fprs.append(fpr)
        pros.append(pro)
    fprs, pros = np.array(fprs)[::-1], np.array(pros)[::-1]
    keep = fprs <= max_fpr
    if keep.sum() < 2:
        return 0.0
    x, y = fprs[keep], pros[keep]
    order = np.argsort(x)
    return float(np.trapezoid(y[order], x[order]) / max_fpr)


def evaluate_category(cat: str, coreset_ratio: float = 0.1) -> dict:
    root = MVTEC_ROOT / cat
    train = sorted((root / "train" / "good").glob("*.png"))
    pc = PatchCore(coreset_ratio=coreset_ratio)
    pc.fit(train)
    scores, labels, heats, masks = [], [], [], []
    for defect_dir in sorted((root / "test").iterdir()):
        for img_path in sorted(defect_dir.glob("*.png")):
            img = Image.open(img_path).convert("RGB")
            s, heat = pc.score(img)
            scores.append(s)
            is_defect = defect_dir.name != "good"
            labels.append(int(is_defect))
            if is_defect:
                mask_path = root / "ground_truth" / defect_dir.name / f"{img_path.stem}_mask.png"
                if mask_path.exists():
                    m = np.array(Image.open(mask_path).convert("L").resize((img.width, img.height))) > 0
                    heats.append(heat)
                    masks.append(m.astype(np.uint8))
    y, sc = np.array(labels), np.array(scores)
    auroc = float(roc_auc_score(y, sc))
    fpr, tpr, thr = roc_curve(y, sc)
    i = int(np.searchsorted(fpr, 0.05, side="right") - 1)
    thr_at_5 = float(thr[max(0, i)])
    fnr_at_5 = float(1.0 - tpr[max(0, i)])
    pc.threshold = thr_at_5
    pc.save(settings.models_dir / f"patchcore_{cat}.pt")
    return {
        "category": cat,
        "n_train_good": len(train),
        "n_test": int(len(y)),
        "n_test_defective": int(y.sum()),
        "image_auroc": auroc,
        "pixel_aupro": aupro(heats, masks) if heats else None,
        "threshold_at_5pct_fpr": thr_at_5,
        "fnr_at_5pct_fpr": fnr_at_5,
    }


def main(categories: list[str]) -> dict:
    results = {"model_version": PatchCore().model_version, "categories": {}}
    for cat in categories:
        r = evaluate_category(cat)
        results["categories"][cat] = r
        print(f"[nazar] {cat:10s} AUROC {r['image_auroc']:.3f}  AUPRO {r['pixel_aupro'] if r['pixel_aupro'] is None else round(r['pixel_aupro'],3)}  FNR@5%FPR {r['fnr_at_5pct_fpr']:.3f}", flush=True)
    vals = [c["image_auroc"] for c in results["categories"].values()]
    pros = [c["pixel_aupro"] for c in results["categories"].values() if c["pixel_aupro"] is not None]
    results["mean_image_auroc"] = float(np.mean(vals))
    results["mean_pixel_aupro"] = float(np.mean(pros)) if pros else None
    existing = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    existing["patchcore"] = results
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(existing, indent=2))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", nargs="+", default=["metal_nut", "screw", "grid", "tile"])
    main(ap.parse_args().categories)

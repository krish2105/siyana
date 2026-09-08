"""Derive a COCO-format bounding-box dataset for the NAZAR detector from MVTec ground-truth masks.

Aircraft skin defect imagery with boxes is scarce and mostly proprietary, so the detector is
trained on the MVTec categories whose defects map onto the SIYANA classes. This is a documented
stand-in: the detector architecture and training loop are what an operator reuses on their own
borescope and skin imagery; the weights are not.

Class map (MVTec defect -> SIYANA class):
  crack, scratch, broken_teeth           -> crack
  bent, bent_lead, poke                  -> dent
  color, contamination, rough, oil, glue -> corrosion
  thread, cut, hole, squeeze, gray_stroke-> delamination
  missing, manipulated_front, flip       -> missing-fastener

Run: .venv/bin/python -m ingest.nazar_boxes  -> data/processed/nazar_boxes/{train,val}.json + images/
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from services.common.config import settings

MVTEC_ROOT = settings.raw_dir / "mvtec"
OUT = settings.processed_dir / "nazar_boxes"
CLASSES = ["crack", "corrosion", "dent", "delamination", "missing-fastener"]
DEFECT_MAP = {
    "crack": "crack", "scratch": "crack", "broken_teeth": "crack",
    "bent": "dent", "bent_lead": "dent", "poke": "dent",
    "color": "corrosion", "contamination": "corrosion", "rough": "corrosion", "oil": "corrosion", "glue": "corrosion", "glue_strip": "corrosion", "metal_contamination": "corrosion",
    "thread": "delamination", "cut": "delamination", "hole": "delamination", "squeeze": "delamination", "gray_stroke": "delamination", "fabric_border": "delamination",
    "missing": "missing-fastener", "manipulated_front": "missing-fastener", "flip": "missing-fastener", "misplaced": "missing-fastener",
}
MIN_BOX = 6


def boxes_from_mask(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    lab, n = ndimage.label(mask > 0)
    out = []
    for r in range(1, n + 1):
        ys, xs = np.where(lab == r)
        x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        if x2 - x1 >= MIN_BOX and y2 - y1 >= MIN_BOX:
            out.append((x1, y1, x2 - x1, y2 - y1))
    return out


def build(categories: list[str] | None = None, val_frac: float = 0.25, seed: int = 7) -> dict:
    rng = random.Random(seed)
    cats = categories or sorted(p.name for p in MVTEC_ROOT.iterdir() if p.is_dir())
    images, annotations = [], []
    img_dir = OUT / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    ann_id = 1
    for cat in cats:
        test_dir = MVTEC_ROOT / cat / "test"
        for defect_dir in sorted(test_dir.iterdir()):
            if defect_dir.name == "good" or defect_dir.name not in DEFECT_MAP:
                continue
            cls = DEFECT_MAP[defect_dir.name]
            for img_path in sorted(defect_dir.glob("*.png")):
                mask_path = MVTEC_ROOT / cat / "ground_truth" / defect_dir.name / f"{img_path.stem}_mask.png"
                if not mask_path.exists():
                    continue
                img = Image.open(img_path)
                mask = np.array(Image.open(mask_path).convert("L").resize(img.size))
                bxs = boxes_from_mask(mask)
                if not bxs:
                    continue
                fname = f"{cat}_{defect_dir.name}_{img_path.name}"
                if not (img_dir / fname).exists():
                    shutil.copyfile(img_path, img_dir / fname)
                image_id = len(images) + 1
                images.append({"id": image_id, "file_name": fname, "width": img.width, "height": img.height, "category_source": cat, "defect_source": defect_dir.name})
                for b in bxs:
                    annotations.append({"id": ann_id, "image_id": image_id, "category_id": CLASSES.index(cls), "bbox": list(b), "area": b[2] * b[3], "iscrowd": 0})
                    ann_id += 1
    ids = [im["id"] for im in images]
    rng.shuffle(ids)
    n_val = int(len(ids) * val_frac)
    val_ids = set(ids[:n_val])
    cats_json = [{"id": i, "name": c} for i, c in enumerate(CLASSES)]
    for split, keep in (("train", lambda i: i not in val_ids), ("val", lambda i: i in val_ids)):
        ims = [im for im in images if keep(im["id"])]
        anns = [a for a in annotations if keep(a["image_id"])]
        (OUT / f"{split}.json").write_text(json.dumps({"images": ims, "annotations": anns, "categories": cats_json}, indent=1))
    summary = {"images": len(images), "annotations": len(annotations), "train": len(ids) - n_val, "val": n_val, "classes": CLASSES}
    print(f"[nazar_boxes] {summary}")
    return summary


if __name__ == "__main__":
    build()

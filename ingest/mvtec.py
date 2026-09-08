"""MVTec AD via the Hugging Face mirror Voxel51/mvtec-ad (CC BY-NC-SA 4.0, research use only).

The mirror is a FiftyOne export: samples.json lists every image with category, defect label,
split and (for defective test images) a mask path. We download a subset of categories and lay
them out in the original MVTec folder structure so PatchCore code reads a familiar tree:

    data/raw/mvtec/<category>/train/good/*.png
    data/raw/mvtec/<category>/test/<defect>/*.png
    data/raw/mvtec/<category>/ground_truth/<defect>/*_mask.png

Run: .venv/bin/python -m ingest.mvtec --categories metal_nut screw grid tile
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

from ingest.common import data_path, record_run
from services.common.db import SessionLocal, db_reachable

REPO = "Voxel51/mvtec-ad"
DEFAULT_CATEGORIES = ("metal_nut", "screw", "grid", "tile")


def select_samples(samples: list[dict], categories: tuple[str, ...]) -> list[dict]:
    return [s for s in samples if s.get("category", {}).get("label") in categories]


def layout_path(sample: dict, root: Path) -> tuple[Path, Path | None]:
    cat = sample["category"]["label"]
    defect = sample["defect"]["label"]
    split = sample["split"]
    name = Path(sample["filepath"]).name
    img = root / cat / split / defect / name
    mask = None
    if sample.get("defect_mask"):
        mask = root / cat / "ground_truth" / defect / (Path(name).stem + "_mask.png")
    return img, mask


def pull(categories: tuple[str, ...] = DEFAULT_CATEGORIES) -> int:
    root = data_path("raw", "mvtec", "x").parent
    samples_path = Path(hf_hub_download(REPO, "samples.json", repo_type="dataset"))
    samples = select_samples(json.load(samples_path.open())["samples"], categories)
    patterns = [s["filepath"] for s in samples] + [s["defect_mask"]["mask_path"] for s in samples if s.get("defect_mask")]
    snap = Path(snapshot_download(REPO, repo_type="dataset", allow_patterns=patterns))
    copied = 0
    for s in samples:
        img, mask = layout_path(s, root)
        img.parent.mkdir(parents=True, exist_ok=True)
        if not img.exists():
            shutil.copyfile(snap / s["filepath"], img)
        if mask is not None:
            mask.parent.mkdir(parents=True, exist_ok=True)
            if not mask.exists():
                shutil.copyfile(snap / s["defect_mask"]["mask_path"], mask)
        copied += 1
    if db_reachable():
        with SessionLocal() as db:
            record_run(db, source="mvtec", source_url=f"https://huggingface.co/datasets/{REPO}", payload=samples_path.read_bytes(), rows=copied, detail=",".join(categories))
            db.commit()
    print(f"[mvtec] {copied} images across {categories} -> {root}", flush=True)
    return copied


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", nargs="+", default=list(DEFAULT_CATEGORIES))
    pull(tuple(ap.parse_args().categories))

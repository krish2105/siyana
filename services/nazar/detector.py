"""Supervised defect detector: RT-DETR (PekingU/rtdetr_r50vd, COCO-pretrained) fine-tuned on the
COCO-format defect boxes from ingest/nazar_boxes.py.

Run: .venv/bin/python -m services.nazar.detector --epochs 12   -> data/models/rtdetr_defects/
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

from services.common.config import settings
from services.nazar.severity import ATA_HINT

DETECTOR_VERSION = "nazar-rtdetr/r50vd-ft-mvtec-boxes/2026-09"
PRETRAINED = "PekingU/rtdetr_r50vd"
BOXES = settings.processed_dir / "nazar_boxes"
OUT_DIR = settings.models_dir / "rtdetr_defects"
CLASSES = ["crack", "corrosion", "dent", "delamination", "missing-fastener"]


def _device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CocoBoxes(Dataset):
    def __init__(self, split: str, processor: RTDetrImageProcessor):
        data = json.loads((BOXES / f"{split}.json").read_text())
        self.images = data["images"]
        self.by_image: dict[int, list[dict]] = {}
        for a in data["annotations"]:
            self.by_image.setdefault(a["image_id"], []).append(a)
        self.processor = processor

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, i: int):
        im = self.images[i]
        img = Image.open(BOXES / "images" / im["file_name"]).convert("RGB")
        anns = self.by_image.get(im["id"], [])
        target = {"image_id": im["id"], "annotations": [{"bbox": a["bbox"], "category_id": a["category_id"], "area": a["area"], "iscrowd": 0} for a in anns]}
        enc = self.processor(images=img, annotations=target, return_tensors="pt")
        return {"pixel_values": enc["pixel_values"][0], "labels": enc["labels"][0]}


def collate(batch):
    return {"pixel_values": torch.stack([b["pixel_values"] for b in batch]), "labels": [b["labels"] for b in batch]}


def fine_tune(epochs: int = 12, lr: float = 1e-4, batch_size: int = 4) -> dict:
    device = _device()
    processor = RTDetrImageProcessor.from_pretrained(PRETRAINED, size={"height": 480, "width": 480})
    model = RTDetrForObjectDetection.from_pretrained(
        PRETRAINED,
        num_labels=len(CLASSES),
        id2label={i: c for i, c in enumerate(CLASSES)},
        label2id={c: i for i, c in enumerate(CLASSES)},
        ignore_mismatched_sizes=True,
    ).to(device)
    train = CocoBoxes("train", processor)
    loader = DataLoader(train, batch_size=batch_size, shuffle=True, collate_fn=collate, num_workers=0)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, epochs * len(loader)))
    t0 = time.time()
    history = []
    model.train()
    for ep in range(epochs):
        total = 0.0
        for batch in loader:
            pv = batch["pixel_values"].to(device)
            labels = [{k: v.to(device) for k, v in lab.items()} for lab in batch["labels"]]
            out = model(pixel_values=pv, labels=labels)
            opt.zero_grad()
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)
            opt.step()
            sched.step()
            total += float(out.loss.item())
        history.append({"epoch": ep + 1, "loss": total / max(1, len(loader))})
        print(f"[rtdetr] epoch {ep + 1}/{epochs} loss {history[-1]['loss']:.3f}", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT_DIR)
    processor.save_pretrained(OUT_DIR)
    meta = {"version": DETECTOR_VERSION, "pretrained": PRETRAINED, "classes": CLASSES, "epochs": epochs, "train_images": len(train), "fit_seconds": time.time() - t0, "history": history}
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


class RTDetrDetector:
    def __init__(self, path: Path = OUT_DIR, threshold: float = 0.4):
        self.device = _device()
        self.processor = RTDetrImageProcessor.from_pretrained(path)
        self.model = RTDetrForObjectDetection.from_pretrained(path).to(self.device).eval()
        self.threshold = threshold
        self.model_version = json.loads((path / "meta.json").read_text())["version"]

    @torch.no_grad()
    def detect(self, img: Image.Image, threshold: float | None = None) -> list[tuple[str, tuple[float, float, float, float], float]]:
        enc = self.processor(images=img.convert("RGB"), return_tensors="pt").to(self.device)
        out = self.model(**enc)
        res = self.processor.post_process_object_detection(out, threshold=threshold or self.threshold, target_sizes=torch.tensor([[img.height, img.width]]))[0]
        dets = []
        for score, label, box in zip(res["scores"], res["labels"], res["boxes"], strict=True):
            x1, y1, x2, y2 = [float(v) for v in box.tolist()]
            dets.append((self.model.config.id2label[int(label)], (x1, y1, x2, y2), float(score)))
        return dets


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--lr", type=float, default=1e-4)
    a = ap.parse_args()
    m = fine_tune(epochs=a.epochs, lr=a.lr)
    print(json.dumps({k: v for k, v in m.items() if k != "history"}, indent=2))

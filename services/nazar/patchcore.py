"""PatchCore anomaly detection: a memory bank of mid-level CNN patch features from serviceable
images only. Anything far from that manifold is novel and goes to a human for review.

Reference: Roth et al., "Towards Total Recall in Industrial Anomaly Detection" (CVPR 2022).
Backbone: torchvision wide_resnet50_2 (ImageNet weights), layers 2 and 3, 3x3 local aggregation,
random-projection greedy coreset subsampling.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import Wide_ResNet50_2_Weights, wide_resnet50_2

PATCHCORE_VERSION = "nazar-patchcore/wrn50-l2l3-coreset0.1/2026-09"
IMAGE_SIZE = 224


def _device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class _Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        net = wide_resnet50_2(weights=Wide_ResNet50_2_Weights.IMAGENET1K_V1)
        self.stem = nn.Sequential(net.conv1, net.bn1, net.relu, net.maxpool)
        self.layer1, self.layer2, self.layer3 = net.layer1, net.layer2, net.layer3
        self.eval()
        for p in self.parameters():
            p.requires_grad_(False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.layer1(x)
        f2 = self.layer2(x)
        f3 = self.layer3(f2)
        f3 = F.interpolate(f3, size=f2.shape[-2:], mode="bilinear", align_corners=False)
        f = torch.cat([f2, f3], dim=1)
        f = F.avg_pool2d(f, kernel_size=3, stride=1, padding=1)  # local neighbourhood aggregation
        return f  # (B, 1536, 28, 28)


class PatchCore:
    def __init__(self, coreset_ratio: float = 0.1, seed: int = 7):
        self.device = _device()
        self.backbone = _Backbone().to(self.device)
        self.coreset_ratio = coreset_ratio
        self.seed = seed
        self.bank: torch.Tensor | None = None
        self.feat_hw: tuple[int, int] = (28, 28)
        self.threshold: float | None = None
        self.model_version = PATCHCORE_VERSION
        self.tf = transforms.Compose(
            [
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    @torch.no_grad()
    def _features(self, imgs: list[Image.Image]) -> torch.Tensor:
        x = torch.stack([self.tf(im.convert("RGB")) for im in imgs]).to(self.device)
        f = self.backbone(x)
        b, c, h, w = f.shape
        self.feat_hw = (h, w)
        return f.permute(0, 2, 3, 1).reshape(b, h * w, c)

    @torch.no_grad()
    def fit(self, image_paths: list[Path], batch: int = 16) -> None:
        feats = []
        for i in range(0, len(image_paths), batch):
            imgs = [Image.open(p) for p in image_paths[i : i + batch]]
            feats.append(self._features(imgs).reshape(-1, 1536).cpu())
        all_feats = torch.cat(feats)
        self.bank = self._coreset(all_feats, self.coreset_ratio).to(self.device)

    def _coreset(self, feats: torch.Tensor, ratio: float) -> torch.Tensor:
        """Greedy k-center on a random projection (Johnson-Lindenstrauss) for speed."""
        n = feats.shape[0]
        k = max(1, int(n * ratio))
        g = torch.Generator().manual_seed(self.seed)
        proj = torch.randn(feats.shape[1], 128, generator=g)
        z = feats @ proj
        selected = [int(torch.randint(n, (1,), generator=g))]
        min_d = torch.cdist(z, z[selected[-1]].unsqueeze(0)).squeeze(1)
        for _ in range(k - 1):
            idx = int(torch.argmax(min_d))
            selected.append(idx)
            d = torch.cdist(z, z[idx].unsqueeze(0)).squeeze(1)
            min_d = torch.minimum(min_d, d)
        return feats[selected]

    @torch.no_grad()
    def score(self, img: Image.Image) -> tuple[float, np.ndarray]:
        """Returns (image anomaly score, HxW patch heatmap upsampled to the input size)."""
        if self.bank is None:
            raise RuntimeError("PatchCore not fitted: call fit() or load()")
        f = self._features([img])[0]  # (hw, c)
        d = torch.cdist(f, self.bank)  # (hw, bank)
        nn_dist = d.min(dim=1).values  # (hw,)
        h, w = self.feat_hw
        patch_map = nn_dist.reshape(1, 1, h, w)
        up = F.interpolate(patch_map, size=(img.height, img.width), mode="bilinear", align_corners=False)[0, 0]
        heat = up.cpu().numpy()
        return float(nn_dist.max().item()), heat

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"bank": self.bank.cpu(), "feat_hw": self.feat_hw, "threshold": self.threshold, "version": self.model_version}, path)

    @classmethod
    def load(cls, path: Path) -> "PatchCore":
        obj = cls()
        state = torch.load(path, map_location="cpu")
        obj.bank = state["bank"].to(obj.device)
        obj.feat_hw = tuple(state["feat_hw"])
        obj.threshold = state.get("threshold")
        return obj

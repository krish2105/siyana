"""Fetch large model artefacts that are not in git.

Trained weights (ATA classifier, PatchCore banks, RT-DETR) are published as GitHub release
assets. On a fresh deploy the first component that needs one downloads it into data/models.
Set SIYANA_ARTEFACT_BASE to another URL prefix to host them elsewhere.
"""
from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from services.common.config import settings

ARTEFACT_BASE = os.environ.get("SIYANA_ARTEFACT_BASE", "https://github.com/krish2105/siyana/releases/download/models-v1")
ARCHIVES = {"rtdetr_defects": "rtdetr_defects.tar.gz"}


def ensure_artefact(name: str) -> Path | None:
    """Return the local path for `name` (a file in data/models or the rtdetr_defects directory),
    downloading it from the release if missing. Returns None if it cannot be fetched."""
    target = settings.models_dir / name
    if target.exists():
        return target
    if os.environ.get("SIYANA_OFFLINE") == "1":
        return None
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    remote = ARCHIVES.get(name, name)
    url = f"{ARTEFACT_BASE}/{remote}"
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=settings.models_dir) as tmp:
            with urllib.request.urlopen(url, timeout=600) as r:  # noqa: S310 (fixed https base)
                shutil.copyfileobj(r, tmp)
            tmp_path = Path(tmp.name)
        if remote.endswith(".tar.gz"):
            with tarfile.open(tmp_path) as tar:
                tar.extractall(settings.models_dir, filter="data")
            tmp_path.unlink()
        else:
            tmp_path.replace(target)
        print(f"[artefacts] fetched {name} from {url}", flush=True)
        return target if target.exists() else None
    except Exception as e:  # network or 404: the caller degrades gracefully
        print(f"[artefacts] could not fetch {name}: {e}", flush=True)
        return None

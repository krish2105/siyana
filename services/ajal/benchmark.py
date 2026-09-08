"""FD001 benchmark: LightGBM vs GRU vs last-cycle-constant on RMSE and the NASA score.

Run: .venv/bin/python -m services.ajal.benchmark   -> data/metrics/ajal_rul.json, data/models/rul_lgbm.txt
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from ingest.cmapss import load_fd
from services.ajal.features import RUL_CAP, last_cycle_rows
from services.ajal.gru_baseline import GRU_VERSION
from services.ajal.rul import MODEL_VERSION, last_cycle_constant_baseline, nasa_score, prepare, rmse, save, train_lgbm
from services.common.config import settings

METRICS_PATH = settings.metrics_dir / "ajal_rul.json"


def train_gru_subprocess(fd: str, epochs: int) -> np.ndarray:
    """torch and LightGBM ship separate OpenMP runtimes; in one process they deadlock on macOS."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "gru.npy"
        subprocess.run(
            [sys.executable, "-m", "services.ajal.gru_baseline", "--fd", fd, "--epochs", str(epochs), "--out", str(out)],
            check=True,
        )
        return np.load(out)


def run_benchmark(fd: str = "FD001", *, gru_epochs: int = 15) -> dict:
    train_df, test_df, rul = load_fd(fd)
    y_true = np.minimum(rul.to_numpy(dtype=float), RUL_CAP)
    ftr, fte, cols, y = prepare(train_df, test_df)

    t0 = time.time()
    model = train_lgbm(ftr[cols], y)
    lgbm_fit_s = time.time() - t0
    last = last_cycle_rows(fte)
    pred_lgbm = np.clip(model.predict(last[cols]), 0, RUL_CAP)

    pred_base = last_cycle_constant_baseline(train_df, len(y_true))

    t0 = time.time()
    pred_gru = train_gru_subprocess(fd, gru_epochs)
    gru_fit_s = time.time() - t0

    importances = sorted(zip(cols, model.feature_importances_.tolist(), strict=True), key=lambda kv: -kv[1])[:15]
    metrics = {
        "dataset": fd,
        "rul_cap": RUL_CAP,
        "n_train_units": int(train_df.unit.nunique()),
        "n_test_units": int(len(y_true)),
        "models": {
            "lgbm": {"version": MODEL_VERSION, "rmse": rmse(y_true, pred_lgbm), "nasa_score": nasa_score(y_true, pred_lgbm), "fit_seconds": lgbm_fit_s},
            "gru": {"version": GRU_VERSION, "rmse": rmse(y_true, pred_gru), "nasa_score": nasa_score(y_true, pred_gru), "fit_seconds": gru_fit_s},
            "last_cycle_constant": {"version": "baseline/train-mean-capped-rul", "rmse": rmse(y_true, pred_base), "nasa_score": nasa_score(y_true, pred_base), "fit_seconds": 0.0},
        },
        "top_features": importances,
        "predictions": [
            {"unit": int(u), "true_rul": float(t), "lgbm": float(p), "gru": float(g), "baseline": float(b)}
            for u, t, p, g, b in zip(last["unit"], y_true, pred_lgbm, pred_gru, pred_base, strict=True)
        ],
    }
    save(model)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    m = run_benchmark()
    for name, r in m["models"].items():
        print(f"{name:22s} RMSE {r['rmse']:7.2f}   NASA {r['nasa_score']:10.1f}   fit {r['fit_seconds']:.1f}s")

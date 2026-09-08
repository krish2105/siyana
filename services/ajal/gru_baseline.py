"""A small GRU sequence model on the same windows, included so the LightGBM choice is shown, not asserted."""
from __future__ import annotations

import numpy as np
import pandas as pd

from services.ajal.features import ACTIVE_SENSORS, RUL_CAP

GRU_VERSION = "ajal-rul/gru-h64-seq30/2026-09"

# torch is imported lazily inside the functions below. On macOS, torch and LightGBM each ship
# their own libomp; importing torch before LightGBM fits segfaults the process. The benchmark
# therefore fits LightGBM first and only then trains the GRU.


def build_model(n_features: int, hidden: int = 64):
    import torch
    from torch import nn

    class GRUModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(n_features, hidden, num_layers=2, batch_first=True, dropout=0.1)
            self.head = nn.Sequential(nn.Linear(hidden, 32), nn.ReLU(), nn.Linear(32, 1))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out, _ = self.gru(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    return GRUModel()


def _scaler(train_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    vals = train_df[ACTIVE_SENSORS].to_numpy(dtype=np.float32)
    mu, sd = vals.mean(0), vals.std(0) + 1e-6
    return mu, sd


def make_sequences(df: pd.DataFrame, mu: np.ndarray, sd: np.ndarray, seq: int = 30, cap: int = RUL_CAP, last_only: bool = False):
    X, y = [], []
    for _, g in df.groupby("unit", sort=True):
        g = g.sort_values("cycle")
        vals = (g[ACTIVE_SENSORS].to_numpy(dtype=np.float32) - mu) / sd
        n = len(vals)
        pad = np.repeat(vals[:1], max(0, seq - n), axis=0)
        vals = np.vstack([pad, vals]) if len(pad) else vals
        rul = np.minimum(g["cycle"].max() - g["cycle"].to_numpy(), cap).astype(np.float32)
        rul = np.concatenate([np.full(len(pad), rul[0], dtype=np.float32), rul]) if len(pad) else rul
        rng = [len(vals) - 1] if last_only else range(seq - 1, len(vals))
        for i in rng:
            X.append(vals[i - seq + 1 : i + 1])
            y.append(rul[i])
    return np.stack(X), np.asarray(y, dtype=np.float32)


def train_gru(train_df: pd.DataFrame, test_df: pd.DataFrame, *, seq: int = 30, epochs: int = 15, seed: int = 7) -> np.ndarray:
    import torch
    from torch import nn

    torch.manual_seed(seed)
    mu, sd = _scaler(train_df)
    Xtr, ytr = make_sequences(train_df, mu, sd, seq)
    Xte, _ = make_sequences(test_df, mu, sd, seq, last_only=True)
    model = build_model(len(ACTIVE_SENSORS))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.L1Loss()
    Xt, yt = torch.from_numpy(Xtr), torch.from_numpy(ytr)
    n = len(Xt)
    for _ in range(epochs):
        perm = torch.randperm(n)
        model.train()
        for i in range(0, n, 256):
            idx = perm[i : i + 256]
            opt.zero_grad()
            loss = loss_fn(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(Xte)).clamp(0, RUL_CAP).numpy()


def main() -> None:
    """Subprocess entry point used by the benchmark so torch never shares a process with LightGBM."""
    import argparse

    from ingest.cmapss import load_fd

    ap = argparse.ArgumentParser()
    ap.add_argument("--fd", default="FD001")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    train_df, test_df, _ = load_fd(a.fd)
    preds = train_gru(train_df, test_df, epochs=a.epochs)
    np.save(a.out, preds)
    print(f"[gru] {len(preds)} predictions -> {a.out}")


if __name__ == "__main__":
    main()

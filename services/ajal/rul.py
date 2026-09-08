"""LightGBM RUL model plus the two metrics that matter: RMSE and the NASA asymmetric score."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import lightgbm as lgb

# lightgbm is imported inside the functions that need it. The API gateway imports this module for
# paths and metrics but must never load LightGBM's OpenMP runtime next to torch's (see benchmark.py).

from services.ajal.features import RUL_CAP, feature_columns, make_labels, window_features
from services.common.config import settings

MODEL_VERSION = "ajal-rul/lgbm-l1-w30-cap125/2026-09"
MODEL_PATH = settings.models_dir / "rul_lgbm.txt"


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_pred) - np.asarray(y_true)) ** 2)))


def nasa_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """PHM08 asymmetric score. d = predicted - actual. Late predictions (d > 0) are penalised
    with exp(d/10) - 1, early ones with exp(-d/13) - 1, so optimism costs more than caution."""
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return float(np.sum(np.where(d < 0, np.exp(-d / 13.0) - 1.0, np.exp(d / 10.0) - 1.0)))


def train_lgbm(X: pd.DataFrame, y: np.ndarray, *, seed: int = 7) -> "lgb.LGBMRegressor":
    import lightgbm as lgb

    model = lgb.LGBMRegressor(
        n_estimators=1200,
        learning_rate=0.03,
        num_leaves=63,
        min_child_samples=40,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        objective="regression_l1",
        random_state=seed,
        verbose=-1,
    )
    model.fit(X, y)
    return model


def prepare(train_df: pd.DataFrame, test_df: pd.DataFrame, window: int = 30):
    ftr = window_features(train_df, window)
    fte = window_features(test_df, window)
    cols = feature_columns(ftr)
    # window_features sorts by unit then cycle, so labels are computed on the same ordering.
    ordered = train_df.sort_values(["unit", "cycle"]).reset_index(drop=True)
    y = make_labels(ordered)
    return ftr, fte, cols, y


def last_cycle_constant_baseline(train_df: pd.DataFrame, n_test_units: int, cap: int = RUL_CAP) -> np.ndarray:
    """Predict the training-set mean capped RUL for every test engine. The 'do nothing clever' baseline."""
    mean_rul = float(np.mean(make_labels(train_df, cap)))
    return np.full(n_test_units, mean_rul, dtype=float)


def save(model: "lgb.LGBMRegressor", path: Path = MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(path))
    return path


def load(path: Path = MODEL_PATH) -> "lgb.Booster":
    import lightgbm as lgb

    # num_threads=1: the gateway also loads torch (NAZAR); a second OpenMP runtime in the same
    # process segfaults multi-threaded LightGBM on macOS. Single-thread prediction is instant anyway.
    return lgb.Booster(model_file=str(path), params={"num_threads": 1})

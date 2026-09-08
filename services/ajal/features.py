"""Feature engineering for C-MAPSS remaining-useful-life prediction.

Degradation shows up as level drift, variance change and trend, so each sensor gets a rolling
mean, rolling std and window slope. RUL labels are capped: an engine 300 cycles from failure and
one 200 cycles away are both simply healthy, and letting the model chase the far tail wastes
capacity on the region nobody acts on.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSOR_COLS = [f"s{i}" for i in range(1, 22)]
# Sensors that are constant in FD001/FD003 carry no signal; dropping them keeps LightGBM honest.
CONSTANT_SENSORS = {"s1", "s5", "s6", "s10", "s16", "s18", "s19"}
ACTIVE_SENSORS = [c for c in SENSOR_COLS if c not in CONSTANT_SENSORS]
RUL_CAP = 125


def window_features(df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """One feature row per (unit, cycle): raw value, rolling mean, rolling std, window slope."""
    out = []
    for unit, g in df.groupby("unit", sort=True):
        g = g.sort_values("cycle")
        feats = {"unit": g["unit"].to_numpy(), "cycle": g["cycle"].to_numpy()}
        for c in ACTIVE_SENSORS:
            s = g[c]
            r = s.rolling(window, min_periods=5)
            feats[c] = s.to_numpy()
            feats[f"{c}_mean"] = r.mean().to_numpy()
            feats[f"{c}_std"] = r.std().to_numpy()
            feats[f"{c}_slope"] = ((s - s.shift(window)) / window).to_numpy()
        out.append(pd.DataFrame(feats))
    result = pd.concat(out, ignore_index=True)
    return result


def make_labels(df: pd.DataFrame, cap: int = RUL_CAP) -> np.ndarray:
    last = df.groupby("unit")["cycle"].transform("max")
    return np.minimum(last - df["cycle"], cap).to_numpy(dtype=np.float32)


def feature_columns(feats: pd.DataFrame) -> list[str]:
    return [c for c in feats.columns if c not in ("unit", "cycle")]


def last_cycle_rows(feats: pd.DataFrame) -> pd.DataFrame:
    """The final observed cycle per test unit, the row the C-MAPSS RUL file scores."""
    idx = feats.groupby("unit")["cycle"].idxmax()
    return feats.loc[idx].sort_values("unit").reset_index(drop=True)

import math

import numpy as np
import pandas as pd

from services.ajal.features import ACTIVE_SENSORS, SENSOR_COLS, make_labels, window_features
from services.ajal.rul import nasa_score, rmse


def _frame(units=2, cycles=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(1, units + 1):
        for c in range(1, cycles + 1):
            rows.append({"unit": u, "cycle": c, "op1": 0, "op2": 0, "op3": 100, **{s: rng.normal() + c * 0.01 for s in SENSOR_COLS}})
    return pd.DataFrame(rows)


def test_nasa_score_is_asymmetric():
    assert math.isclose(nasa_score([10], [20]), math.exp(1) - 1)
    late = nasa_score([100], [110])
    early = nasa_score([100], [90])
    assert late > early


def test_rmse():
    assert math.isclose(rmse([0, 0], [3, 4]), math.sqrt(12.5))


def test_make_labels_caps_at_125():
    df = _frame(units=1, cycles=300)
    y = make_labels(df)
    assert y.max() == 125 and y.min() == 0


def test_window_features_columns():
    feats = window_features(_frame(), window=10)
    assert "s2_slope" in feats.columns and "s2_mean" in feats.columns and "s2_std" in feats.columns
    assert "s1" not in feats.columns  # constant sensor dropped
    assert len(feats) == 80
    assert set(feats.unit.unique()) == {1, 2}
    assert len([c for c in feats.columns if c not in ("unit", "cycle")]) == 4 * len(ACTIVE_SENSORS)

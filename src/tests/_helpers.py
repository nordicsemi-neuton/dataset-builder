"""Shared test helpers: put src/ on sys.path and build synthetic frames/profiles.

Importing this module first (each test does `import _helpers as H`) makes `import data_builder` work
under `python3 -m unittest discover -s src/tests`.
"""
import os
import sys

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

from data_builder.profile import DatasetProfile  # noqa: E402

BASE_PROFILE = {
    "dataset_name": "test",
    "label_column": "class",
    "sensor_columns": ["acc_x", "acc_y", "acc_z"],
    "separator": "comma",
    "task_type": "multiclass_classification",
    "target_technology": "neuton",
    "session_column": None,
    "time_column": None,
    "class_encoding": {"map": {"idle": 0, "left": 1, "right": 2},
                       "continuous_classes": [0], "gesture_classes": [1, 2]},
    "window": {"candidates": [20], "shift": 20, "frequency_domain_features": False},
}


def prof(**over):
    raw = {**BASE_PROFILE, **over}
    return DatasetProfile.from_dict(raw)


def block(label, n, base=0.0, sensors=("acc_x", "acc_y", "acc_z"), peak_at=None, rng=None):
    """A contiguous block of n rows for one class. If peak_at given, acc_z gets a bump there (gesture)."""
    rng = rng or np.random.RandomState(0)
    data = {s: base + 0.01 * rng.randn(n) for s in sensors}
    if peak_at is not None:
        data[sensors[-1]] = data[sensors[-1]].copy()
        lo, hi = max(0, peak_at - 2), min(n, peak_at + 3)
        data[sensors[-1]][lo:hi] += 5.0
    df = pd.DataFrame(data)
    df["class"] = label
    return df


def concat(*frames):
    return pd.concat(frames, ignore_index=True)


def as_strings(df):
    """Mimic a freshly-read raw frame (all columns object strings)."""
    return df.astype(str)

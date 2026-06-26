"""datatype — recommend the platform input data type from the data + target technology.

Axon (LiteRT) accepts ONLY FLOAT32, so an Axon target forces FLOAT32 regardless of value ranges
(databuilder-001 [gate]). Otherwise decide from value CONTENT (are all values integral?), not pandas
dtype, so a float-typed-but-integral column is not pushed to FLOAT32 unnecessarily.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PREPROC = "wiki/architecture/platform-preprocessing-options.md"

INT8_MIN, INT8_MAX = -128, 127
INT16_MIN, INT16_MAX = -32768, 32767


def recommend_dtype(df: pd.DataFrame, feature_cols, target_technology: str = "neuton") -> dict:
    """Return {'dtype': 'INT8'|'INT16'|'FLOAT32', 'reason': str, 'rule_ref': str}."""
    if target_technology == "axon":
        return {"dtype": "FLOAT32",
                "reason": "Axon (LiteRT) accepts only FLOAT32, regardless of value ranges.",
                "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}

    any_float = False
    vmin, vmax = np.inf, -np.inf
    for col in feature_cols:
        if col not in df.columns:
            continue
        arr = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=np.float64)
        arr = arr[~np.isnan(arr)]
        if arr.size == 0:
            continue
        if not np.all(np.equal(np.mod(arr, 1), 0)):
            any_float = True
        vmin = min(vmin, float(arr.min()))
        vmax = max(vmax, float(arr.max()))

    if any_float:
        return {"dtype": "FLOAT32",
                "reason": "At least one value is fractional (a float), so the whole dataset is FLOAT32.",
                "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}
    if vmin == np.inf:  # no numeric values seen
        return {"dtype": "FLOAT32", "reason": "No numeric feature values found; defaulting to FLOAT32.",
                "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}
    if INT8_MIN <= vmin and vmax <= INT8_MAX:
        return {"dtype": "INT8", "reason": f"All values are integers within [{INT8_MIN},{INT8_MAX}].",
                "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}
    if INT16_MIN <= vmin and vmax <= INT16_MAX:
        return {"dtype": "INT16", "reason": f"All values are integers within [{INT16_MIN},{INT16_MAX}].",
                "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}
    return {"dtype": "FLOAT32", "reason": "Integer values exceed the INT16 range.",
            "rule_ref": f"{PREPROC}#input-data-type-one-type-for-the-whole-dataset"}

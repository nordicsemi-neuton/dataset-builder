#!/usr/bin/env python3
"""
windowed_feature_distribution_comparison.py — compare per-window time-domain
features between training data (per class) and test data, to detect distribution
shift in feature space.

Usage:
    python3 windowed_feature_distribution_comparison.py \\
        --train train_centered.csv --train-label class \\
        --test imu_data.csv \\
        --window 100 --shift 33

Computes a representative subset of the platform's time-domain features per
window (mean, std, min, max, range, MAD, RMS, ABSMEAN, MCR, ZCR, PSOZ, PSOM,
PSOS, PSCR, CREST, RMDS, AMDF) on each axis. Then for each test window finds
the closest training class in feature space (Cohen's-d-like distance averaged
across features). Reports:
- Per-axis STD distribution (median, p95) per training class and overall test
- For each test window, which training class is closest
- Cohen's-d distance from test data overall to each training class signature
"""
import argparse
import numpy as np
import pandas as pd


def windowed_features(arr: np.ndarray, win=100, shift=33):
    """Return per-window features. arr shape (n, n_axes)."""
    n_axes = arr.shape[1]
    starts = np.arange(0, len(arr) - win + 1, shift)
    feats = []
    for s in starts:
        w = arr[s:s + win].astype(np.float64)
        row = []
        for ai in range(n_axes):
            x = w[:, ai]
            m = x.mean()
            s_ = x.std()
            row.extend([
                x.min(), x.max(), x.max() - x.min(),
                m, s_,
                np.sqrt((x ** 2).mean()),
                np.abs(x).mean(),
                np.abs(x - m).mean(),
                ((np.diff(np.sign(x - m))) != 0).sum() / len(x),  # MCR
                ((np.diff(np.sign(x))) != 0).sum() / len(x),       # ZCR
                (x > 0).mean(),
                (x > m).mean(),
                (x > (m + s_)).mean(),
                ((np.diff((x > (m + s_)).astype(int))) == 1).sum() / len(x),
                np.abs(x).max() / max(np.sqrt((x ** 2).mean()), 1.0),
                np.sqrt(np.mean(np.diff(x) ** 2)) if len(x) > 1 else 0,
                np.abs(np.diff(x)).mean() if len(x) > 1 else 0,
            ])
        feats.append(row)
    return np.array(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--train-label", default="class")
    ap.add_argument("--test", required=True)
    ap.add_argument("--axis-cols", nargs="+", default=None,
                    help="Names of the 6 axis columns (defaults: all numeric cols except label)")
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--shift", type=int, default=33)
    args = ap.parse_args()

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)

    if args.axis_cols is None:
        cols = [c for c in train.columns if c != args.train_label and pd.api.types.is_numeric_dtype(train[c])]
    else:
        cols = args.axis_cols

    if not all(c in test.columns for c in cols):
        # try a positional rename for test
        if len(test.columns) == len(cols):
            test = test.copy()
            test.columns = cols
        else:
            raise SystemExit(f"Test file columns {list(test.columns)} don't match training axes {cols}")

    print(f"axes: {cols}")
    print(f"train rows: {len(train):,}   test rows: {len(test):,}")
    print(f"window={args.window}  shift={args.shift}")
    print()

    classes = sorted(train[args.train_label].unique())
    train_features = {}
    for c in classes:
        seg = train[train[args.train_label] == c][cols].values
        if len(seg) >= args.window:
            train_features[c] = windowed_features(seg, args.window, args.shift)

    test_features = windowed_features(test[cols].values, args.window, args.shift)
    print(f"train windows per class: {[(c, len(train_features[c])) for c in classes]}")
    print(f"test windows: {len(test_features)}")
    print()

    # Per-axis STD distribution comparison (just one indicative slice)
    print("=== Per-axis STD per window: median / p95 (column 'STD' in our feature set is at index axis*17+4) ===")
    print(f"{'class/file':>14}  ", "  ".join(f"{c[:7]:>9}" for c in cols))
    n_axes = len(cols)

    def _std_stats(F):
        # Float formatting (not int(): FLOAT32 IMU STD is often < 1, which int() would collapse to 0).
        meds = [np.median(F[:, ai * 17 + 4]) for ai in range(n_axes)]
        p95s = [np.percentile(F[:, ai * 17 + 4], 95) for ai in range(n_axes)]
        return meds, p95s

    for c in classes:
        if c not in train_features:
            continue
        meds, p95s = _std_stats(train_features[c])
        print(f"  cls {c} med  ".rjust(14) + "  " + "  ".join(f"{m:>9.3g}" for m in meds))
        print(f"  cls {c} p95  ".rjust(14) + "  " + "  ".join(f"{p:>9.3g}" for p in p95s))
    meds, p95s = _std_stats(test_features)
    print(f"  test    med  ".rjust(14) + "  " + "  ".join(f"{m:>9.3g}" for m in meds))
    print(f"  test    p95  ".rjust(14) + "  " + "  ".join(f"{p:>9.3g}" for p in p95s))
    print()

    # Cohen's-d distance from test (overall) to each training class
    print("=== Mean Cohen's-d distance: test (overall) vs each training class ===")
    print("Lower = test data more similar to that class")
    test_mean = test_features.mean(axis=0)
    test_std = test_features.std(axis=0)

    # Compute each class's per-feature Cohen's-d ONCE, then flag the single closest class by argmin.
    # (The old one-liner ran min() over a generator of arrays, which raises ValueError under NumPy.)
    per_class_d = {}
    for c in classes:
        if c not in train_features:
            continue
        F = train_features[c]
        pooled = np.sqrt((F.std(axis=0) ** 2 + test_std ** 2) / 2 + 1e-9)
        per_class_d[c] = np.abs(F.mean(axis=0) - test_mean) / pooled
    closest = min(per_class_d, key=lambda k: float(per_class_d[k].mean())) if per_class_d else None
    for c in classes:
        if c not in per_class_d:
            continue
        d = per_class_d[c]
        flag = "  <-- closest" if c == closest else ""
        print(f"  class {c}: mean d={d.mean():.2f}  median d={np.median(d):.2f}  max d={d.max():.2f}{flag}")


if __name__ == "__main__":
    main()

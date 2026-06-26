#!/usr/bin/env python3
"""
check_signal_centered.py — verify whether a multi-class gesture training
CSV is "centered" (each 100-row window has its gesture peak roughly in the
middle), and which classes are centered vs. raw.

Usage:
    python3 check_signal_centered.py <csv_path> [--window 100]

For each class, walk through non-overlapping windows of size WINDOW, find the
argmax of |signal - window-mean| on the most active axis per window, and report
the distribution of those peak positions (0..WINDOW-1).

Heuristic verdict (per class), matching the thresholds in the code below:
- RAW      if peak-position std >= 25 (uniform-random positions have std ~ WINDOW/sqrt(12) ~ 29).
- CENTERED if the median peak position is within ±10 of WINDOW/2 AND std < 15.
- LOOSE    if the median is within ±10 of WINDOW/2 but std is wider (15 <= std < 25), e.g. tap.
- RAW      otherwise (median off-center).

Continuous classes (e.g. idle / "unknown" in the gesture-demo convention) are *expected* to read as
RAW — they are continuous streams, not discrete gesture events; discrete-gesture classes should read
CENTERED (tap-like ones often LOOSE). Which class index is continuous vs gesture is per-dataset, not a
platform rule — confirm against your own data (see data-skill-preset-contract).
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


SENSOR_COLS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]


def detect_separator(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
    if not head:
        return ","
    if ";" in head[0] and "," not in head[0]:
        return ";"
    if "\t" in head[0]:
        return "\t"
    return ","


def peak_position_per_window(seg: np.ndarray, win: int):
    """seg: shape (n_rows, n_axes). Return array of argmax(|x-mean|) per window
       on the per-window most-active axis."""
    n_win = len(seg) // win
    if n_win == 0:
        return np.array([], dtype=int)
    arr = seg[:n_win * win].reshape(n_win, win, -1)
    stds = arr.std(axis=1)                # (n_win, n_axes)
    axes = stds.argmax(axis=1)            # most-active axis per window
    peaks = []
    for w in range(n_win):
        x = arr[w, :, axes[w]].astype(np.float64)
        x -= x.mean()
        peaks.append(int(np.argmax(np.abs(x))))
    return np.array(peaks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--label-col", default="class")
    args = ap.parse_args()

    path = Path(args.csv)
    sep = detect_separator(path)
    df = pd.read_csv(path, sep=sep)
    if args.label_col not in df.columns:
        raise SystemExit(f"Column '{args.label_col}' not found in {path}")
    cols = [c for c in SENSOR_COLS if c in df.columns]
    if not cols:
        raise SystemExit(f"No sensor columns found; expected any of {SENSOR_COLS}")

    print(f"Loaded {path} ({sep!r}-sep)  rows={len(df):,}")
    print(f"Window size: {args.window}")
    print()
    midpoint = args.window // 2
    print(f"{'class':>5}  {'n_win':>5}  {'median':>6}  {'p25':>4}  {'p75':>4}  "
          f"{'std':>5}  verdict")
    for cls in sorted(df[args.label_col].unique()):
        seg = df[df[args.label_col] == cls][cols].values
        peaks = peak_position_per_window(seg, args.window)
        if len(peaks) == 0:
            print(f"  {cls}  too-short")
            continue
        med = int(np.median(peaks))
        p25 = int(np.percentile(peaks, 25))
        p75 = int(np.percentile(peaks, 75))
        std = float(peaks.std())
        # Uniform random positions in [0, window) have std ≈ window/sqrt(12) ≈ 29
        # for window=100. So std >= ~25 is the signature of a non-centered (random)
        # distribution regardless of median (which gravitates to mid by CLT).
        in_center = abs(med - midpoint) <= 10
        if std >= 25:
            verdict = "RAW (continuous stream or not centered)"
        elif in_center and std < 15:
            verdict = "CENTERED"
        elif in_center:
            verdict = "LOOSE (centered with wide tolerance)"
        else:
            verdict = "RAW (not centered)"
        print(f"  {cls}    {len(peaks):>5}  {med:>6}  {p25:>4}  {p75:>4}  "
              f"{std:>5.1f}  {verdict}")


if __name__ == "__main__":
    main()

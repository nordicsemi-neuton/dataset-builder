#!/usr/bin/env python3
"""
center_training_data.py
=======================

Center a multi-class IMU training CSV for the Nordic Edge AI Lab platform.

WHAT THIS SCRIPT DOES
---------------------
You collect raw recordings of each gesture, label them, and concatenate them
into one CSV with a `class` column. This script then:

  1. Splits the file by class.
  2. For each DISCRETE-GESTURE class (e.g. swipes, knock, tap): finds the
     motion events inside the recording and emits 100-row windows with the
     event peak placed near the middle. This is the "centering" step.
  3. For each CONTINUOUS class (idle, unknown, cwr, ccwr): keeps the stream
     as-is, trimmed to a multiple of the window length so it tiles cleanly
     into the platform's windowing.
  4. Concatenates everything back, in class-index order, and writes a single
     centered training CSV ready to upload to Edge AI Lab.

INPUT FORMAT
------------
A comma- or semicolon-separated CSV with these 7 columns (order matters,
header required):

    acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, class

`class` is an integer (0..N). Each class should already form ONE contiguous
block of rows — the file is NOT a randomly interleaved recording. This is
the same layout Edge AI Lab expects.

USAGE
-----
Basic:

    python3 center_training_data.py \\
        --input  raw_training_data.csv \\
        --output centered_training_data.csv

With non-default class encoding (e.g. you later add cwr=8, ccwr=9 as
continuous rotation classes):

    python3 center_training_data.py \\
        --input  raw_training_data.csv \\
        --output centered_training_data.csv \\
        --continuous-classes 0 1 8 9 \\
        --gesture-classes    2 3 4 5 6 7

WORK-AXIS PICKING
-----------------
The centering algorithm finds the motion peak on a single chosen axis (the
"work-axis"). For different gestures, different axes carry the signal:

  - swipe_left / swipe_right  →  lateral motion, often strong on gyro_y or acc_x
  - swipe_up / swipe_down     →  vertical wrist motion, strong on acc_y or gyro_x
  - knock / tap               →  short impulse, strong on gyro axes

If you see ONE class producing very few segments while the others look fine,
the work-axis is probably wrong FOR THAT CLASS. Three options, in order of
preference:

  (1) --auto-work-axis : try every axis for every gesture class and use the
      one that keeps the most windows. Slowest, but no tuning needed.

          python3 center_training_data.py ... --auto-work-axis

  (2) --work-axis-per-class : explicitly tell the script which axis to use
      for which class. Format is "cls:axis,cls:axis,...". Any class not in
      the list uses --work-axis (default acc_y).

          python3 center_training_data.py ... \\
              --work-axis-per-class "2:gyro_y,7:gyro_y"

  (3) --work-axis : the single default axis for all gesture classes. Only
      useful if you know all your gestures share the same dominant axis.

Optional: trim N samples from the start and end of EACH per-class block
BEFORE centering — useful for cleaning up the "I pressed record / I stopped
recording" artifacts at the edges of each gesture file:

    python3 center_training_data.py ... --trim-edges 200

RECOMMENDED PRE-STEP
--------------------
Before running this script, in your raw per-gesture recording files, drop the
first and last ~200-300 rows of each file (the act of starting/stopping the
recording introduces hiccups). You can do this either:

  (a) in pandas before concatenating into the multi-class file
        df = df.iloc[200:-200]
  (b) via the --trim-edges flag, which does this per-class on the merged
        file. (a) gives you tighter control.

DEPENDENCIES
------------
  numpy, pandas only. (Centering uses a NumPy envelope peak finder; no scipy.)

CONTACT
-------
Questions: Nordic Edge AI Lab support.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd


SENSOR_COLUMNS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]
REQUIRED_COLUMNS = SENSOR_COLUMNS + ["class"]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def detect_separator(path: Path) -> str:
    """Look at the first line and guess the delimiter (`,` `;` or `\\t`)."""
    head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:1]
    if not head:
        return ","
    line = head[0]
    if ";" in line and "," not in line:
        return ";"
    if "\t" in line:
        return "\t"
    return ","


def load_input(path: Path) -> pd.DataFrame:
    sep = detect_separator(path)
    print(f"Input delimiter: {sep!r}")
    df = pd.read_csv(path, sep=sep)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(
            f"ERROR: input is missing required columns: {missing}\n"
            f"Expected columns: {REQUIRED_COLUMNS}"
        )
    # Coerce to numeric. Sensor axes stay FLOAT (never astype(int) — that truncated 9.78 -> 9).
    for c in REQUIRED_COLUMNS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad_idx = df.index[df[REQUIRED_COLUMNS].isna().any(axis=1)].tolist()
    df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)
    if bad_idx:
        # Loud, not silent: the production path (src/data_builder) repairs+reports instead of dropping.
        print(f"WARNING: dropped {len(bad_idx)} row(s) containing non-numeric / empty values "
              f"(first indices: {bad_idx[:5]}). This reference script drops them; the data-builder "
              f"reports them instead.")
    df["class"] = df["class"].astype(int)   # label is an integer class id; sensor axes remain float
    return df


# ---------------------------------------------------------------------------
# Segmentation / centering logic
# ---------------------------------------------------------------------------
def envelope_signal(axis: np.ndarray, work_window: int, step: int = 1) -> np.ndarray:
    """min/max envelope of `axis` over a rolling work_window."""
    out = []
    for i in range(0, len(axis) - work_window, step):
        w = axis[i : i + work_window]
        out.append(np.sqrt(w.min() ** 2 + w.max() ** 2))
    return np.asarray(out, dtype=np.float64)


def detect_segments(env: np.ndarray, work_window: int, threshold_coef: float
                    ) -> List[Tuple[int, int]]:
    """Return list of (start, end) sample indices for each above-threshold run."""
    if len(env) == 0:
        return []
    threshold = threshold_coef * float(env.mean())
    segments: List[Tuple[int, int]] = []
    started = False
    start = 0
    for i, v in enumerate(env, start=1):
        if v > threshold and not started:
            started = True
            start = i
        elif v <= threshold and started:
            started = False
            segments.append((start + work_window // 2, i + work_window // 2))
    if started:
        segments.append((start + work_window // 2, len(env) + work_window // 2))
    return segments


def deduplicate_centers(scored_centers: List[Tuple[int, float]],
                        min_distance: int) -> List[int]:
    """NMS-style: keep strongest centers, enforce a minimum distance between them."""
    if min_distance <= 0:
        return sorted(c for c, _ in scored_centers)
    by_score = sorted(scored_centers, key=lambda x: x[1], reverse=True)
    kept: List[int] = []
    for c, _ in by_score:
        if all(abs(c - k) >= min_distance for k in kept):
            kept.append(c)
    return sorted(kept)


def center_gesture_class(df_class: pd.DataFrame,
                         work_axis: str,
                         window: int,
                         work_window_ratio: float,
                         threshold: float,
                         peak_tolerance: int) -> Tuple[pd.DataFrame, dict]:
    """Center one class's recording. Returns (centered_df, stats)."""
    work_window = int(window * work_window_ratio)
    axis = df_class[work_axis].to_numpy(dtype=np.float64)
    axis = axis - axis.mean()                  # de-mean
    abs_peak = np.abs(axis)

    env = envelope_signal(axis, work_window=work_window)
    segments = detect_segments(env, work_window=work_window, threshold_coef=threshold)

    # Pick the strongest sample inside each detected segment as the center.
    candidates: List[Tuple[int, float]] = []
    for s, e in segments:
        s = max(0, s); e = min(len(abs_peak), e)
        if e - s <= 1:
            continue
        local_peak = int(s + np.argmax(abs_peak[s:e]))
        candidates.append((local_peak, float(abs_peak[local_peak])))

    selected = deduplicate_centers(candidates, min_distance=window)

    half = window // 2
    windows: List[pd.DataFrame] = []
    dropped = 0
    for c in selected:
        left = c - half
        right = left + window
        if left < 0 or right > len(df_class):
            dropped += 1
            continue
        w_df = df_class.iloc[left:right]
        if peak_tolerance >= 0:
            # Confirm the strongest sample in the picked window is near the middle.
            wpeak = int(np.argmax(abs_peak[left:right]))
            if abs(wpeak - half) > peak_tolerance:
                dropped += 1
                continue
        windows.append(w_df)

    if not windows:
        out = pd.DataFrame(columns=df_class.columns)
    else:
        out = pd.concat(windows, ignore_index=True)

    stats = {
        "found_segments": len(segments),
        "selected_centers": len(selected),
        "kept_windows": len(windows),
        "dropped_windows": dropped,
    }
    return out, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Center a multi-class IMU training CSV for Edge AI Lab.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input", required=True, type=Path,
                    help="Raw multi-class training CSV.")
    ap.add_argument("--output", required=True, type=Path,
                    help="Output centered CSV (comma-separated).")
    ap.add_argument("--window", type=int, default=100,
                    help="Window size in samples. Must match what you set on the "
                         "Edge AI Lab platform. Default: 100.")
    ap.add_argument("--continuous-classes", type=int, nargs="*", default=[0, 1],
                    help="Class IDs that are continuous streams and must NOT be "
                         "centered (idle, unknown, cwr, ccwr). Default: 0 1.")
    ap.add_argument("--gesture-classes", type=int, nargs="*",
                    default=[2, 3, 4, 5, 6, 7],
                    help="Class IDs that are discrete gestures and MUST be "
                         "centered. Default: 2 3 4 5 6 7.")
    ap.add_argument("--work-axis", choices=SENSOR_COLUMNS, default="acc_y",
                    help="Default axis used to detect the motion peak for any "
                         "class not covered by --work-axis-per-class or "
                         "--auto-work-axis. Default: acc_y.")
    ap.add_argument("--work-axis-per-class", default="",
                    help="Per-class work-axis override, format "
                         "'cls:axis,cls:axis'. Example: '2:gyro_y,7:gyro_y'. "
                         "Classes not listed fall back to --work-axis.")
    ap.add_argument("--auto-work-axis", action="store_true",
                    help="For each gesture class, try every sensor axis and "
                         "use the one that produces the most kept windows. "
                         "Overrides --work-axis and --work-axis-per-class.")
    ap.add_argument("--work-window-ratio", type=float, default=0.95,
                    help="Internal detection window as a fraction of --window. "
                         "Default: 0.95.")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="Segmentation threshold coefficient. Higher = stricter "
                         "(only big peaks counted). Default: 0.5.")
    ap.add_argument("--peak-tolerance", type=int, default=10,
                    help="Drop a window if its peak is farther than this many "
                         "samples from the window center. Set -1 to disable. "
                         "Default: 10.")
    ap.add_argument("--trim-edges", type=int, default=0,
                    help="Drop this many rows from the start AND end of each "
                         "per-class block BEFORE centering. Helps if you didn't "
                         "already trim your raw per-gesture recordings. "
                         "Default: 0.")
    args = ap.parse_args()

    if args.window <= 0:
        sys.exit("ERROR: --window must be > 0")

    # Parse --work-axis-per-class string "cls:axis,cls:axis" → {int: str}.
    per_class_axis: dict[int, str] = {}
    if args.work_axis_per_class.strip():
        for pair in args.work_axis_per_class.split(","):
            pair = pair.strip()
            if not pair:
                continue
            if ":" not in pair:
                sys.exit(f"ERROR: --work-axis-per-class entry {pair!r} must be 'cls:axis'")
            cls_str, axis = (s.strip() for s in pair.split(":", 1))
            try:
                cls_int = int(cls_str)
            except ValueError:
                sys.exit(f"ERROR: bad class id {cls_str!r} in --work-axis-per-class")
            if axis not in SENSOR_COLUMNS:
                sys.exit(f"ERROR: bad axis {axis!r}; must be one of {SENSOR_COLUMNS}")
            per_class_axis[cls_int] = axis

    df = load_input(args.input)
    classes_present = sorted(df["class"].unique().tolist())
    print(f"Input: {len(df):,} rows; classes present: {classes_present}")
    print(f"Centering window: {args.window}")
    print(f"Continuous classes: {args.continuous_classes}")
    print(f"Gesture classes:    {args.gesture_classes}")
    print()

    parts: List[Tuple[int, pd.DataFrame]] = []

    # ---- continuous classes: trim to a multiple of the window ----
    for cls in args.continuous_classes:
        if cls not in classes_present:
            continue
        sub = df[df["class"] == cls][REQUIRED_COLUMNS].copy().reset_index(drop=True)
        if args.trim_edges > 0 and len(sub) > 2 * args.trim_edges:
            sub = sub.iloc[args.trim_edges:-args.trim_edges].reset_index(drop=True)
        n_keep = (len(sub) // args.window) * args.window
        sub = sub.iloc[:n_keep].copy()
        sub["class"] = cls
        parts.append((cls, sub))
        print(f"class {cls} (continuous): kept {len(sub):>6} rows "
              f"({len(sub)//args.window} windows)")

    # ---- gesture classes: center each ----
    for cls in args.gesture_classes:
        if cls not in classes_present:
            print(f"class {cls} (gesture): not present, skipping")
            continue
        sub = df[df["class"] == cls][REQUIRED_COLUMNS].copy().reset_index(drop=True)
        if args.trim_edges > 0 and len(sub) > 2 * args.trim_edges:
            sub = sub.iloc[args.trim_edges:-args.trim_edges].reset_index(drop=True)

        # Decide which axis to use for THIS class.
        if args.auto_work_axis:
            best_axis, best_kept, best_centered, best_stats = None, -1, None, None
            for ax in SENSOR_COLUMNS:
                c, s = center_gesture_class(
                    df_class=sub, work_axis=ax, window=args.window,
                    work_window_ratio=args.work_window_ratio,
                    threshold=args.threshold, peak_tolerance=args.peak_tolerance,
                )
                if s["kept_windows"] > best_kept:
                    best_axis, best_kept = ax, s["kept_windows"]
                    best_centered, best_stats = c, s
            chosen_axis, centered, stats = best_axis, best_centered, best_stats
        else:
            chosen_axis = per_class_axis.get(cls, args.work_axis)
            centered, stats = center_gesture_class(
                df_class=sub, work_axis=chosen_axis, window=args.window,
                work_window_ratio=args.work_window_ratio,
                threshold=args.threshold, peak_tolerance=args.peak_tolerance,
            )
        centered["class"] = cls
        parts.append((cls, centered[REQUIRED_COLUMNS]))
        print(f"class {cls} (gesture, axis={chosen_axis:>6}): "
              f"segments={stats['found_segments']:>4}  "
              f"centers={stats['selected_centers']:>4}  "
              f"kept={stats['kept_windows']:>4}  "
              f"dropped={stats['dropped_windows']:>4}  "
              f"→ {stats['kept_windows']*args.window:>5} rows")

    # ---- concatenate in canonical class order ----
    parts.sort(key=lambda x: x[0])
    merged = pd.concat([p[1] for p in parts], ignore_index=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)
    print()
    print(f"=== Saved: {args.output} ===")
    print(f"Total rows: {len(merged):,}")
    print("Per-class window counts:")
    for cls in sorted(merged["class"].unique()):
        n = int((merged["class"] == cls).sum())
        print(f"  class {cls}: {n:>6} rows  ({n // args.window} windows)")


if __name__ == "__main__":
    main()

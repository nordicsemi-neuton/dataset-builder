#!/usr/bin/env python3
"""
apply_centering_per_class.py — wrap an external center_signal.py and apply it
correctly to a multi-class training CSV.

PROBLEM the wrapper solves
==========================
An external `center_signal.py` (a gesture project's own centering script) runs peak
detection on a SINGLE axis across the WHOLE file. If you feed it a multi-class
training CSV where each class is a contiguous block, peak detection straddles
class boundaries and produces garbage centering.

Also, a common project convention is:
    "Centering of all gestures, except for rotation, idle and unknown"

So we need to:
  1. Split the input file by class.
  2. Run center_signal.py on each *discrete-gesture* class (2..7) only.
  3. Leave idle (0) and unknown (1) as continuous streams (just trim to a
     multiple of WINDOW so they tile cleanly into the platform's windowing).
  4. Concatenate everything back into a single file, preserving the
     one-contiguous-block-per-class layout the platform expects.

This wrapper does that.

PRECONDITIONS
=============
- An external center_signal.py must be available (path passed in via --src-dir).
- Input CSV must have columns: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, class
- Delimiter is auto-detected (',' or ';').

DEFAULTS (typical multi-class gesture conventions — adjust if yours differ)
=====================================================================
- window = 100 samples
- continuous classes = {0, 1}  (idle, unknown)
- gesture classes    = {2, 3, 4, 5, 6, 7}  (swipes, knock, tap)
- center_signal.py defaults: --work-axis acc_y, segment pipeline, threshold 0.5

USAGE
=====
    python3 apply_centering_per_class.py \\
        --src-dir /path/to/center_signal_dir \\
        --input  /path/to/training_data_raw.csv \\
        --output /path/to/training_data_centered.csv \\
        --window 100

    # Optional: override which classes get centered
    python3 apply_centering_per_class.py ... \\
        --continuous-classes 0 1 \\
        --gesture-classes 2 3 4 5 6 7

VERIFY CENTERING QUALITY
========================
After running, use ../diagnostics/check_signal_centered.py on the output to confirm
peak-position std per 100-row window is < 20 for the discrete-gesture classes.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z", "class"]


def detect_separator(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:2]
    if not head:
        return ","
    line = head[0]
    if ";" in line and "," not in line:
        return ";"
    if "\t" in line:
        return "\t"
    return ","


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir", required=True, type=Path,
                    help="Path to the directory containing center_signal.py "
                         "(e.g. <repo>/src)")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--window", type=int, default=100)
    ap.add_argument("--continuous-classes", type=int, nargs="*", default=[0, 1],
                    help="Classes to trim-only (not center). Default: 0 1")
    ap.add_argument("--gesture-classes", type=int, nargs="*",
                    default=[2, 3, 4, 5, 6, 7],
                    help="Classes to center. Default: 2 3 4 5 6 7")
    ap.add_argument("--work-axis", default="acc_y",
                    help="Axis used by center_signal.py for peak detection. "
                         "Default acc_y matches the typical gesture convention.")
    ap.add_argument("--keep-intermediates", action="store_true",
                    help="Keep per-class split / centered CSVs in a sibling "
                         "directory of --output for inspection.")
    args = ap.parse_args()

    center_script = args.src_dir / "center_signal.py"
    if not center_script.exists():
        sys.exit(f"ERROR: {center_script} not found")

    sep_in = detect_separator(args.input)
    print(f"Input separator detected: {sep_in!r}")

    df = pd.read_csv(args.input, sep=sep_in)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: input missing columns: {missing}")

    print(f"Input: {len(df):,} rows; classes present: "
          f"{sorted(df['class'].unique().tolist())}")

    # Pick intermediates directory
    if args.keep_intermediates:
        out_dir = args.output.parent
        split_dir = out_dir / f"_split_{args.input.stem}"
        centered_dir = out_dir / f"_centered_{args.input.stem}"
        split_dir.mkdir(exist_ok=True)
        centered_dir.mkdir(exist_ok=True)
    else:
        tmpdir = Path(tempfile.mkdtemp(prefix="apply_centering_"))
        split_dir = tmpdir / "split"
        centered_dir = tmpdir / "centered"
        split_dir.mkdir()
        centered_dir.mkdir()

    # Split by class (use semicolon as the canonical pipeline separator)
    classes_present = sorted(df["class"].unique().tolist())
    for cls in classes_present:
        sub = df[df["class"] == cls][REQUIRED_COLUMNS]
        sub.to_csv(split_dir / f"class_{cls}.csv", sep=";", index=False)

    parts = []

    # Continuous classes: trim to a multiple of WINDOW
    for cls in args.continuous_classes:
        if cls not in classes_present:
            continue
        sub = df[df["class"] == cls][REQUIRED_COLUMNS].copy()
        n_trim = (len(sub) // args.window) * args.window
        sub = sub.iloc[:n_trim].copy()
        sub["class"] = cls
        parts.append(("continuous", cls, sub))
        print(f"class {cls} (continuous): trimmed to {len(sub)} rows "
              f"({len(sub)//args.window} windows)")

    # Gesture classes: run center_signal.py on each
    for cls in args.gesture_classes:
        if cls not in classes_present:
            print(f"class {cls} (gesture): NOT in input, skipping")
            continue
        in_path = split_dir / f"class_{cls}.csv"
        out_path = centered_dir / f"class_{cls}.csv"
        cmd = [
            "python3", str(center_script),
            "--input", str(in_path),
            "--output", str(out_path),
            "--sep", ";",
            "--window", str(args.window),
            "--work-axis", args.work_axis,
        ]
        print(f"class {cls} (gesture): running center_signal.py …")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit(f"ERROR centering class {cls}:\n{result.stderr}")
        # Print short summary from center_signal.py stdout
        summary = [line for line in result.stdout.splitlines()
                   if line.startswith(("Input rows", "Found segments",
                                       "Selected centers", "Dropped segments",
                                       "Output rows", "Centered windows"))]
        for line in summary:
            print(f"    {line}")
        sub = pd.read_csv(out_path, sep=";")
        for col in REQUIRED_COLUMNS:
            sub[col] = pd.to_numeric(sub[col], errors="coerce").astype(int)
        sub["class"] = cls
        parts.append(("centered", cls, sub[REQUIRED_COLUMNS]))

    # Concatenate in canonical class order (0, 1, 2, 3, 4, 5, 6, 7)
    ordered = sorted(parts, key=lambda x: x[1])
    merged = pd.concat([p[2] for p in ordered], ignore_index=True)
    merged.to_csv(args.output, index=False)  # always comma — platform-friendly
    print()
    print(f"=== Saved: {args.output} ===")
    print(f"rows: {len(merged):,}")
    print("Per-class:")
    for cls in sorted(merged["class"].unique()):
        n = (merged["class"] == cls).sum()
        print(f"  class {cls}: {n:>6}  ({n // args.window} windows)")

    if not args.keep_intermediates:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

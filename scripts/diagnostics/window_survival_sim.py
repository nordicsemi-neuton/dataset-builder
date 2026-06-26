#!/usr/bin/env python3
"""
window_survival_sim.py — simulate Edge AI Lab's per-window pure-label extraction.

Estimates how many "pure" (single-label) windows the platform will produce per
class for a given window size and sliding shift. Useful when the user complains
that data is being removed at preprocessing — usually because their per-label
contiguous runs are shorter than the window size, so windows that span label
boundaries are dropped.

Usage:
    python3 window_survival_sim.py <csv_path> --window 150 --shift 10
    python3 window_survival_sim.py <csv_path> --window 150 --shift 10 --window 100 --shift 100

Multiple --window / --shift flags can be passed in pairs to compare
configurations side-by-side.
"""
import argparse
import sys
import numpy as np
import pandas as pd


def simulate(df, label_col, session_col, window, shift):
    counts = {l: 0 for l in sorted(df[label_col].unique())}
    total = 0
    if session_col in df.columns:
        groups = df.groupby(session_col)
    else:
        groups = [(None, df)]
    for _, sub in groups:
        lab = sub[label_col].values
        if len(lab) < window:
            continue
        for start in range(0, len(lab) - window + 1, shift):
            total += 1
            chunk = lab[start:start + window]
            if (chunk == chunk[0]).all():
                counts[chunk[0]] += 1
    pure = sum(counts.values())
    mixed = total - pure
    return total, pure, mixed, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--label-col", default="label")
    ap.add_argument("--session-col", default="session_id")
    ap.add_argument("--window", type=int, action="append", required=True)
    ap.add_argument("--shift", type=int, action="append", required=True)
    args = ap.parse_args()

    if len(args.window) != len(args.shift):
        sys.exit("ERROR: --window and --shift must be passed in equal counts (paired)")

    df = pd.read_csv(args.csv)
    print(f"loaded {args.csv}: {len(df):,} rows, "
          f"{df[args.label_col].nunique()} labels, "
          f"{df[args.session_col].nunique() if args.session_col in df.columns else 1} sessions")

    for w, s in zip(args.window, args.shift):
        total, pure, mixed, counts = simulate(df, args.label_col, args.session_col, w, s)
        pct = 100 * mixed / total if total else 0
        print(f"\n=== window={w}, shift={s} ===")
        print(f"  total candidate windows: {total:,}")
        print(f"  pure (kept):             {pure:,}")
        print(f"  mixed (dropped):         {mixed:,} ({pct:.1f}%)")
        print(f"  per-label pure windows:")
        for k, v in counts.items():
            warn = "  <-- ZERO" if v == 0 else ""
            print(f"    label {int(k)}: {v:,}{warn}")


if __name__ == "__main__":
    main()

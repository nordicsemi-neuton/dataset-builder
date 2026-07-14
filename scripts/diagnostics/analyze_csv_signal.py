#!/usr/bin/env python3
"""
analyze_csv_signal.py — first-pass profiler for a user-uploaded sensor CSV.

Usage:
    python3 analyze_csv_signal.py <csv_path> [--label-col=label] [--session-col=session_id] [--time-col=t_us]

Prints:
    - schema (columns, dtypes)
    - row count and overall label distribution
    - session count, lengths, length distribution
    - per-session class composition (crosstab)
    - per-session per-label run-length stats (key for windowing diagnostics)
    - per-session sampling rate (median dt between consecutive rows)

Requires only pandas + numpy.
"""
import sys
import argparse
import numpy as np
import pandas as pd

# Windows consoles/pipes default to cp1252, which cannot encode every character in
# this tool's output; degrade to '?' instead of crashing (no-op on UTF-8 terminals).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def runs(arr):
    """Return (run_values, run_lengths) for a 1D numpy array."""
    if len(arr) == 0:
        return np.array([]), np.array([])
    breaks = np.where(arr[1:] != arr[:-1])[0] + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(arr)]
    return arr[starts], ends - starts


def profile(csv_path, label_col="label", session_col="session_id", time_col="t_us"):
    df = pd.read_csv(csv_path)

    print(f"=== {csv_path} ===")
    print(f"rows: {len(df):,}    cols: {list(df.columns)}")
    print(f"dtypes: {df.dtypes.to_dict()}")

    # NaN check
    n_na = df.isna().sum().sum()
    if n_na:
        print(f"WARNING: {n_na} NaN cells found")

    if label_col not in df.columns:
        print(f"\n(no '{label_col}' column — skipping label analysis)")
        return

    print("\n=== Label distribution ===")
    print(df[label_col].value_counts().sort_index().to_string())
    unique_labels = sorted(df[label_col].unique())
    expected = list(range(len(unique_labels)))
    if list(unique_labels) != expected:
        print(f"WARNING: labels are {unique_labels} — platform requires contiguous 0..N-1")

    if session_col in df.columns:
        sess = df.groupby(session_col)
        print(f"\n=== Sessions ({df[session_col].nunique()}) ===")
        lengths = sess.size().sort_values()
        print(f"length stats: min={lengths.min()} p25={int(np.percentile(lengths,25))} "
              f"median={int(np.median(lengths))} p75={int(np.percentile(lengths,75))} "
              f"max={lengths.max()}  total={lengths.sum():,}")

        print("\n=== Per-session class composition (rows) ===")
        ct = pd.crosstab(df[session_col], df[label_col])
        print(ct.to_string())

        print("\n=== Per-session per-label run-length stats ===")
        print(f"{'session':>8} {'label':>5} {'n_rows':>7} {'n_runs':>6} {'max_run':>7} {'p95_run':>7}")
        for sid, sub in sess:
            lab = sub[label_col].values
            run_vals, run_lens = runs(lab)
            for label_val in sorted(np.unique(lab)):
                mask = run_vals == label_val
                rl = run_lens[mask]
                if len(rl) == 0:
                    continue
                print(f"{sid:>8} {int(label_val):>5} {int(rl.sum()):>7} {len(rl):>6} "
                      f"{int(rl.max()):>7} {int(np.percentile(rl, 95)):>7}")

        if time_col in df.columns:
            print("\n=== Sampling rate per session ===")
            for sid, sub in sess:
                dt = sub.sort_values(time_col)[time_col].diff().dropna()
                if len(dt) and dt.median() > 0:
                    hz = 1e6 / dt.median()
                    print(f"  session {sid}: median dt={dt.median():.0f} us  -> {hz:.1f} Hz, "
                          f"n_rows={len(sub):,}")
                else:
                    print(f"  session {sid}: dt unavailable")
    else:
        print(f"\n(no '{session_col}' column — skipping session analysis)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--label-col", default="label")
    ap.add_argument("--session-col", default="session_id")
    ap.add_argument("--time-col", default="t_us")
    args = ap.parse_args()
    profile(args.csv, args.label_col, args.session_col, args.time_col)


if __name__ == "__main__":
    main()

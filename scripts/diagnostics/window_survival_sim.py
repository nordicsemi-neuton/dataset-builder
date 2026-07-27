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

# Windows consoles/pipes default to cp1252, which cannot encode every character in
# this tool's output; degrade to '?' instead of crashing (no-op on UTF-8 terminals).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def _valid_label(v):
    """A label is usable iff it is present and, when numeric, finite. Missing / NaN / +-inf
    labels are not real classes — the platform requires every value numeric and finite — so they
    are never counted as a class (which would print a phantom '<-- ZERO' line) nor used as a dict
    key (which crashed on int()/OverflowError before)."""
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(v, (float, np.floating)):
        return bool(np.isfinite(v))
    return True


def _fmt_label(v):
    """Render a label for display. Integral numerics (int, integral float, bool) print as bare
    integers, byte-identical to the previous int(k); anything else prints as itself instead of
    crashing (the bug: int('run') / int(NaN) / int(inf))."""
    if isinstance(v, (bool, np.bool_)):
        return str(int(v))
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)) and np.isfinite(v) and float(v).is_integer():
        return str(int(v))
    return str(v)


def _sorted_labels(values):
    """Sort the distinct valid labels. Falls back to string order only when the values are not
    mutually comparable (e.g. a column mixing text and numbers), which otherwise raises TypeError;
    homogeneous label sets sort exactly as before."""
    valid = [v for v in values if _valid_label(v)]
    try:
        return sorted(valid)
    except TypeError:
        return sorted(valid, key=str)


def simulate(df, label_col, session_col, window, shift):
    counts = {l: 0 for l in _sorted_labels(df[label_col].unique())}
    invalid_rows = int((~df[label_col].map(_valid_label)).sum())
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
            # A window is pure only if every row shares one *valid* label. Windows that are all
            # one invalid label (e.g. an inf run) satisfy chunk==chunk[0] but are not a real class,
            # so they fall into "mixed" rather than being counted or crashing on the key.
            if (chunk == chunk[0]).all() and _valid_label(chunk[0]):
                counts[chunk[0]] += 1
    pure = sum(counts.values())
    mixed = total - pure
    return total, pure, mixed, counts, invalid_rows


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
    n_labels = len(_sorted_labels(df[args.label_col].unique()))
    print(f"loaded {args.csv}: {len(df):,} rows, "
          f"{n_labels} labels, "
          f"{df[args.session_col].nunique() if args.session_col in df.columns else 1} sessions")

    for w, s in zip(args.window, args.shift):
        total, pure, mixed, counts, invalid_rows = simulate(
            df, args.label_col, args.session_col, w, s)
        pct = 100 * mixed / total if total else 0
        print(f"\n=== window={w}, shift={s} ===")
        print(f"  total candidate windows: {total:,}")
        print(f"  pure (kept):             {pure:,}")
        print(f"  mixed (dropped):         {mixed:,} ({pct:.1f}%)")
        if invalid_rows:
            print(f"  ({invalid_rows:,} row(s) have a missing / non-finite label — not a real class; "
                  f"they break the label runs windows are drawn from and are excluded below)")
        print(f"  per-label pure windows:")
        for k, v in counts.items():
            warn = "  <-- ZERO" if v == 0 else ""
            print(f"    label {_fmt_label(k)}: {v:,}{warn}")


if __name__ == "__main__":
    main()

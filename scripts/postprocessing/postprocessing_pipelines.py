#!/usr/bin/env python3
"""
postprocessing_pipelines.py — apply and compare prediction-postprocessing pipelines
on Edge AI Lab inference-runner output (a CSV with columns 'target' and
'Probability of 0' .. 'Probability of N').

Usage:
    python3 postprocessing_pipelines.py <predictions.csv>
    python3 postprocessing_pipelines.py <predictions.csv> --compare-baseline

Tests:
1. Postprocessing ceiling per class (max-prob, mean-prob, rank distribution).
   If max-prob is ~0 for a class, NO postprocessing can recover it — class is dead.
2. Several pipelines side-by-side: baseline argmax, top-1 threshold, consecutive-N,
   majority-vote-K, exclude-unknown argmax, EMA-smoothed argmax, hybrid production
   (EMA → unknown-margin suppression → threshold → consecutive-N).
3. Per-class frame counts and episode counts for each pipeline.

Episodes vs frames: a frame is one inference window; an episode is a contiguous
run of same predicted class. On-device, episodes matter more — they correspond
to "events" the firmware reports.
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


def load_predictions(path: str):
    df = pd.read_csv(path)
    prob_cols = [c for c in df.columns if c.startswith("Probability of ")]
    if not prob_cols:
        sys.exit("ERROR: no 'Probability of X' columns found")
    P = df[prob_cols].values
    return df, P, len(prob_cols)


def ceiling_check(P: np.ndarray):
    n_classes = P.shape[1]
    print("=== Postprocessing ceiling per class ===")
    print("(if max-prob is 0 for class C, NO postprocessing can recover it)")
    print(f"  {'cls':>4} {'max':>10} {'mean':>10} {'top1':>6} {'top2':>6} {'top3':>6} {'never_top3':>11}")
    ranks = np.argsort(-P, axis=1)
    for c in range(n_classes):
        max_p = P[:, c].max()
        mean_p = P[:, c].mean()
        r1 = (ranks[:, 0] == c).sum()
        r2 = (ranks[:, 1] == c).sum()
        r3 = (ranks[:, 2] == c).sum()
        not_top3 = ((ranks[:, :3] == c).sum(axis=1) == 0).sum()
        marker = "  <-- DEAD" if max_p < 0.1 else ""
        print(f"  {c:>4} {max_p:>10.4f} {mean_p:>10.4f} {r1:>6} {r2:>6} {r3:>6} {not_top3:>11}{marker}")
    print()


def baseline(P):
    return P.argmax(axis=1)


def threshold(P, thr=0.95):
    top = P.max(axis=1)
    cls = P.argmax(axis=1)
    return np.where(top >= thr, cls, -1)


def consecutive_N(preds, N=3):
    out = np.full_like(preds, -1)
    if len(preds) == 0:
        return out
    streak_cls = preds[0]
    streak_len = 1
    current = -1
    for i, p in enumerate(preds):
        if p == streak_cls:
            streak_len += 1
        else:
            streak_cls = p
            streak_len = 1
        if streak_len >= N:
            current = streak_cls
        out[i] = current
    return out


def majority_vote_K(preds, K=5):
    out = np.full_like(preds, -1)
    for i in range(len(preds)):
        lo = max(0, i - K + 1)
        window = preds[lo:i + 1]
        valid = window[window != -1]
        if len(valid) == 0:
            out[i] = -1
        else:
            vals, cnts = np.unique(valid, return_counts=True)
            out[i] = int(vals[cnts.argmax()])
    return out


def exclude_unknown_argmax(P, min_prob=0.5, unknown_class=1):
    P_no = P.copy()
    P_no[:, unknown_class] = -np.inf
    cls = P_no.argmax(axis=1)
    p = P_no.max(axis=1)
    return np.where(p >= min_prob, cls, -1)


def ema_smooth(P, alpha=0.3):
    out = np.zeros_like(P)
    out[0] = P[0]
    for i in range(1, len(P)):
        out[i] = alpha * P[i] + (1 - alpha) * out[i - 1]
    return out


def production_pipe(P, alpha=0.3, thr=0.6, N=2,
                    suppress_unknown_margin=0.2, unknown_class=1):
    """EMA → suppress narrow-margin unknown wins → threshold top-1 → consecutive-N."""
    smooth = ema_smooth(P, alpha)
    cls = smooth.argmax(axis=1)
    top = smooth.max(axis=1)
    P_no = smooth.copy()
    P_no[:, unknown_class] = -np.inf
    cls_alt = P_no.argmax(axis=1)
    top_alt = P_no.max(axis=1)
    swap = (cls == unknown_class) & ((top - top_alt) < suppress_unknown_margin)
    cls = np.where(swap, cls_alt, cls)
    top = np.where(swap, top_alt, top)
    cls = np.where(top >= thr, cls, -1)

    out = np.full_like(cls, -1)
    streak = -1
    streak_len = 0
    current = -1
    for i, p in enumerate(cls):
        if p == -1:
            streak = -1
            streak_len = 0
        elif p == streak:
            streak_len += 1
        else:
            streak = p
            streak_len = 1
        if streak_len >= N:
            current = streak
        out[i] = current
    return out


def episodes(preds):
    """Return list of (class, start, end, length) for each contiguous run (excluding -1)."""
    if len(preds) == 0:
        return []
    runs = []
    cur = preds[0]
    start = 0
    for i in range(1, len(preds)):
        if preds[i] != cur:
            runs.append((int(cur), start, i, i - start))
            cur = preds[i]
            start = i
    runs.append((int(cur), start, len(preds), len(preds) - start))
    return [r for r in runs if r[0] >= 0]


def report(name, preds, n_classes, n_total):
    n_pred = (preds >= 0).sum()
    n_drop = n_total - n_pred
    eps = episodes(preds)
    counts = {c: sum(1 for r in eps if r[0] == c) for c in range(n_classes)}
    frames = {c: int((preds == c).sum()) for c in range(n_classes)}
    line = f"  {name:>40} | drop={n_drop:>3} ({100*n_drop/n_total:>3.0f}%) | "
    line += "frames: " + " ".join(f"{c}={frames[c]}" for c in range(n_classes) if frames[c]) + " | "
    line += "episodes: " + " ".join(f"{c}={counts[c]}" for c in range(n_classes) if counts[c])
    print(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions_csv")
    ap.add_argument("--unknown-class", type=int, default=1,
                    help="class index treated as 'unknown' (default 1)")
    args = ap.parse_args()

    df, P, n_classes = load_predictions(args.predictions_csv)
    n = len(df)
    print(f"Loaded {args.predictions_csv}: {n} windows, {n_classes} classes\n")
    ceiling_check(P)

    base = baseline(P)
    print("=== Postprocessing pipeline comparison ===")
    report("baseline (argmax)", base, n_classes, n)
    for thr in [0.50, 0.80, 0.95, 0.99]:
        report(f"threshold={thr}", threshold(P, thr), n_classes, n)
    for N in [2, 3, 5]:
        report(f"consecutive-N={N}", consecutive_N(base, N), n_classes, n)
    for K in [3, 5, 7]:
        report(f"majority-vote K={K}", majority_vote_K(base, K), n_classes, n)
    for thr in [0.10, 0.30, 0.50]:
        report(f"no-unknown >= {thr}",
               exclude_unknown_argmax(P, thr, args.unknown_class), n_classes, n)
    for a in [0.1, 0.3, 0.5]:
        report(f"EMA-smooth alpha={a}", ema_smooth(P, a).argmax(axis=1), n_classes, n)
    report("PRODUCTION (EMA0.3 + supp + thr0.6 + N=2)",
           production_pipe(P, unknown_class=args.unknown_class), n_classes, n)


if __name__ == "__main__":
    main()

"""window_survival — per-(session,label) run lengths + pure-window survival.

Generalises scripts/diagnostics/window_survival_sim.py. The strict-pure model is an UPPER BOUND on
data loss; every finding it feeds carries the "verify in the platform's Processed Data view" framing
(databuilder-001 [gate]). Column names come from the reconciled profile — no hardcoded defaults.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"
VERIFY_NOTE = "Upper bound — confirm against the platform's Processed Data view after upload."


def _runs(arr: np.ndarray):
    if len(arr) == 0:
        return np.array([]), np.array([])
    breaks = np.where(arr[1:] != arr[:-1])[0] + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(arr)]
    return arr[starts], ends - starts


def _groups(df: pd.DataFrame, session_col: str | None):
    if session_col and session_col in df.columns:
        return list(df.groupby(session_col, sort=False))
    return [(None, df)]


def run_lengths(df: pd.DataFrame, label_col: str, session_col: str | None):
    """Return {label: {'max_run': int, 'total': int, 'n_runs': int}} aggregated across sessions."""
    agg: dict = {}
    for _, sub in _groups(df, session_col):
        lab = sub[label_col].to_numpy()
        vals, lens = _runs(lab)
        for label_val in np.unique(lab):
            mask = vals == label_val
            rl = lens[mask]
            if len(rl) == 0:
                continue
            cur = agg.setdefault(label_val, {"max_run": 0, "total": 0, "n_runs": 0})
            cur["max_run"] = max(cur["max_run"], int(rl.max()))
            cur["total"] += int(rl.sum())
            cur["n_runs"] += int(len(rl))
    return agg


def simulate_survival(df: pd.DataFrame, label_col: str, session_col: str | None,
                      window: int, shift: int):
    """Strict-pure simulation. Returns (total, pure, mixed, per_label_counts)."""
    counts = {lab: 0 for lab in sorted(df[label_col].unique())}
    total = 0
    for _, sub in _groups(df, session_col):
        lab = sub[label_col].to_numpy()
        if len(lab) < window:
            continue
        for start in range(0, len(lab) - window + 1, shift):
            total += 1
            chunk = lab[start:start + window]
            if (chunk == chunk[0]).all():
                counts[chunk[0]] += 1
    pure = sum(counts.values())
    return total, pure, total - pure, counts


WINDOW_IMBALANCE_RATIO = 3


def window_yield_findings(df: pd.DataFrame, label_col: str, session_col: str | None, window: int):
    """Per-class INDEPENDENT (non-overlapping, shift=window) pure-window yield via simulate_survival:
    an INFO with the counts (the windowed training-set composition B7's discard hands off, databuilder-020)
    and, when the survivors' counts differ by >= WINDOW_IMBALANCE_RATIO, an ADVISORY. The imbalance is
    measured over survivors (yield >= 1): a ratio needs a nonzero denominator, and a zero-yield class is
    already shown in the INFO census -- a class reaches zero windows either by max_run < window
    (min_run_ok's class_run_below_window) or by a grid-misaligned run in [window, 2*window) that min_run_ok
    does not catch; the census's 0 is the honest disclosure for both, and simulate_survival's fixed grid is
    only an approximation of the platform's window placement (VERIFY_NOTE), so no hard survivor->zero
    finding is added."""
    total, pure, mixed, per_class = simulate_survival(df, label_col, session_col, window, window)
    counts = {int(k): int(v) for k, v in per_class.items()}
    findings: list[Finding] = [Finding(
        Group.INFO, Severity.INFO, "window_class_yield",
        f"After non-overlapping windowing (window {window}), each class yields these pure (single-label) "
        f"windows: {counts}. This is the per-class training-set size at the recommended training shift "
        f"(shift = window); a smaller sliding shift produces more, overlapping windows. A class with few "
        f"windows trains weakly even with many rows. {VERIFY_NOTE}",
        f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
        {"pure_windows": counts, "total_windows": int(total)})]
    nz = {k: v for k, v in counts.items() if v > 0}
    if nz and max(nz.values()) / min(nz.values()) >= WINDOW_IMBALANCE_RATIO:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.ADVISORY, "window_class_imbalance",
            f"The windowed training set is imbalanced: pure windows per class {nz} differ by more than "
            f"{WINDOW_IMBALANCE_RATIO}x. Window counts can be imbalanced even when row counts are balanced, "
            f"because a class recorded in short or fragmented runs yields fewer clean windows. Record the "
            f"weak class in longer continuous runs, or read results with Balanced Accuracy. {VERIFY_NOTE}",
            f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
            {"pure_windows": nz, "ratio": round(max(nz.values()) / min(nz.values()), 1)}))
    return findings


def _label_key(label_val):
    """Best-effort integer for a label min_run_ok formats, never raising and always JSON-safe.
    min_run_ok is gated to int-coercible classification labels, but a raw cell may be a string like
    '0.0' (int-coercible via validate._label_ints, reachable when min_run_ok is called directly on
    str labels) that a bare int() rejects. Integral numerics/bools and integral-valued strings collapse
    to int (byte-identical to the old int() on the int64 path); anything else becomes a display string
    (never a raw numpy scalar, which json.dumps cannot serialise). Mirrors the intent of
    scripts/diagnostics/window_survival_sim._fmt_label -- a deliberate second copy, since production
    must not import a diagnostics script."""
    if isinstance(label_val, (bool, np.bool_)):
        return int(label_val)
    if isinstance(label_val, (int, np.integer)):
        return int(label_val)
    if isinstance(label_val, (float, np.floating)):
        if np.isfinite(label_val) and float(label_val).is_integer():
            return int(label_val)
        return str(label_val)
    try:
        if float(label_val).is_integer():
            return int(float(label_val))
    except (TypeError, ValueError):
        pass
    return str(label_val)


def min_run_ok(df: pd.DataFrame, label_col: str, session_col: str | None, window: int):
    """Findings for classes whose longest contiguous run < window (they would yield zero pure windows)."""
    findings: list[Finding] = []
    agg = run_lengths(df, label_col, session_col)
    for label_val, stats in sorted(agg.items()):
        if stats["max_run"] < window:
            key = _label_key(label_val)
            findings.append(Finding(
                Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "class_run_below_window",
                f"Class {key}'s longest unbroken run is {stats['max_run']} rows, shorter than "
                f"the window ({window}); it would produce zero clean windows and silently disappear. "
                f"{VERIFY_NOTE}",
                f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
                {"label": key, "max_run": stats["max_run"], "window": window}))
    return findings


def short_session_findings(df: pd.DataFrame, session_col: str | None, window: int):
    findings: list[Finding] = []
    if not (session_col and session_col in df.columns):
        return findings
    for sid, sub in df.groupby(session_col, sort=False):
        if len(sub) < window:
            findings.append(Finding(
                Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "session_below_window",
                f"Session {sid} has {len(sub)} rows, fewer than the window ({window}); the platform drops "
                f"sessions shorter than the window. {VERIFY_NOTE}",
                f"{SIGNAL_PROC}#why-this-matters-to-the-data-builder",
                {"session": str(sid), "rows": int(len(sub)), "window": window}))
    return findings

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


def min_run_ok(df: pd.DataFrame, label_col: str, session_col: str | None, window: int):
    """Findings for classes whose longest contiguous run < window (they would yield zero pure windows)."""
    findings: list[Finding] = []
    agg = run_lengths(df, label_col, session_col)
    for label_val, stats in sorted(agg.items()):
        if stats["max_run"] < window:
            findings.append(Finding(
                Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "class_run_below_window",
                f"Class {int(label_val)}'s longest unbroken run is {stats['max_run']} rows, shorter than "
                f"the window ({window}); it would produce zero clean windows and silently disappear. "
                f"{VERIFY_NOTE}",
                f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
                {"label": int(label_val), "max_run": stats["max_run"], "window": window}))
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

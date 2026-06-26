"""resample — bring a dataset onto a single common sampling rate (domain P-04).

Resamples per session AND per contiguous same-label run, so it never interpolates across a class
boundary (which could shorten a minority class below the window and kill it — databuilder-001 [gate]).
numpy.interp only; requires strictly increasing timestamps per group (duplicate/decreasing -> finding,
no interpolation). Assumes the time column is in `time_unit` (default seconds).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"
UNIT_PER_SECOND = {"s": 1.0, "ms": 1e3, "us": 1e6}


def _contiguous_runs(labels: np.ndarray):
    if len(labels) == 0:
        return []
    breaks = np.where(labels[1:] != labels[:-1])[0] + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(labels)]
    return list(zip(starts, ends))


def resample_to_rate(df: pd.DataFrame, time_col: str | None, target_hz: float, sensor_cols,
                     label_col: str, session_col: str | None, time_unit: str = "s"):
    """Return (df, findings). No-op (+finding) if time_col absent."""
    findings: list[Finding] = []
    if not time_col or time_col not in df.columns:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.FIX_REQUIRED, "no_time_column_for_resample",
            "Cannot resample without a time column. Add a numeric epoch/relative time column, or record "
            "the sampling rate and ensure it is already uniform.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {}))
        return df, findings

    # Consistent output column set: sensor + label + session + time, in the original order. Every output
    # part (resampled AND raw) is projected onto exactly these columns, so pd.concat never NaN-fills an
    # undeclared column (the silent-corruption path the impl gate found).
    declared = set(sensor_cols) | {label_col, time_col}
    if session_col and session_col in df.columns:
        declared.add(session_col)
    keep_cols = [c for c in df.columns if c in declared]
    extra = [c for c in df.columns if c not in declared]
    if extra:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.INFO, "columns_dropped_on_resample",
            f"Columns {extra} are not declared sensor/label/session/time columns and were dropped while "
            f"resampling. Add them to the profile if they should be kept.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {"dropped": extra}))

    step = UNIT_PER_SECOND[time_unit] / float(target_hz)
    out_parts = []
    groups = list(df.groupby(session_col, sort=False)) if (
        session_col and session_col in df.columns) else [(None, df)]

    for sid, sub in groups:
        sub = sub.reset_index(drop=True)
        labels = sub[label_col].to_numpy()
        for s, e in _contiguous_runs(labels):
            run = sub.iloc[s:e]
            t = pd.to_numeric(run[time_col], errors="coerce").to_numpy(dtype=np.float64)
            if len(t) < 2 or np.any(np.diff(t) <= 0):
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.FIX_REQUIRED, "nonmonotonic_timestamps",
                    f"A run in session {sid} has duplicate or non-increasing timestamps; resampling would "
                    f"produce garbage. Sort/clean the timestamps first. That run was left at its ORIGINAL "
                    f"rate, so the file stays mixed-rate until the timestamps are fixed.",
                    f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {"session": str(sid)}))
                out_parts.append(run[keep_cols])
                continue
            n_new = int(np.floor((t[-1] - t[0]) / step)) + 1
            new_t = t[0] + step * np.arange(n_new)
            cols = {}
            for ax in sensor_cols:
                if ax in run.columns:
                    y = pd.to_numeric(run[ax], errors="coerce").to_numpy(dtype=np.float64)
                    cols[ax] = np.interp(new_t, t, y)
            cols[label_col] = np.full(n_new, labels[s])
            if session_col and session_col in df.columns:
                cols[session_col] = np.full(n_new, sid)
            cols[time_col] = new_t
            out_parts.append(pd.DataFrame(cols).reindex(columns=keep_cols))

    if not out_parts:
        return df, findings
    return pd.concat(out_parts, ignore_index=True)[keep_cols], findings

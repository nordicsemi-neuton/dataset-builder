"""center — float-safe per-class centering for discrete-gesture datasets (domain P-05).

Ports the VALIDATED algorithm from scripts/preprocessing/center_training_data.py (from field
experience): RMS envelope -> threshold segmentation -> strongest-sample-per-segment -> NMS dedup ->
window extraction with a peak-tolerance quality drop, with auto-work-axis per class. Sensor values are
sliced (rows), never cast — floats are preserved bit-for-bit (databuilder-003).

Gesture classes are centered (peak mid-window); continuous classes are trimmed to a window multiple; a
class in neither list is left untouched with a finding. Defaults match the reference tool.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity
from .profile import DatasetProfile

SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"
PRESET = "wiki/architecture/data-skill-preset-contract.md"

WORK_WINDOW_RATIO = 0.95   # internal detection window as a fraction of the platform window
THRESHOLD_COEF = 0.5       # segmentation threshold = THRESHOLD_COEF * mean(envelope)
PEAK_TOLERANCE = 10        # drop a window whose peak is farther than this from the middle
MAX_CLASSES_IN_MESSAGE = 8  # per-class clauses shown in the row-delta message; full ledger stays in data


def _envelope(axis: np.ndarray, work_window: int) -> np.ndarray:
    """RMS of the rolling min/max over work_window (matches the reference tool)."""
    if work_window < 1 or len(axis) <= work_window:
        return np.asarray([], dtype=np.float64)
    sw = np.lib.stride_tricks.sliding_window_view(axis, work_window)
    return np.sqrt(sw.min(axis=1) ** 2 + sw.max(axis=1) ** 2)


def _detect_segments(env: np.ndarray, work_window: int, threshold_coef: float):
    """(start, end) sample ranges for each above-threshold run (offset to signal coordinates)."""
    if len(env) == 0:
        return []
    threshold = threshold_coef * float(env.mean())
    segments, started, start = [], False, 0
    for i, v in enumerate(env, start=1):
        if v > threshold and not started:
            started, start = True, i
        elif v <= threshold and started:
            started = False
            segments.append((start + work_window // 2, i + work_window // 2))
    if started:
        segments.append((start + work_window // 2, len(env) + work_window // 2))
    return segments


def _dedup_centers(scored, min_distance: int):
    """NMS: keep the strongest centers, enforcing a minimum distance between them."""
    if min_distance <= 0:
        return sorted(c for c, _ in scored)
    kept = []
    for c, _ in sorted(scored, key=lambda x: x[1], reverse=True):
        if all(abs(c - k) >= min_distance for k in kept):
            kept.append(c)
    return sorted(kept)


def _center_one_axis(sub: pd.DataFrame, work_axis: str, window: int):
    """Center one class using one axis to detect peaks.

    Returns (centered_df_or_None, windows_kept, events_detected), where events_detected is the number
    of gesture events this axis resolved (above-threshold envelope runs, after the ≤1-sample filter
    and NMS de-duplication) and windows_kept is how many of those became clean windows. The two differ
    only when an event was dropped for landing off-centre or within half a window of an edge; at small
    windows no drop is reachable, so they coincide there (databuilder-014, domain P-18).
    """
    work_window = max(1, int(window * WORK_WINDOW_RATIO))
    axis = pd.to_numeric(sub[work_axis], errors="coerce").to_numpy(dtype=np.float64)
    axis = axis - np.nanmean(axis)
    abs_peak = np.abs(axis)

    env = _envelope(axis, work_window)
    segments = _detect_segments(env, work_window, THRESHOLD_COEF)

    candidates = []
    for s, e in segments:
        s, e = max(0, s), min(len(abs_peak), e)
        if e - s <= 1:
            continue
        local_peak = int(s + np.argmax(abs_peak[s:e]))
        candidates.append((local_peak, float(abs_peak[local_peak])))

    centers = _dedup_centers(candidates, min_distance=window)
    events_detected = len(centers)

    half = window // 2
    windows = []
    for c in centers:
        left, right = c - half, c - half + window
        if left < 0 or right > len(sub):
            continue
        if PEAK_TOLERANCE >= 0:                          # QC: the peak must sit near the middle
            wpeak = int(np.argmax(abs_peak[left:right]))
            if abs(wpeak - half) > PEAK_TOLERANCE:
                continue
        windows.append(sub.iloc[left:right])             # row slice -> floats preserved
    if not windows:
        return None, 0, events_detected
    return pd.concat(windows, ignore_index=True), len(windows), events_detected


def _center_gesture(sub: pd.DataFrame, sensor_cols, window: int):
    """Auto-work-axis: keep the axis yielding the most windows; report ITS detected/kept counts.

    Returns (centered_df_or_None, windows_kept, events_detected). The counts come from the winning
    axis only -- the one whose windows are actually returned -- so events_detected >= windows_kept
    holds and both describe the same data the caller receives (databuilder-014).
    """
    best, best_kept, best_detected = None, -1, 0
    for ax in sensor_cols:
        if ax not in sub.columns:
            continue
        out, kept, detected = _center_one_axis(sub, ax, window)
        if kept > best_kept:
            best, best_kept, best_detected = out, kept, detected
    return best, max(0, best_kept), max(0, best_detected)


def center_per_class(df: pd.DataFrame, profile: DatasetProfile, window: int):
    """Return (df, findings). Reorders rows into class-blocks (gesture-centered / continuous-trimmed).

    Centering re-orders rows and extracts non-contiguous windows, so any time/session column would be
    scrambled (non-monotonic). Like the validated reference tool, the output keeps ONLY sensor axes +
    the label; time/session columns are dropped (the platform windows fixed-rate rows by position).

    Requires a positive int window. Centering is a windowing operation; there is no meaningful centering
    without a window, so a None/<1 window is a contract violation, raised loudly rather than crashing
    cryptically deep in the arithmetic. pipeline.prep never reaches here with a bad window (it skips
    centering under SP off, and SP-on always resolves window >= 1) -- this guards the module for any
    other caller (databuilder-016, P-21).
    """
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError(f"center_per_class requires a positive int window, got {window!r}")
    findings: list[Finding] = []
    label_col = profile.label_column
    gesture = set(profile.gesture_classes)
    continuous = set(profile.continuous_classes)
    keep_cols = [c for c in df.columns if c in (set(profile.sensor_columns) | {label_col})]
    dropped = [c for c in df.columns if c not in keep_cols]
    if dropped:
        findings.append(Finding(
            Group.INFO, Severity.INFO, "centering_dropped_columns",
            f"Centering re-orders rows, so the {dropped} column(s) (time/session) were dropped from the "
            f"centered file — they would otherwise be non-monotonic. The platform windows fixed-rate rows "
            f"by position, so a time column is not needed after centering.",
            f"{SIGNAL_PROC}#why-this-matters-to-the-data-builder", {"dropped": dropped}))
    df = df[keep_cols + dropped]  # keep all for the per-class slicing below; project at the end
    parts = []
    ledger = []  # one entry per class: rows in, rows out, events -- announce the discard, then quantify it (P-18)

    for cls in sorted(df[label_col].unique()):
        sub = df[df[label_col] == cls].reset_index(drop=True)
        c = int(cls)
        rows_in = len(sub)
        if c in continuous:
            keep = (len(sub) // window) * window
            if keep == 0:
                findings.append(Finding(
                    Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "class_too_short_to_trim",
                    f"Continuous class {c} has {len(sub)} rows, fewer than the window ({window}); nothing "
                    f"to keep after trimming to a window multiple.",
                    f"{SIGNAL_PROC}#why-this-matters-to-the-data-builder", {"label": c, "rows": len(sub)}))
            else:
                parts.append(sub.iloc[:keep])
            ledger.append({"label": c, "kind": "continuous", "rows_in": rows_in,
                           "rows_out": keep, "events_detected": None})
        elif c in gesture:
            windows, kept, detected = _center_gesture(sub, profile.sensor_columns, window)
            if windows is None or kept == 0:
                findings.append(Finding(
                    Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "no_centered_windows",
                    f"Gesture class {c} produced no centered windows (too short, weak peaks, or peaks not "
                    f"landing mid-window at window {window}); it would have no clean samples. Try a "
                    f"different window or recollect sharper gestures.",
                    f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
                    {"label": c, "rows": len(sub)}))
                rows_out = 0
            else:
                parts.append(windows)
                rows_out = len(windows)
            ledger.append({"label": c, "kind": "gesture", "rows_in": rows_in,
                           "rows_out": rows_out, "events_detected": detected})
        else:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.FIX_REQUIRED, "class_not_partitioned",
                f"Class {c} is in neither gesture_classes nor continuous_classes in the profile, so the "
                f"tool does not know whether to center or trim it; it was left untouched. Add it to one list.",
                f"{PRESET}#invariants-the-load-bearing-contract", {"label": c}))
            parts.append(sub)
            ledger.append({"label": c, "kind": "unpartitioned", "rows_in": rows_in,
                           "rows_out": rows_in, "events_detected": None})

    findings += _row_delta_findings(ledger, window)

    if not parts:
        return df[keep_cols].iloc[0:0].copy(), findings
    return pd.concat(parts, ignore_index=True)[keep_cols], findings


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _class_clause(e: dict) -> str:
    pct = e["discarded_percent"]
    head = f"class {e['label']}: {e['rows_in']} -> {e['rows_out']} rows ({pct}% discarded; "
    if e["kind"] == "gesture":
        return head + _plural(e["events_detected"], "gesture event") + " found)"
    if e["kind"] == "continuous":
        tail = "continuous, trimmed to whole windows" if e["rows_out"] else \
            "continuous, too short to fill one window"
        return head + tail + ")"
    return head + "left untouched)"


def _row_delta_findings(ledger, window: int):
    """One INFO stating rows in, rows out and gesture events per class (domain P-18).

    Verdict-neutral by design: centering legitimately discards most of a sparse gesture recording, so a
    row-discard fraction is not a fault signal. Total loss is already WILL_LOSE_DATA; a thin or
    imbalanced result is caught by validate on the centered frame; event yield is B8's concern. This
    finding only makes the discard visible and quantified, which is what P-18 asks for (databuilder-014).
    """
    for e in ledger:
        e["discarded_percent"] = round(100.0 * (e["rows_in"] - e["rows_out"]) / e["rows_in"], 1) \
            if e["rows_in"] else 0.0
    if not ledger:
        return []
    rows_in = sum(e["rows_in"] for e in ledger)
    rows_out = sum(e["rows_out"] for e in ledger)
    if rows_in == 0:
        return []
    pct = round(100.0 * (rows_in - rows_out) / rows_in, 1)

    shown = sorted(ledger, key=lambda e: (-e["discarded_percent"], e["label"]))[:MAX_CLASSES_IN_MESSAGE]
    detail = "; ".join(_class_clause(e) for e in shown)
    hidden = len(ledger) - len(shown)
    if hidden:
        noun = "class" if hidden == 1 else "classes"
        detail += f"; and {hidden} more {noun} — see this finding's data"

    if rows_out == 0:
        lead = (f"Centering produced no rows at all: {rows_in} rows entering centering, 0 rows out at "
                f"window {window}. The findings above say which classes were lost and why.")
    elif any(e["kind"] == "gesture" for e in ledger):
        lead = (f"Centering keeps one window per detected gesture and discards what lies between events, "
                f"so the row count drops by design: {rows_in} rows entering centering, {rows_out} rows "
                f"out ({pct}% discarded) at window {window}.")
    else:
        # No gesture class in the frame: each class was trimmed to a whole window multiple or left
        # untouched (the per-class detail says which). Keep the lead neutral so it is true either way.
        lead = (f"Centering kept {rows_out} of {rows_in} rows ({pct}% discarded) at window {window}.")

    return [Finding(
        Group.INFO, Severity.INFO, "centering_rows_discarded",
        f"{lead} Per class — {detail}.",
        f"{SIGNAL_PROC}#why-this-matters-to-the-data-builder",
        {"rows_in": rows_in, "rows_out": rows_out, "discarded_percent": pct, "window": window,
         "per_class": ledger})]

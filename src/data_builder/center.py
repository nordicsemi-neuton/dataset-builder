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
    """Center one class using one axis to detect peaks. Returns (centered_df_or_None, kept_count)."""
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

    half = window // 2
    windows, dropped = [], 0
    for c in _dedup_centers(candidates, min_distance=window):
        left, right = c - half, c - half + window
        if left < 0 or right > len(sub):
            dropped += 1
            continue
        if PEAK_TOLERANCE >= 0:                          # QC: the peak must sit near the middle
            wpeak = int(np.argmax(abs_peak[left:right]))
            if abs(wpeak - half) > PEAK_TOLERANCE:
                dropped += 1
                continue
        windows.append(sub.iloc[left:right])             # row slice -> floats preserved
    if not windows:
        return None, 0
    return pd.concat(windows, ignore_index=True), len(windows)


def _center_gesture(sub: pd.DataFrame, sensor_cols, window: int):
    """Auto-work-axis: try every sensor axis, keep the one yielding the most kept windows."""
    best, best_kept = None, -1
    for ax in sensor_cols:
        if ax not in sub.columns:
            continue
        out, kept = _center_one_axis(sub, ax, window)
        if kept > best_kept:
            best, best_kept = out, kept
    return best


def center_per_class(df: pd.DataFrame, profile: DatasetProfile, window: int):
    """Return (df, findings). Reorders rows into class-blocks (gesture-centered / continuous-trimmed).

    Centering re-orders rows and extracts non-contiguous windows, so any time/session column would be
    scrambled (non-monotonic). Like the validated reference tool, the output keeps ONLY sensor axes +
    the label; time/session columns are dropped (the platform windows fixed-rate rows by position).
    """
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

    for cls in sorted(df[label_col].unique()):
        sub = df[df[label_col] == cls].reset_index(drop=True)
        c = int(cls)
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
        elif c in gesture:
            windows = _center_gesture(sub, profile.sensor_columns, window)
            if windows is None or len(windows) == 0:
                findings.append(Finding(
                    Group.SILENT_LOSS, Severity.WILL_LOSE_DATA, "no_centered_windows",
                    f"Gesture class {c} produced no centered windows (too short, weak peaks, or peaks not "
                    f"landing mid-window at window {window}); it would have no clean samples. Try a "
                    f"different window or recollect sharper gestures.",
                    f"{SIGNAL_PROC}#observed-in-practice-field-scenarios--not-documented-platform-rules",
                    {"label": c, "rows": len(sub)}))
            else:
                parts.append(windows)
        else:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.FIX_REQUIRED, "class_not_partitioned",
                f"Class {c} is in neither gesture_classes nor continuous_classes in the profile, so the "
                f"tool does not know whether to center or trim it; it was left untouched. Add it to one list.",
                f"{PRESET}#invariants-the-load-bearing-contract", {"label": c}))
            parts.append(sub)

    if not parts:
        return df[keep_cols].iloc[0:0].copy(), findings
    return pd.concat(parts, ignore_index=True)[keep_cols], findings

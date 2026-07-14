"""resample — bring a dataset onto a single common sampling rate (domain P-04, P-14).

Resamples per session AND per contiguous same-label run, so it never interpolates across a class
boundary (which could shorten a minority class below the window and kill it — databuilder-001 [gate]).

Direction is decided once per session from the measured source rate (1/median(diff timestamps), robust
to jitter — never the nominal rate). Upsampling and near-equal ("no-op") stay on numpy.interp. DOWNSAMPLING
is anti-aliased: interpolate onto a uniform grid at the source rate, then scipy.signal.resample_poly with
padtype='line' (a plain decimation / bare numpy.interp onto a coarser grid ALIASES — databuilder-008).
scipy is imported lazily inside the downsample path only (ADR-0003); if it is missing, or a run is too
short to filter cleanly, the downsample REFUSES (FIX_REQUIRED) rather than shipping aliased/distorted data.
Assumes the time column is in `time_unit` (default seconds).
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"
UNIT_PER_SECOND = {"s": 1.0, "ms": 1e3, "us": 1e6}

NOOP_TOL = 0.02      # |target-src|/src at or below this -> pass-through re-grid, no anti-alias filter
MAX_DENOM = 256      # cap on the rational up/down denominator (jittery floats -> bounded FIR, no blow-up)
MAX_UPDOWN = 256     # hard cap on max(up, down) (safety net alongside MAX_DENOM)
FIR_HALF_TAPS = 10   # scipy.signal.resample_poly default half-length factor: len(h)=2*10*max(up,down)+1
GUARD_FACTOR = 3     # a downsampled run must hold >= GUARD_FACTOR * FIR-length (in source samples)
GAP_FACTOR = 4.0     # a diff greater than GAP_FACTOR * median step counts as a real gap (dropout)


def _contiguous_runs(labels: np.ndarray):
    if len(labels) == 0:
        return []
    breaks = np.where(labels[1:] != labels[:-1])[0] + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(labels)]
    return list(zip(starts, ends))


def _session_src_hz(t_all: np.ndarray, unit: float) -> float:
    """Measured source rate for a whole session: unit / median(positive diffs). NaN if undeterminable.

    No sorting: on a session that concatenates two recordings (reset clocks), sorting would interleave
    their timestamps and halve the median step (→ a spurious 2x rate). The single negative/boundary diff
    between concatenated recordings is dropped by the d>0 filter; per-run monotonicity is checked separately.
    """
    d = np.diff(t_all)
    d = d[d > 0]
    if len(d) == 0:
        return float("nan")
    return unit / float(np.median(d))


def _direction(src_hz: float, target_hz: float) -> str:
    """'down' only when target is meaningfully below the measured source; else 'up_or_noop' (linear regrid)."""
    if not np.isfinite(src_hz) or src_hz <= 0:
        return "up_or_noop"  # cannot measure -> keep the pre-existing linear behaviour (no scipy)
    if abs(target_hz - src_hz) / src_hz <= NOOP_TOL:
        return "up_or_noop"
    return "down" if target_hz < src_hz else "up_or_noop"


def _regrid_linear(run, t, target_hz, unit, sensor_cols, label_col, label, has_session, session_col, sid,
                   time_col, keep_cols):
    """Upsample / no-op / unmeasurable: linear interp onto a uniform target grid (the pre-existing path)."""
    step = unit / float(target_hz)
    n_new = int(np.floor((t[-1] - t[0]) / step)) + 1
    new_t = t[0] + step * np.arange(n_new)
    cols = {}
    for ax in sensor_cols:
        if ax in run.columns:
            y = pd.to_numeric(run[ax], errors="coerce").to_numpy(dtype=np.float64)
            cols[ax] = np.interp(new_t, t, y)
    cols[label_col] = np.full(n_new, label)
    if has_session:
        cols[session_col] = np.full(n_new, sid)
    cols[time_col] = new_t
    return pd.DataFrame(cols).reindex(columns=keep_cols)


def _downsample_run(run, t, up, down, src_hz, target_hz, unit, sensor_cols, label_col, label,
                    has_session, session_col, sid, time_col, keep_cols):
    """Anti-aliased downsample of one run. Returns (part_df_or_None, findings). None => refused."""
    findings: list[Finding] = []
    # Ratio out of the supported range (target far below source -> Fraction rounds up to 0, or an
    # over-cap factor): refuse cleanly, never divide by up=0 or hand resample_poly a zero factor.
    if up < 1 or max(up, down) > MAX_UPDOWN:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.FIX_REQUIRED, "downsample_run_too_short",
            f"Class {int(label)}: target {target_hz:.1f} Hz is too far below the source ~{src_hz:.1f} Hz to "
            f"resample cleanly (rate ratio out of the supported range). Choose a target rate closer to the "
            f"source, or downsample in stages.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder",
            {"class": int(label), "src_hz": round(float(src_hz), 2), "target_hz": float(target_hz)}))
        return None, findings
    fir_taps = 2 * FIR_HALF_TAPS * max(up, down) + 1
    min_samples = int(np.ceil(GUARD_FACTOR * fir_taps / up))
    if len(t) < min_samples:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.FIX_REQUIRED, "downsample_run_too_short",
            f"Class {int(label)} has a run of {len(t)} samples but needs at least {min_samples} to "
            f"downsample from ~{src_hz:.1f} Hz to {target_hz:.1f} Hz without distortion. Record that class "
            f"in longer runs, exclude it, or choose a target rate closer to the source.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder",
            {"class": int(label), "has": int(len(t)), "needs": int(min_samples)}))
        return None, findings

    try:
        from scipy import signal as _sig  # type: ignore  # scipy ships no type stubs
    except ImportError:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.FIX_REQUIRED, "scipy_required_for_downsample",
            "Downsampling needs the scipy library for the anti-alias filter, but scipy is not installed. "
            "Install scipy, or choose a target rate at or above the recording's rate (upsampling needs no "
            "filter). The tool will not downsample without anti-aliasing, because that silently distorts "
            "the signal.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {}))
        return None, findings

    # (a) uniform grid at the SOURCE rate (handles jitter) -> (b) anti-alias + decimate.
    src_step = unit / src_hz
    n_src = int(np.floor((t[-1] - t[0]) / src_step)) + 1
    src_t = t[0] + src_step * np.arange(n_src)
    achieved_hz = src_hz * up / down
    out_step = unit / achieved_hz
    cols = {}
    n_out = 0
    for ax in sensor_cols:
        if ax in run.columns:
            y = pd.to_numeric(run[ax], errors="coerce").to_numpy(dtype=np.float64)
            y_uniform = np.interp(src_t, t, y)
            y_ds = _sig.resample_poly(y_uniform, up, down, padtype="line")
            cols[ax] = y_ds
            n_out = len(y_ds)
    if n_out == 0:
        return None, findings
    new_t = t[0] + out_step * np.arange(n_out)
    cols[label_col] = np.full(n_out, label)
    if has_session:
        cols[session_col] = np.full(n_out, sid)
    cols[time_col] = new_t
    return pd.DataFrame(cols).reindex(columns=keep_cols), findings


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
    has_session = bool(session_col) and session_col in df.columns
    if has_session:
        declared.add(session_col)
    keep_cols = [c for c in df.columns if c in declared]
    extra = [c for c in df.columns if c not in declared]
    if extra:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.INFO, "columns_dropped_on_resample",
            f"Columns {extra} are not declared sensor/label/session/time columns and were dropped while "
            f"resampling. Add them to the profile if they should be kept.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {"dropped": extra}))

    unit = UNIT_PER_SECOND[time_unit]
    out_parts = []
    groups = list(df.groupby(session_col, sort=False)) if has_session else [(None, df)]

    for sid, sub in groups:
        sub = sub.reset_index(drop=True)
        t_all = pd.to_numeric(sub[time_col], errors="coerce").to_numpy(dtype=np.float64)
        src_hz = _session_src_hz(t_all, unit)
        direction = _direction(src_hz, target_hz)
        up, down = 1, 1
        if direction == "down":
            frac = Fraction(target_hz / src_hz).limit_denominator(MAX_DENOM)
            up, down = frac.numerator, frac.denominator
            if up >= down:  # rationalised ratio isn't actually a decimation -> no filter needed, treat as no-op
                direction = "up_or_noop"
                up, down = 1, 1

        labels = sub[label_col].to_numpy()
        session_resampled = False
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

            # Real dropout inside the run: interpolation would fabricate data across it, and on a downsample
            # the anti-alias filter then launders the fabrication -> block the write there (advisory otherwise).
            d = np.diff(t)
            med = float(np.median(d))
            if med > 0 and float(d.max()) > GAP_FACTOR * med:
                sev = Severity.FIX_REQUIRED if direction == "down" else Severity.ADVISORY
                findings.append(Finding(
                    Group.BAD_MODEL, sev, "large_gap_in_resampled_run",
                    f"Class {int(labels[s])} has a run with a timestamp gap ~{float(d.max()) / med:.0f}x the "
                    f"normal step; resampling interpolates across it, inventing data. Split the recording at "
                    f"the gap or drop that segment.",
                    f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder",
                    {"class": int(labels[s]), "gap": float(d.max()), "step": med}))

            if direction == "down":
                part, fnd = _downsample_run(run, t, up, down, src_hz, target_hz, unit, sensor_cols,
                                            label_col, labels[s], has_session, session_col, sid, time_col,
                                            keep_cols)
                findings += fnd
                if part is None:
                    out_parts.append(run[keep_cols])  # refused -> left at original rate (finding blocks write)
                else:
                    out_parts.append(part)
                    session_resampled = True
            else:
                out_parts.append(_regrid_linear(run, t, target_hz, unit, sensor_cols, label_col, labels[s],
                                                 has_session, session_col, sid, time_col, keep_cols))
                session_resampled = True

        if session_resampled and np.isfinite(src_hz):
            is_down = direction == "down"
            achieved = round(float(src_hz) * up / down, 4) if is_down else round(float(target_hz), 4)
            findings.append(Finding(
                Group.INFO, Severity.INFO, "resample_provenance",
                f"Session {sid}: measured ~{src_hz:.2f} Hz, resampled to {target_hz:.2f} Hz "
                f"({'downsample, anti-aliased' if is_down else 'upsample/regrid, linear'}).",
                f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder",
                {"session": str(sid), "measured_src_hz": round(float(src_hz), 4),
                 "target_hz": float(target_hz), "achieved_hz": achieved,
                 "direction": "down" if is_down else "up_or_noop",
                 "method": "resample_poly-antialias" if is_down else "linear-interp",
                 "up": int(up) if is_down else None, "down": int(down) if is_down else None,
                 "fir_taps": int(2 * FIR_HALF_TAPS * max(up, down) + 1) if is_down else None}))

    if not out_parts:
        return df, findings
    return pd.concat(out_parts, ignore_index=True)[keep_cols], findings

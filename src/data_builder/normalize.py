"""normalize — numeric repair, timestamp check, index-column detection.

Every path here FLAGS rather than silently corrupting: an empty/NA value or an unrepairable token
becomes a HARD-REJECT finding, never a silent NaN or a dropped row (databuilder-001 [gate]). Calendar
timestamps are flagged, never auto-converted (no format guessing).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"
SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"

# A backward timestamp step is a real reorder only when it exceeds this * the normal forward step;
# smaller backward steps are sub-step clock jitter, not a shuffle (databuilder-019).
ORDER_STEP_TOL = 1.0

NA_TOKENS = {"", "NA", "NAN", "N/A", "NULL", "NONE", "#N/A", "#NA", "NIL"}
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_INT64_MAX = 2 ** 63 - 1


def try_parse_number(token: str, allow_comma_decimal: bool = True):
    """Parse one raw cell. Returns (value, reason). value is int/float on success, None on failure;
    reason is None on success, else "empty_or_na" / "unrepairable"."""
    if token is None:
        return None, "empty_or_na"
    s = str(token).strip().strip('"').strip()
    if s == "" or s.upper() in NA_TOKENS:
        return None, "empty_or_na"

    has_comma, has_dot = "," in s, "." in s
    if has_comma and has_dot:
        core = s.replace(",", "")                 # comma = thousands sep, dot = decimal
    elif has_comma and not has_dot:
        parts = s.split(",")
        if allow_comma_decimal and len(parts) == 2 and len(parts[1]) != 3:
            core = s.replace(",", ".")            # decimal comma, e.g. "9,78"
        else:
            core = s.replace(",", "")             # thousands grouping, e.g. "1,234"
    else:
        core = s

    m = _NUM_RE.search(core)
    if not m:
        return None, "unrepairable"
    remainder = (core[:m.start()] + core[m.end():]).strip()
    if any(ch.isdigit() for ch in remainder):     # a second number / embedded digits -> ambiguous
        return None, "unrepairable"
    try:
        val = float(m.group(0))
    except ValueError:
        return None, "unrepairable"
    if val.is_integer():
        return int(val), None
    return val, None


def normalize_numeric(df: pd.DataFrame, cols, allow_comma_decimal: bool = True):
    """Repair the given (string) columns to numeric. Returns (df, findings). Unparseable / empty / NA
    values are flagged HARD-REJECT and left as NaN (prep refuses to write on hard-reject)."""
    df = df.copy()
    findings: list[Finding] = []
    for col in cols:
        if col not in df.columns:
            continue
        values, bad_examples, n_empty, n_unrep, integral = [], [], 0, 0, True
        for idx, raw in zip(df.index, df[col].to_numpy()):
            val, reason = try_parse_number(raw, allow_comma_decimal)
            if reason is None:
                values.append(val)
                # Only treat as integer-typed when it fits int64; a huge int (device-counter junk) is
                # widened to float64 so np.array(..., int64) never overflows.
                if not (isinstance(val, int) and not isinstance(val, bool)) or abs(val) > _INT64_MAX:
                    integral = False
            else:
                values.append(np.nan)
                integral = False
                if reason == "empty_or_na":
                    n_empty += 1
                else:
                    n_unrep += 1
                if len(bad_examples) < 5:
                    bad_examples.append({"row": int(idx), "value": str(raw)})
        if n_empty:
            findings.append(Finding(
                Group.HARD_REJECT, Severity.HARD_REJECT, "empty_or_na_value",
                f"Column '{col}' has {n_empty} empty / NA / NAN value(s). The platform requires all "
                f"values numeric with no blanks; fix or remove these rows (do not leave them blank).",
                f"{DATASET_REQ}#value-rules", {"column": col, "count": n_empty, "examples": bad_examples}))
        if n_unrep:
            findings.append(Finding(
                Group.HARD_REJECT, Severity.HARD_REJECT, "unrepairable_value",
                f"Column '{col}' has {n_unrep} value(s) that could not be reduced to a single number "
                f"(e.g. text, two numbers, or an ambiguous unit).",
                f"{DATASET_REQ}#value-rules", {"column": col, "count": n_unrep, "examples": bad_examples}))
        df[col] = np.array(values, dtype=np.int64) if (integral and not n_empty and not n_unrep) \
            else np.array(values, dtype=np.float64)
    return df, findings


def check_timestamps(series: pd.Series, col_name: str = "time"):
    """Flag calendar-string timestamps; never auto-convert. Numeric epoch/relative passes."""
    findings: list[Finding] = []
    bad = []
    for idx, raw in zip(series.index, series.to_numpy()):
        s = str(raw).strip().strip('"')
        if s == "":
            continue
        _, reason = try_parse_number(s, allow_comma_decimal=False)
        if reason == "unrepairable":      # non-numeric -> looks like a calendar string
            if len(bad) < 5:
                bad.append({"row": int(idx), "value": s})
    if bad:
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "calendar_timestamp",
            f"Column '{col_name}' looks like calendar dates/times. Convert to epoch or relative numeric "
            f"timestamps before uploading (e.g. 10/18/2017 -> 1508284800). The tool will not guess the "
            f"format/timezone for you.",
            f"{DATASET_REQ}#value-rules", {"column": col_name, "examples": bad}))
    return findings


def check_time_order(df: pd.DataFrame, time_col: str | None, session_col: str | None = None,
                     source: str | None = None):
    """Flag rows whose timestamp goes backwards WITHIN one recording — a shuffled / mis-sorted row
    order the platform's row-order windowing cannot recover (databuilder-019).

    Called PER RECORDING: validate checks the one uploaded file (per session where a session column
    exists); prep checks each input file inside combine (passing source=the file name), so a legitimate
    concatenation seam (a new recording restarting its clock) is never seen and never flagged -- the
    exemption is exact, not heuristic. A backward step counts only when it exceeds the normal forward
    step (ORDER_STEP_TOL), so sub-step clock jitter is not a 'shuffle'; a run with no forward progress
    (reverse-sorted) is flagged wholesale. Non-numeric / calendar timestamps are check_timestamps'
    province and are ignored here (coerced to NaN, dropped)."""
    findings: list[Finding] = []
    if not (time_col and time_col in df.columns):
        return findings
    groups = df.groupby(session_col, sort=False) if (session_col and session_col in df.columns) \
        else [(None, df)]
    for sid, sub in groups:
        t = pd.to_numeric(sub[time_col], errors="coerce").to_numpy(dtype=np.float64)
        t = t[~np.isnan(t)]
        if len(t) < 2:
            continue
        d = np.diff(t)
        pos = d[d > 0]
        if len(pos) == 0:
            n_bad = int((d < 0).sum())                                   # no forward progress -> reverse
        else:
            n_bad = int((d < -ORDER_STEP_TOL * float(np.median(pos))).sum())
        if not n_bad:
            continue
        where = (f"Session {sid}" if sid is not None
                 else (f"Recording '{source}'" if source else "The recording"))
        data: dict = {"session": None if sid is None else str(sid), "out_of_order_rows": n_bad}
        if source:
            data["source"] = source
        findings.append(Finding(
            Group.BAD_MODEL, Severity.FIX_REQUIRED, "timestamps_out_of_order",
            f"{where} has {n_bad} place(s) where the timestamp jumps backwards mid-recording (rows out "
            f"of time order). The platform windows in row order, so out-of-order rows build "
            f"temporally-incoherent windows. Sort this recording by time (or confirm the rows are "
            f"already in acquisition order); if it is really several recordings, give each its own "
            f"session (a session column) so the platform does not window across the boundary.",
            f"{SIGNAL_PROC}#why-this-matters-to-the-data-builder", data))
    return findings


def find_index_column(df: pd.DataFrame, profile_names: set[str]):
    """Detect a forbidden row-index column. Returns (index_col_or_None, findings).

    Auto-flags only the unambiguous strict 0..n-1 case; a monotonic integer column that is NOT 0..n-1
    is reported for human confirmation, never auto-dropped.
    """
    findings: list[Finding] = []
    n = len(df)
    index_col = None
    for col in df.columns:
        if col in profile_names:
            continue
        vals = []
        ok = True
        for raw in df[col].to_numpy():
            v, reason = try_parse_number(raw, allow_comma_decimal=False)
            if reason is not None or not (isinstance(v, int) and not isinstance(v, bool)):
                ok = False
                break
            vals.append(v)
        if not ok:
            continue
        arr = np.array(vals, dtype=np.int64)
        if n > 0 and np.array_equal(arr, np.arange(n)):
            index_col = col
            findings.append(Finding(
                Group.HARD_REJECT, Severity.HARD_REJECT, "index_column_present",
                f"Column '{col}' is a 0..N-1 row index. The platform requires the row/line number to be "
                f"excluded; it will be dropped from the upload file.",
                f"{DATASET_REQ}#value-rules", {"column": col}))
        elif n > 2 and (np.all(np.diff(arr) == 1)):
            findings.append(Finding(
                Group.BAD_MODEL, Severity.INFO, "possible_index_column",
                f"Column '{col}' is a strictly increasing integer counter; if it is a row index, remove "
                f"it (not auto-dropped because it could be a real sensor counter).",
                f"{DATASET_REQ}#value-rules", {"column": col}))
    return index_col, findings

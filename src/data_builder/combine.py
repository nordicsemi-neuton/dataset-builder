"""combine — structural concatenation of several recordings into one single-header frame.

Structural ONLY (no value-dependent ops): read each file, drop a per-file index column, optional
bounded edge-trim in SAMPLES, and ABORT on any column-set/order mismatch — never concat-then-report,
which would let pandas NaN-fill or mis-align a sensor axis (databuilder-001 [gate]).
"""
from __future__ import annotations

import pandas as pd

from . import csv_io
from .findings import Finding, Group, Severity
from .normalize import find_index_column
from .profile import DatasetProfile


class CombineError(ValueError):
    """Files cannot be safely combined (mismatched columns)."""


def _profile_names(profile: DatasetProfile) -> set[str]:
    names = {profile.label_column, *profile.sensor_columns}
    if profile.session_column:
        names.add(profile.session_column)
    if profile.time_column:
        names.add(profile.time_column)
    return names


def combine_recordings(paths, sep_char: str, encoding: str, profile: DatasetProfile,
                       trim_head: int = 0, trim_tail: int = 0):
    """Return (df, findings). Raises CombineError on a column mismatch across files."""
    findings: list[Finding] = []
    frames = []
    ref_cols = None
    names = _profile_names(profile)

    for path in paths:
        df, fnd = csv_io.read_table(path, sep_char, encoding)
        findings.extend(fnd)
        if df is None:
            raise CombineError(f"file {path!r} could not be parsed; cannot combine")

        index_col, idx_findings = find_index_column(df, names)
        findings.extend(idx_findings)
        if index_col is not None:
            df = df.drop(columns=[index_col])

        cols = list(df.columns)
        if ref_cols is None:
            ref_cols = cols
        elif cols != ref_cols:
            raise CombineError(
                f"file {path!r} has columns {cols} but the first file has {ref_cols}; column sets/order "
                f"must be identical to combine safely (mis-aligned columns would corrupt the data)")

        n = len(df)
        if trim_head or trim_tail:
            if trim_head + trim_tail >= n:
                findings.append(Finding(
                    Group.BAD_MODEL, Severity.INFO, "trim_skipped",
                    f"Edge trim ({trim_head}+{trim_tail}) would empty {path!r} ({n} rows); skipped.",
                    "wiki/architecture/platform-dataset-requirements.md#cleaning-expectations-pre-upload",
                    {"path": str(path), "rows": n}))
            else:
                df = df.iloc[trim_head: n - trim_tail].reset_index(drop=True)
        frames.append(df)

    if not frames:
        raise CombineError("no input files provided")
    combined = pd.concat(frames, ignore_index=True)
    return combined, findings

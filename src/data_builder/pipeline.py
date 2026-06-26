"""pipeline — prep(): assemble raw recordings into one upload-ready CSV, gated by validation.

Order: combine(structural) -> normalize sensors -> relabel -> [resample] -> [center] -> validate ->
write. Refuses to write on FIX_REQUIRED or WILL_LOSE_DATA unless write_anyway=True (databuilder-001
[gate]). Keeps the reconciled label-column name and reports the desktop-runner flags rather than
silently renaming.
"""
from __future__ import annotations

import json
import os

import pandas as pd

from . import csv_io, validate
from .combine import combine_recordings, CombineError
from .findings import Finding, Group, Severity, make_report
from .normalize import normalize_numeric
from .profile import DatasetProfile
from .relabel import relabel_contiguous
from .resample import resample_to_rate
from .center import center_per_class

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"
DEPLOY = "wiki/architecture/platform-deployment-inference.md"
_SKIP_INTAKE = {"mixed_line_endings", "cr_only_line_endings"}  # prep re-normalises line endings on write


def _dict_path(out_path: str) -> str:
    base, _ = os.path.splitext(out_path)
    return base + "_dictionary.json"


def prep(input_paths, profile: DatasetProfile, out_path: str, window: int,
         do_center: bool | None = None, target_rate: float | None = None, write_anyway: bool = False,
         time_unit: str = "s"):
    """Return a result dict: {report, written, out_path, dictionary, dictionary_path}."""
    findings: list[Finding] = []

    # Intake scan per file (encoding for the reader; surface real blockers, skip line-ending noise prep fixes).
    encoding = "utf-8"
    for i, path in enumerate(input_paths):
        scan = csv_io.sniff_raw(path)
        if i == 0 and scan.encoding != "unknown":
            encoding = scan.encoding
        findings += [f for f in scan.findings if f.code not in _SKIP_INTAKE]

    # Combine (structural).
    try:
        df, fnd = combine_recordings(input_paths, profile.sep_char, encoding, profile)
    except CombineError as exc:
        findings.append(Finding(Group.HARD_REJECT, Severity.HARD_REJECT, "combine_failed",
                                str(exc), f"{DATASET_REQ}#combining-multiple-recordings"))
        return {"report": make_report(findings), "written": False, "out_path": out_path,
                "dictionary": None, "dictionary_path": None}
    findings += fnd

    if len(df) == 0:
        findings.append(Finding(Group.HARD_REJECT, Severity.HARD_REJECT, "empty_input",
                                "The combined input has no data rows.", f"{DATASET_REQ}#file-level-requirements"))
        return {"report": make_report(findings), "written": False, "out_path": out_path,
                "dictionary": None, "dictionary_path": None}

    # Repair sensor (and time) values.
    allow_comma_decimal = profile.separator != "comma"
    numeric_cols = list(profile.sensor_columns)
    if profile.time_column and profile.time_column in df.columns:
        numeric_cols.append(profile.time_column)
    df, fnd = normalize_numeric(df, numeric_cols, allow_comma_decimal)
    findings += fnd

    # Encode labels.
    df, dictionary, fnd = relabel_contiguous(df, profile.label_column, profile.class_map or None)
    findings += fnd

    # Resample (optional).
    if target_rate:
        df, fnd = resample_to_rate(df, profile.time_column, target_rate, profile.sensor_columns,
                                   profile.label_column, profile.session_column, time_unit)
        findings += fnd

    # Center / trim. Default-on for gesture datasets (classification profile that declares
    # gesture_classes); pass do_center=False (CLI --no-center) to skip.
    center_on = do_center if do_center is not None else (
        profile.is_classification and bool(profile.gesture_classes))
    if center_on:
        df, fnd = center_per_class(df, profile, window)
        findings += fnd

    # Validate the prepared frame (+ output file-name check).
    findings += validate.check_dataframe(df, profile, window, profile.frequency_domain, file_name=out_path)

    # Desktop-runner flags note (we keep the user's column names; tell them how to call the runner).
    flags = [f"-t {profile.label_column}"]
    if profile.session_column and profile.session_column in df.columns:  # centering may have dropped it
        flags.append(f"-sn {profile.session_column}")
    if profile.separator != "comma":
        flags.append(f"-d {profile.runner_delim_keyword}")
    findings.append(Finding(
        Group.INFO, Severity.INFO, "runner_flags",
        f"To validate locally with the desktop inference runner, call it with: {' '.join(flags)} "
        f"(it defaults to target='target', session='session', delimiter=comma).",
        f"{DEPLOY}#run-inference-on-desktop--the-csv-runner-contract-", {"flags": flags}))

    report = make_report(findings)
    blocking = report.verdict in ("FIX_REQUIRED", "WILL_LOSE_DATA")
    if blocking and not write_anyway:
        return {"report": report, "written": False, "out_path": out_path,
                "dictionary": dictionary, "dictionary_path": None}

    csv_io.write_table(df, out_path, sep_char=",", line_ending="\n")
    dpath = _dict_path(out_path)
    with open(dpath, "w", encoding="utf-8") as fh:
        json.dump(dictionary, fh, indent=2, sort_keys=True)
    return {"report": report, "written": True, "out_path": out_path,
            "dictionary": dictionary, "dictionary_path": dpath}

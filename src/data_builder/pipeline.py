"""pipeline — prep(): assemble raw recordings into one upload-ready CSV, gated by validation.

Order: combine(structural) -> target-present guard -> normalize sensors -> relabel (classification
and anomaly only) -> [resample] -> [center] -> validate -> write (+ reconcile a stale class
dictionary when this dataset has none). Refuses to write on FIX_REQUIRED or WILL_LOSE_DATA unless write_anyway=True (databuilder-001
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
TASK_TYPES = "wiki/discovery/platform-task-types.md"
SP_APPLICABILITY = "wiki/architecture/platform-signal-processing-applicability.md"
# _PREP_REPAIRS -- the authoritative record of every finding code where prep's report legitimately
# differs from validate's over the SAME input. validate inspects the RAW file; prep transforms it
# (combine -> normalize -> relabel -> [resample] -> [center]) then validates the PREPARED frame and
# adds its own transform-stage findings. So the two surfaces diverge BY DESIGN. This allowlist says
# why; test_prep_validate_parity asserts no UNDOCUMENTED code ever appears on one surface but not the
# other over a fixture matrix (sprint acceptance -- replaces the false blanket "prep == validate"
# criterion, which was wrong for at least eight code pairs).
_PREP_REPAIRS = {
    # prep repairs these on write, so it drops the raw-intake finding validate raises. zip_inner_file_name
    # is here because prep emits a correctly named OUTPUT -- refusing over the INPUT archive member name
    # would swap one false refusal for another (databuilder-013).
    "intake_repaired_on_write": {"mixed_line_endings", "cr_only_line_endings", "zip_inner_file_name"},
    # prep normalizes values, so validate's raw view (non-numeric / parse error) is re-expressed after
    # repair (fixed, or surfaced as empty / unrepairable on the prepared frame).
    "value_normalized": {"non_numeric_value", "parse_error", "empty_or_na_value", "unrepairable_value"},
    # prep-only: findings produced by transforms validate never runs, or reported on the prepared frame.
    "prep_only_transforms": {
        "runner_flags", "centering_rows_discarded", "centering_dropped_columns", "no_centered_windows",
        "class_too_short_to_trim", "class_not_partitioned", "class_imbalance", "window_class_imbalance",
        "window_class_yield", "downsample_run_too_short", "resample_integer_preserved", "combine_failed",
        "empty_input", "label_keyspace_mixed", "stale_dictionary_removed", "stale_dictionary_not_removed",
        "unrecognised_file_at_dictionary_path", "output_overwrites_input", "output_not_csv"},
    # mode-disclosure surface difference: validate discloses SP-off via sp_off_unverified; prep's SP-off
    # path handles the mode without re-emitting that advisory (ADR-0006/0007).
    "mode_surface": {"sp_off_unverified"},
}
_PREP_REPAIRS_FLAT = frozenset().union(*_PREP_REPAIRS.values())
# Functional subset (single source of truth): the intake codes prep drops from its own report on write.
_SKIP_INTAKE = _PREP_REPAIRS["intake_repaired_on_write"]


def _output_guard(input_paths, out_path: str):
    """Pre-flight filesystem safety, evaluated BEFORE any analysis and NOT overridable by
    --write-anyway: prep writes a CSV to out_path, so out_path must not be an input file (it would
    destroy the user's only copy) and must not be named .zip (our own reader then rejects the result
    as a broken archive). samefile catches symlink/hardlink aliases a path-string compare misses
    (databuilder-013)."""
    for src in input_paths:
        try:
            if os.path.exists(out_path) and os.path.samefile(out_path, src):
                return Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "output_overwrites_input",
                    f"The output path '{out_path}' is the same file as the input '{src}'. Writing "
                    f"would destroy your only copy — choose a different --out path.",
                    f"{DATASET_REQ}#file-level-requirements", {"out": out_path, "input": src})
        except OSError:
            pass
    if out_path.lower().endswith(".zip"):
        return Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "output_not_csv",
            f"The output path '{out_path}' ends in .zip, but prep writes a plain CSV — the result "
            f"would be a file the platform (and this tool) reads as a broken archive. Use a .csv "
            f"--out path.", f"{DATASET_REQ}#file-level-requirements", {"out": out_path})
    return None


def _dict_path(out_path: str) -> str:
    base, _ = os.path.splitext(out_path)
    return base + "_dictionary.json"


def _looks_like_class_dictionary(path: str) -> bool:
    """True only if the file is the shape relabel_contiguous writes: {token: int}."""
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError):
        return False
    return isinstance(obj, dict) and bool(obj) and all(isinstance(v, int) for v in obj.values())


def _reconcile_stale_dictionary(dpath: str):
    """Remove a leftover class map beside a dataset that has none — but only if it IS one."""
    if not os.path.exists(dpath):
        return []
    name = os.path.basename(dpath)
    if not _looks_like_class_dictionary(dpath):
        # Do not delete what we cannot identify. It still must not travel with the upload.
        return [Finding(
            Group.INTAKE, Severity.FIX_REQUIRED, "unrecognised_file_at_dictionary_path",
            f"'{name}' sits where this dataset's class dictionary would go, but it is not a class "
            f"map and this dataset has no classes to map. Move or delete it before uploading — "
            f"otherwise it travels with the dataset and describes something else.",
            f"{DATASET_REQ}#file-level-requirements", {"path": dpath})]
    try:
        os.remove(dpath)
    except OSError:
        return [Finding(
            Group.INTAKE, Severity.FIX_REQUIRED, "stale_dictionary_not_removed",
            f"'{name}' is a class map left by an earlier run, and this dataset has no classes. "
            f"It could not be removed automatically — delete it by hand, or it will be uploaded "
            f"alongside the data describing a different dataset.",
            f"{DATASET_REQ}#file-level-requirements", {"path": dpath})]
    return [Finding(
        Group.INFO, Severity.INFO, "stale_dictionary_removed",
        f"Removed '{name}' — it is a class map from an earlier run, and this dataset has a "
        f"continuous or absent target, so no class dictionary applies.",
        f"{TASK_TYPES}#what-our-own-tooling-covers-per-task-type", {"path": dpath})]


def prep(input_paths, profile: DatasetProfile, out_path: str, window: int | None,
         do_center: bool | None = None, target_rate: float | None = None, write_anyway: bool = False,
         time_unit: str = "s", sp_on: bool | None = None):
    """Return a result dict: {report, written, out_path, dictionary, dictionary_path}.

    sp_on is the Signal-Processing mode the CLI resolved; None is the legacy contract (SP on, window is a
    real int) so every existing caller is byte-identical. sp_on is False (tabular) skips centering and
    refuses --resample -- both are windowing/continuous-signal operations that would silently corrupt
    independent rows -- and passes the mode to check_dataframe, which then skips the window checks and
    discloses via sp_off_unverified (databuilder-016)."""
    findings: list[Finding] = []
    sp_off = sp_on is False

    # Pre-flight filesystem safety BEFORE any analysis -- not a data verdict, so not overridable by
    # write_anyway (databuilder-013).
    guard = _output_guard(input_paths, out_path)
    if guard is not None:
        return {"report": make_report([guard]), "written": False, "out_path": out_path,
                "dictionary": None, "dictionary_path": None}

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

    # Target column must exist before anything touches it. Return early rather than appending and
    # continuing: relabel_contiguous indexes df[label_col] directly, so carrying on raises KeyError
    # for classification. Anomaly detection is exempt (unlabeled normal-only data).
    if profile.task_type != "anomaly_detection" and profile.label_column not in df.columns:
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "label_column_missing",
            f"The target column '{profile.label_column}' named in the profile is not in the data. "
            f"Every task type except anomaly detection needs it; check the profile against the file. "
            f"The remaining checks were skipped until the target column is present.",
            f"{DATASET_REQ}#inertial-sensor-signal-processing-row-layout",
            {"label_column": profile.label_column, "columns": [str(c) for c in df.columns]}))
        return {"report": make_report(findings), "written": False, "out_path": out_path,
                "dictionary": None, "dictionary_path": None}

    # A continuous target is a value, not a class: it must never be relabelled
    # (discovery/platform-task-types.md). Normalise it numerically instead, so a non-numeric cell is
    # reported rather than silently rank-encoded.
    is_regression = profile.task_type == "regression"

    # Repair sensor (and time) values.
    allow_comma_decimal = profile.separator != "comma"
    numeric_cols = list(profile.sensor_columns)
    if profile.time_column and profile.time_column in df.columns:
        numeric_cols.append(profile.time_column)
    if is_regression:  # the guard above guarantees the column is present
        numeric_cols.append(profile.label_column)
    df, fnd = normalize_numeric(df, numeric_cols, allow_comma_decimal)
    findings += fnd

    # Encode labels (classification and anomaly only). Anomaly data is legitimately unlabeled, and it
    # is the only task type that reaches here without the column -- the guard above returned for the
    # rest -- so there is nothing to encode.
    if is_regression or profile.label_column not in df.columns:
        dictionary = None
    else:
        df, dictionary, fnd = relabel_contiguous(df, profile.label_column, profile.class_map or None)
        findings += fnd

    # Resample (optional). Interpolating a continuous signal; a tabular dataset has none -- each row is an
    # independent observation -- so resampling would fabricate rows. Refuse under SP off, never fabricate.
    if target_rate:
        if sp_off:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.FIX_REQUIRED, "sp_off_resample_refused",
                "You asked to resample, but the profile declares Signal Processing OFF (tabular). "
                "Resampling interpolates a continuous signal; a tabular dataset has none — each row is an "
                "independent observation, so resampling would fabricate rows. Remove --resample, or set "
                '"signal_processing": true if this is a windowed time series.',
                f"{SP_APPLICABILITY}#the-two-modes", {}))
        else:
            df, fnd = resample_to_rate(df, profile.time_column, target_rate, profile.sensor_columns,
                                       profile.label_column, profile.session_column, time_unit)
            findings += fnd

    # Center / trim. A windowing operation, so it is skipped under SP off; the SP-off + gesture_classes
    # contradiction is surfaced by check_dataframe(sp_on=False) below (sp_off_contradicts_profile). For SP
    # on/unset it is default-on for gesture datasets (classification + gesture_classes); --no-center skips.
    center_on = False if sp_off else (do_center if do_center is not None else (
        profile.is_classification and bool(profile.gesture_classes)))
    if center_on:
        df, fnd = center_per_class(df, profile, window)
        findings += fnd

    # Validate the prepared frame (+ output file-name check). Passing the mode -> SP off skips the window
    # checks and emits sp_off_unverified (ADVISORY) / sp_off_contradicts_profile (FIX_REQUIRED).
    findings += validate.check_dataframe(df, profile, window, profile.frequency_domain,
                                         file_name=out_path, sp_on=sp_on)

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

    if dictionary is None:
        # This dataset has no class dictionary — a continuous target (regression), or anomaly data
        # with no target column at all. A rebuild overwrites in place (process P-09), so anything at
        # the dictionary path belongs to an earlier, different run. Never write `null` there, and
        # never assert what the file is without reading it.
        findings += _reconcile_stale_dictionary(dpath)
        return {"report": make_report(findings), "written": True, "out_path": out_path,
                "dictionary": None, "dictionary_path": None}

    with open(dpath, "w", encoding="utf-8") as fh:
        json.dump(dictionary, fh, indent=2, sort_keys=True)
    return {"report": report, "written": True, "out_path": out_path,
            "dictionary": dictionary, "dictionary_path": dpath}

"""validate — two layers (raw-file intake + dataframe semantics) -> a Report.

check_raw_file runs on raw bytes (encoding, line endings, header, file name) because pandas hides
those. check_dataframe runs the semantic contract. run_checks composes both for the standalone
`validate` CLI; pipeline.prep calls check_dataframe directly on the prepared frame. Findings are
deduped by (code, column) so the two layers don't double-report (databuilder-001 [gate]).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import csv_io, datatype
from .findings import Finding, Group, Severity, make_report, Report
from .normalize import try_parse_number, check_timestamps, check_time_order, find_index_column
from .profile import DatasetProfile, NAME_RE
from .window_survival import min_run_ok, short_session_findings, window_yield_findings

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"
SIGNAL_PROC = "wiki/architecture/platform-signal-processing.md"
PREPROC = "wiki/architecture/platform-preprocessing-options.md"
FEATURES = "wiki/architecture/platform-feature-extraction.md"
SP_APPLICABILITY = "wiki/architecture/platform-signal-processing-applicability.md"

MIN_SAMPLES_PER_CLASS = 20
MIN_CLASSES = 2
RATE_TOLERANCE = 0.05  # fractional difference above which two session rates count as "distinct"

# Forbidden characters in the uploaded FILE NAME (dataset-requirements; includes space and dot).
FORBIDDEN_FILENAME_CHARS = set(" !@#$%^&*,.?\":{}\\/|<>()[]+'`")


def _is_pow2(n: int) -> bool:
    return n >= 1 and (n & (n - 1)) == 0


def _dedupe(findings):
    seen, out = set(), []
    for f in findings:
        key = (f.code, f.data.get("column"), f.data.get("label"), f.data.get("session"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def check_filename(path: str):
    name = os.path.basename(path)
    stem = name[:-4] if name.lower().endswith(".csv") else os.path.splitext(name)[0]
    bad = sorted({c for c in stem if c in FORBIDDEN_FILENAME_CHARS})
    if bad:
        return Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "bad_file_name",
            f"The file name '{name}' contains characters the platform forbids ({''.join(bad)} — note "
            f"spaces and dots are not allowed in the name). Rename it using only letters, digits, '-' and '_'.",
            f"{DATASET_REQ}#file-level-requirements", {"name": name, "bad": bad})
    return None


def check_raw_file(path: str, profile: DatasetProfile):
    findings = []
    scan = csv_io.sniff_raw(path)
    findings.extend(scan.findings)
    if scan.delimiter and scan.delimiter != profile.separator:
        findings.append(Finding(
            Group.INTAKE, Severity.INFO, "delimiter_mismatch",
            f"The file's delimiter looks like '{scan.delimiter}' but the profile says '{profile.separator}'. "
            f"Confirm the delimiter before relying on the column split.",
            f"{DATASET_REQ}#file-level-requirements",
            {"detected": scan.delimiter, "profile": profile.separator}))
    name_finding = check_filename(path)
    if name_finding:
        findings.append(name_finding)
    return findings


def _label_ints(df: pd.DataFrame, label_col: str):
    """Return (int_array_or_None, had_non_numeric)."""
    vals, bad = [], False
    for raw in df[label_col].to_numpy():
        v, reason = try_parse_number(raw, allow_comma_decimal=False)
        if reason is not None or not isinstance(v, int):
            bad = True
            continue
        vals.append(v)
    if bad and not vals:
        return None, True
    return np.array(vals, dtype=np.int64), bad


def _value_findings(df, cols, allow_comma_decimal):
    findings = []
    for col in cols:
        if col not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            n_nan = int(pd.isna(df[col]).sum())
            if n_nan:
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "empty_or_na_value",
                    f"Column '{col}' has {n_nan} missing value(s). The platform requires all values numeric.",
                    f"{DATASET_REQ}#value-rules", {"column": col, "count": n_nan}))
            continue
        n_bad = 0
        ex = []
        for idx, raw in zip(df.index, df[col].to_numpy()):
            _, reason = try_parse_number(raw, allow_comma_decimal)
            if reason is not None:
                n_bad += 1
                if len(ex) < 5:
                    ex.append({"row": int(idx), "value": str(raw)})
        if n_bad:
            findings.append(Finding(
                Group.HARD_REJECT, Severity.HARD_REJECT, "non_numeric_value",
                f"Column '{col}' has {n_bad} non-numeric / empty value(s).",
                f"{DATASET_REQ}#value-rules", {"column": col, "count": n_bad, "examples": ex}))
    return findings


def check_dataframe(df: pd.DataFrame, profile: DatasetProfile, window: int | None,
                    freq_domain: bool = False, file_name: str | None = None,
                    holdout_df: pd.DataFrame | None = None, sp_on: bool | None = None):
    findings = []
    # Signal-Processing gate. sp_on is the mode the CLI resolved; None is the legacy contract for
    # every existing caller (pipeline.prep, tests, run_checks default) -> SP on, no mode findings, so
    # their behaviour is byte-identical. Only cmd_validate passes it explicitly.
    #   _sp  -> Signal Processing is on (windowed): run the SP-only checks.
    #   _win -> those checks that also need a concrete window (SP off never produces one).
    _sp = sp_on is not False
    _win = _sp and window is not None

    # Target column present at all. Anomaly detection is exempt: the platform's anomaly data is
    # unlabeled normal-only sensor data, so a missing target column is the documented shape there
    # (discovery/platform-task-types.md). For every other task type its absence means the file cannot
    # be trained on -- and this path passed silently before databuilder-010.
    if profile.task_type != "anomaly_detection" and profile.label_column not in df.columns:
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "label_column_missing",
            f"The target column '{profile.label_column}' named in the profile is not in the data. "
            f"Every task type except anomaly detection needs it; check the profile against the file.",
            f"{DATASET_REQ}#inertial-sensor-signal-processing-row-layout",
            {"label_column": profile.label_column, "columns": [str(c) for c in df.columns]}))

    # Column names.
    for c in df.columns:
        if not NAME_RE.match(str(c)):
            findings.append(Finding(
                Group.HARD_REJECT, Severity.HARD_REJECT, "bad_column_name",
                f"Column name '{c}' has characters outside [A-Za-z0-9_-].",
                f"{DATASET_REQ}#column--header-rules", {"column": str(c)}))
    if len(set(df.columns)) != len(df.columns):
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "duplicate_columns",
            "Two or more columns share a name; column names must be unique.",
            f"{DATASET_REQ}#column--header-rules"))

    # Values numeric (sensor axes + label + time).
    allow_comma_decimal = profile.separator != "comma"
    feature_cols = list(profile.sensor_columns)
    findings += _value_findings(df, feature_cols + [profile.label_column], allow_comma_decimal)
    if profile.time_column and profile.time_column in df.columns:
        findings += check_timestamps(df[profile.time_column], profile.time_column)

    # Index column.
    names = {profile.label_column, *profile.sensor_columns}
    if profile.session_column:
        names.add(profile.session_column)
    if profile.time_column:
        names.add(profile.time_column)
    _, idx_findings = find_index_column(df, names)
    findings += idx_findings

    # Classification target.
    if profile.is_classification and profile.label_column in df.columns:
        labels, had_bad = _label_ints(df, profile.label_column)
        if labels is None or had_bad:
            # Some/all labels are non-numeric. The bad rows are already flagged HARD-REJECT by
            # _value_findings; do NOT compute contiguity/imbalance on a partial label set (misleading).
            findings.append(Finding(
                Group.INFO, Severity.INFO, "labels_not_numeric",
                "The label column is not fully numeric yet; class-structure checks run after the labels "
                "are fixed/encoded.",
                f"{DATASET_REQ}#classification-target-rules"))
        else:
            uniq = sorted(set(labels.tolist()))
            if uniq != list(range(len(uniq))):
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "noncontiguous_target",
                    f"Classification labels {uniq} are not contiguous from 0.",
                    f"{DATASET_REQ}#classification-target-rules", {"labels": uniq}))
            if len(uniq) < MIN_CLASSES:
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "too_few_classes",
                    f"Only {len(uniq)} class(es); the platform needs at least {MIN_CLASSES}.",
                    f"{DATASET_REQ}#classification-target-rules", {"n_classes": len(uniq)}))
            counts = {int(u): int((labels == u).sum()) for u in uniq}
            small = {k: v for k, v in counts.items() if v < MIN_SAMPLES_PER_CLASS}
            if small:
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "class_below_min_samples",
                    f"Class(es) {sorted(small)} have fewer than {MIN_SAMPLES_PER_CLASS} samples.",
                    f"{DATASET_REQ}#classification-target-rules", {"counts": small}))
            if counts and min(counts.values()) and max(counts.values()) / min(counts.values()) >= 3:
                findings.append(Finding(
                    Group.BAD_MODEL, Severity.ADVISORY, "class_imbalance",
                    "Classes are imbalanced; read results with Balanced Accuracy or weighted F1, not plain "
                    "Accuracy, so a small-class change isn't hidden by the large classes. This only changes "
                    "how you read results — the platform's training always optimizes cross-entropy "
                    "regardless of the selected metric, so switching metrics is not itself a training fix.",
                    f"{PREPROC}#task-type--evaluation-metric", {"counts": counts}))

    # Window range, shift, survival: these exist only when Signal Processing is on (the platform
    # windows the stream). With SP off there is no window and none of them applies -- skipping them
    # is the whole point of the field (platform-signal-processing-applicability.md). _win also guards
    # against a None window (SP off never produces one; legacy callers always pass an int).
    if _win:
        # Window range (conditional on frequency-domain).
        if freq_domain:
            if not (_is_pow2(window) and 128 <= window <= 2048):
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "window_out_of_range_fft",
                    f"Frequency-domain features require the window to be a power of 2 in [128,2048]; {window} is not.",
                    f"{SIGNAL_PROC}#frequency-domain-features-exception", {"window": window}))
        else:
            if not (10 <= window <= 1000):
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "window_out_of_range",
                    f"Window must be between 10 and 1000 samples; {window} is out of range.",
                    f"{SIGNAL_PROC}#windowing", {"window": window}))

        # Shift.
        shift = profile.shift
        if shift is not None:
            if shift > window:
                findings.append(Finding(
                    Group.HARD_REJECT, Severity.HARD_REJECT, "shift_exceeds_window",
                    f"Sliding shift ({shift}) cannot exceed the window size ({window}).",
                    f"{SIGNAL_PROC}#sliding-shift-window-overlap", {"shift": shift, "window": window}))
            elif shift != window:
                findings.append(Finding(
                    Group.BAD_MODEL, Severity.ADVISORY, "training_shift_not_window",
                    f"For training, set the sliding shift equal to the window ({window}); a smaller shift "
                    f"over-samples the dominant class. Reserve overlap for inference.",
                    f"{SIGNAL_PROC}#sliding-shift-window-overlap", {"shift": shift, "window": window}))
        else:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.INFO, "shift_unspecified",
                f"Sliding shift not specified; for training set it equal to the window ({window}).",
                f"{SIGNAL_PROC}#sliding-shift-window-overlap", {"window": window}))

        # Window survival (silent loss). min_run_ok is class-run analysis: it applies only to a
        # CLASSIFICATION target whose labels are ALL int-coercible. is_classification excludes a
        # regression VALUE column (an integral target like [60,90,120] is itself fully int-coercible,
        # so that conjunct alone would not suppress it) and anomaly detection (no classes). Full
        # int-coercibility excludes a label still carrying a blank/NaN, which would fracture a real run
        # into a false short one; the blank is a HARD-REJECT the user fixes first (_value_findings).
        # Reuse _label_ints (never a second coercion path) AND feed min_run_ok the coerced labels so
        # run lengths use the same canonical integer classes the target block does -- a class written
        # both "0" and "0.0" is int-coercible (gate passes) but raw-string run detection would split it.
        if profile.is_classification and profile.label_column in df.columns:
            labels, had_bad = _label_ints(df, profile.label_column)
            if labels is not None and not had_bad:
                sdf = df.assign(**{profile.label_column: labels})
                findings += min_run_ok(sdf, profile.label_column, profile.session_column, window)
                # B8 (databuilder-020): per-class window-level yield (INFO) + imbalance (ADVISORY) --
                # what the platform trains on is WINDOWS, not rows, and the two diverge on fragmented
                # data. Verdict-neutral; reuses the same coerced sdf so it never runs where min_run_ok
                # doesn't (SP-off / regression / anomaly / blank-label all skip it).
                findings += window_yield_findings(sdf, profile.label_column, profile.session_column, window)
        # short_session_findings is LABEL-INDEPENDENT (rows-per-session only): lifted out of the guard
        # above so it runs for every task type / label dtype, but kept inside `if _win:` (B5a) so SP-off
        # still skips it.
        findings += short_session_findings(df, profile.session_column, window)

    # Sampling rate. rate_unknown fires in both modes but its SEVERITY is mode-conditional (advisory
    # under SP off, where window math does not run -- see _rate_findings); mixed_sampling_rate is
    # windowing-justified, so it is gated with SP.
    findings += _rate_findings(df, profile, _sp)

    # Data type recommendation.
    rec = datatype.recommend_dtype(df, profile.sensor_columns, profile.target_technology)
    findings.append(Finding(
        Group.BAD_MODEL, Severity.ADVISORY, "recommended_dtype",
        f"Recommended input data type: {rec['dtype']} ({rec['reason']}).",
        rec["rule_ref"], {"dtype": rec["dtype"]}))

    # Direction features for multi-class gestures. Per-window features -> SP-only.
    if _sp and profile.is_classification and len(profile.gesture_classes) >= 2:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.ADVISORY, "enable_lr_features",
            "With two or more directional gesture classes, enable LR_SLOPE and LR_INTERCEPT — they are the "
            "only features encoding signed direction; without them opposite gestures conflate.",
            f"{FEATURES}#observed-in-practice-direction-features-are-load-bearing",
            {"gesture_classes": profile.gesture_classes}))

    # Holdout column order.
    if holdout_df is not None and list(holdout_df.columns) != list(df.columns):
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "holdout_column_order",
            "The holdout file's columns differ in name or order from the training file; they must match "
            "exactly (otherwise the platform auto-splits 80/20 instead of using your holdout).",
            f"{DATASET_REQ}#test--holdout-dataset",
            {"train": list(df.columns), "holdout": list(holdout_df.columns)}))

    # File name.
    if file_name:
        nf = check_filename(file_name)
        if nf:
            findings.append(nf)

    # Signal-Processing mode findings. Only when the caller stated the mode (cmd_validate); legacy
    # callers pass sp_on=None and get none of these, so their reports are byte-identical.
    #
    # Declaring SP off suppresses the window checks above on the profile's say-so alone, and the tool
    # does not yet reconcile "is this really tabular?" against the file (that check is unbuilt). So the
    # suppression is disclosed, not silent -- ADVISORY, not blocking: blocking would punish the one
    # user who declared the mode honestly and push them to conceal it. Unverified *suppression* of
    # checks is what we surface; unverified *addition* (declaring SP on, which only adds checks) is
    # safe and needs no finding.
    if sp_on is False:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.ADVISORY, "sp_off_unverified",
            "This profile declares Signal Processing OFF, so the platform trains on each row as an "
            "independent sample; the window-based checks (window range, sliding shift, window survival, "
            "direction features, mixed sampling rate) were skipped because they do not apply. The tool "
            "has not verified the data is actually tabular — confirm one row is a complete observation "
            "before upload.",
            f"{SP_APPLICABILITY}#the-decision-rule", {}))
        if profile.gesture_classes:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.FIX_REQUIRED, "sp_off_contradicts_profile",
                f"The profile sets Signal Processing OFF but declares gesture classes "
                f"{profile.gesture_classes}. A discrete gesture is a windowed concept; with SP off there "
                f"is no window. Either set \"signal_processing\": true, or drop gesture_classes — note "
                f"that dropping them also turns off default-on gesture centering in prep.",
                f"{SP_APPLICABILITY}#the-two-modes", {"gesture_classes": profile.gesture_classes}))

    return _dedupe(findings)


def _rate_findings(df: pd.DataFrame, profile: DatasetProfile, sp_on: bool = True):
    findings = []
    tcol = profile.time_column
    if tcol and tcol in df.columns:
        rates = []
        groups = df.groupby(profile.session_column, sort=False) if (
            profile.session_column and profile.session_column in df.columns) else [(None, df)]
        for _, sub in groups:
            t = pd.to_numeric(sub[tcol], errors="coerce").to_numpy(dtype=np.float64)
            t = t[~np.isnan(t)]
            if len(t) > 2:
                dt = np.median(np.diff(np.sort(t)))
                if dt > 0:
                    rates.append(1.0 / dt)
        if sp_on and len(rates) >= 2 and (max(rates) - min(rates)) / min(rates) > RATE_TOLERANCE:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.ADVISORY, "mixed_sampling_rate",
                f"Sessions have different sampling rates (~{min(rates):.1f}–{max(rates):.1f} units⁻¹). "
                f"Resample everything to one common rate before upload — the window is counted in samples, "
                f"so a mixed rate makes the same window span different real durations.",
                f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {"rates": [round(r, 2) for r in rates]}))
    elif profile.time_column is None and profile.sampling_rate_hz is None:
        # Rate is known if the profile records it OR declares a time column (centering may have dropped
        # the time column from the frame, but the rate was still derivable from it). Severity is
        # mode-conditional: the rate is load-bearing only when the platform windows the data (window
        # math is in samples), so SP off -> ADVISORY (do not block a legitimately tabular user); SP on
        # or unstated (legacy sp_on=None -> _sp=True) -> FIX_REQUIRED. B5a carry-out: conditional on the
        # mode, NOT demoted globally.
        sev = Severity.FIX_REQUIRED if sp_on else Severity.ADVISORY
        findings.append(Finding(
            Group.BAD_MODEL, sev, "rate_unknown",
            "No time column and no recorded sampling rate. Record the sampling rate (Hz) — window math, "
            "resampling, and session checks all depend on it.",
            f"{SIGNAL_PROC}#sampling-rate-rule-critical-for-our-data-builder", {}))
    return findings


def run_checks(path: str, profile: DatasetProfile, window: int | None, freq_domain: bool = False,
               holdout_path: str | None = None, sp_on: bool | None = None) -> Report:
    """Standalone file validation: raw-bytes intake + dataframe semantics -> Report."""
    findings = check_raw_file(path, profile)
    scan = csv_io.sniff_raw(path)
    df, read_findings = csv_io.read_table(path, profile.sep_char,
                                          scan.encoding if scan.encoding != "unknown" else "utf-8")
    findings += read_findings
    if df is not None:
        # Timestamp order (databuilder-019). validate sees exactly one file = one recording (per
        # session where a session column exists). SP-gated: with SP off the platform trains on each row
        # independently, so row order is irrelevant (B5a carry-out). Placed here, NOT in
        # check_dataframe, so prep's check_dataframe call does not re-run it on the already-combined
        # frame (which would re-expose the concatenation seams combine deliberately checked per-file).
        if sp_on is not False:
            findings += check_time_order(df, profile.time_column, profile.session_column)
        holdout_df = None
        if holdout_path:
            hscan = csv_io.sniff_raw(holdout_path)
            # Surface the holdout's raw-byte findings too -- they were computed for the encoding then
            # dropped, so a readable holdout with an illegal inner name / mixed line endings was silently
            # ignored (databuilder-017, B3 carry-out). Deduped against the training file by run_checks.
            findings += hscan.findings
            holdout_df, hf = csv_io.read_table(holdout_path, profile.sep_char,
                                               hscan.encoding if hscan.encoding != "unknown" else "utf-8")
            findings += hf
        findings += check_dataframe(df, profile, window, freq_domain, file_name=path,
                                    holdout_df=holdout_df, sp_on=sp_on)
    return make_report(_dedupe(findings))

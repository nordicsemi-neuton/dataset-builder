"""quality — per-source profiling + intra-class source-outlier detection.

Answers "is one recording / one user's data collected differently from the rest?" by comparing each
source's per-window features for a class against the SAME class pooled over the other sources (mean
Cohen's-d), using the validated 17-feature set from
scripts/diagnostics/windowed_feature_distribution_comparison.py. The d threshold is INDICATIVE, not a
platform pass/fail (there is no documented cutoff) — the orchestrator presents the evidence and the user
decides (databuilder-004). A source = a session-column value, or one input file (one user = one file).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import csv_io
from .findings import Finding, Group, Severity
from .normalize import normalize_numeric
from .profile import DatasetProfile

CASE_PATTERNS = "wiki/synthesis/support-case-patterns.md"
DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"

OUTLIER_D = 1.5     # mean Cohen's-d above which a source's class looks like a different regime (indicative)
MIN_WINDOWS = 3     # need at least this many windows on each side for a stable comparison
SOURCE_COL = "__source__"
N_FEATURES_PER_AXIS = 17


def windowed_features(arr: np.ndarray, win: int, shift: int) -> np.ndarray:
    """Validated 17-features-per-axis set (identical to the diagnostic script). arr shape (n, n_axes)."""
    if arr.ndim != 2 or len(arr) < win:
        return np.empty((0, arr.shape[1] * N_FEATURES_PER_AXIS if arr.ndim == 2 else 0))
    n_axes = arr.shape[1]
    feats = []
    for s in range(0, len(arr) - win + 1, shift):
        w = arr[s:s + win].astype(np.float64)
        row = []
        for ai in range(n_axes):
            x = w[:, ai]
            m, sd = x.mean(), x.std()
            row.extend([
                x.min(), x.max(), x.max() - x.min(), m, sd,
                np.sqrt((x ** 2).mean()), np.abs(x).mean(), np.abs(x - m).mean(),
                ((np.diff(np.sign(x - m))) != 0).sum() / len(x),
                ((np.diff(np.sign(x))) != 0).sum() / len(x),
                (x > 0).mean(), (x > m).mean(), (x > (m + sd)).mean(),
                ((np.diff((x > (m + sd)).astype(int))) == 1).sum() / len(x),
                np.abs(x).max() / max(np.sqrt((x ** 2).mean()), 1.0),
                np.sqrt(np.mean(np.diff(x) ** 2)) if len(x) > 1 else 0,
                np.abs(np.diff(x)).mean() if len(x) > 1 else 0,
            ])
        feats.append(row)
    return np.asarray(feats, dtype=np.float64)


def load_sources(paths, profile: DatasetProfile):
    """Read recordings, tag each with its source, normalise sensor columns. Returns (df, source_col, findings).

    Multiple files -> source = file basename. Single file -> source = the profile's session column (or one
    source if none).
    """
    findings: list[Finding] = []
    frames = []
    for path in paths:
        scan = csv_io.sniff_raw(path)
        enc = scan.encoding if scan.encoding != "unknown" else "utf-8"
        df, fnd = csv_io.read_table(path, profile.sep_char, enc)
        findings.extend(fnd)
        if df is None:
            continue
        df = df.copy()
        df[SOURCE_COL] = os.path.basename(path)
        frames.append(df)
    if not frames:
        return None, None, findings
    df = pd.concat(frames, ignore_index=True)
    df, fnd = normalize_numeric(df, list(profile.sensor_columns), profile.separator != "comma")
    findings.extend(fnd)

    if len(paths) > 1:
        source_col = SOURCE_COL
    elif profile.session_column and profile.session_column in df.columns:
        source_col = profile.session_column
    else:
        source_col = SOURCE_COL  # single source
    return df, source_col, findings


def quality_report(df: pd.DataFrame, profile: DatasetProfile, window: int, source_col: str) -> dict:
    """Per-source profiling + intra-class outlier flags. Pure analysis; never mutates data.

    The profiling loop always runs (it needs only row counts); class_counts and the intra-class outlier
    comparison need the label column. quality-report never called check_dataframe, so a missing label
    column used to KeyError here -- it now surfaces the same label_column_missing HARD_REJECT the other
    two surfaces have, anomaly detection exempt (databuilder-017). comparison_ran tells the caller whether
    the source comparison actually happened, so the CLI does not print a false "no outlier" reassurance.
    """
    label_col = profile.label_column
    label_present = label_col in df.columns
    findings: list[Finding] = []
    if not label_present and profile.task_type != "anomaly_detection":
        # Same guard check_dataframe / pipeline.prep carry (databuilder-010). Anomaly detection is
        # unlabeled normal-only data (discovery/platform-task-types.md), so a missing label is its
        # documented shape, not an error -- exempt, no finding.
        findings.append(Finding(
            Group.HARD_REJECT, Severity.HARD_REJECT, "label_column_missing",
            f"The target column '{label_col}' named in the profile is not in the data. quality-report "
            f"groups each class to compare sources, so it has no classes to compare; check the profile "
            f"against the file.",
            f"{DATASET_REQ}#inertial-sensor-signal-processing-row-layout",
            {"label_column": label_col, "columns": [str(c) for c in df.columns]}))

    sensors = [c for c in profile.sensor_columns if c in df.columns]
    sources = list(pd.unique(df[source_col])) if source_col in df.columns else ["all"]

    # --- per-source profiling (class_counts only when the label column is present) ---
    profiling = []
    for src in sources:
        sub = df[df[source_col] == src] if source_col in df.columns else df
        counts = ({str(k): int(v) for k, v in sub[label_col].value_counts().sort_index().items()}
                  if label_present else {})
        profiling.append({"source": str(src), "rows": int(len(sub)), "class_counts": counts})

    # --- intra-class source-outlier detection (needs the label + >=2 sources + a window) ---
    # window is None under Signal Processing OFF (tabular): there are no windowed features to compare, so
    # the comparison is skipped and shift's None // 2 is never reached (databuilder-016).
    outliers, insufficient = [], []
    comparison_ran = label_present and len(sources) >= 2 and window is not None
    if comparison_ran:
        shift = max(1, window // 2)
        for label_val in pd.unique(df[label_col]):
            cls = df[df[label_col] == label_val]
            for src in sources:
                in_src = cls[cls[source_col] == src][sensors].to_numpy(dtype=np.float64)
                in_rest = cls[cls[source_col] != src][sensors].to_numpy(dtype=np.float64)
                f_src = windowed_features(in_src, window, shift)
                f_rest = windowed_features(in_rest, window, shift)
                if len(f_src) < MIN_WINDOWS or len(f_rest) < MIN_WINDOWS:
                    insufficient.append({"source": str(src), "label": str(label_val),
                                         "windows": int(len(f_src))})
                    continue
                pooled = np.sqrt((f_src.std(axis=0) ** 2 + f_rest.std(axis=0) ** 2) / 2 + 1e-9)
                d = np.abs(f_src.mean(axis=0) - f_rest.mean(axis=0)) / pooled
                mean_d = float(d.mean())
                if mean_d >= OUTLIER_D:
                    per_axis = [float(d[i * N_FEATURES_PER_AXIS:(i + 1) * N_FEATURES_PER_AXIS].mean())
                                for i in range(len(sensors))]
                    top = [sensors[i] for i in np.argsort(per_axis)[::-1][:2]]
                    outliers.append({"source": str(src), "label": str(label_val),
                                     "mean_d": round(mean_d, 2), "windows": int(len(f_src)),
                                     "top_axes": top})

    for o in outliers:
        findings.append(Finding(
            Group.BAD_MODEL, Severity.ADVISORY, "source_outlier",
            f"Source '{o['source']}' for class {o['label']} sits ~{o['mean_d']} std (Cohen's d) from the "
            f"same class in the other sources (most on {', '.join(o['top_axes'])}) — it was likely "
            f"collected differently. Indicative, not a hard rule: review it, then keep / re-collect / drop.",
            f"{CASE_PATTERNS}", o))

    return {"source_col": source_col, "sources": profiling, "outliers": outliers,
            "insufficient": insufficient, "threshold_d": OUTLIER_D,
            "note": "Cohen's-d is indicative (no documented platform cutoff); evidence for the user to judge.",
            "findings": findings, "comparison_ran": comparison_ran}

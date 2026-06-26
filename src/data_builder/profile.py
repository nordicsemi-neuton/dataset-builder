"""DatasetProfile — load & structurally validate a dataset-profile JSON.

Contract: wiki/architecture/data-skill-preset-contract.md. The profile is confirm-first config the
caller has already reconciled against the file; this loader only checks structural invariants and
raises ProfileError on a broken profile (a usage error -> CLI exit 4). Per-dataset *data* rules
(does the class map match the actual labels, is the window in range) are the validator's job.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Separator keyword -> delimiter character (platform-accepted set).
SEP_CHAR = {"comma": ",", "semicolon": ";", "pipe": "|", "caret": "^", "tab": "\t"}
# Desktop inference runner delimiter keyword (NOTE: the runner calls pipe "vbar", caret "caret").
# platform-deployment-inference.md: keywords comma, semicolon, tab, caret, vbar.
RUNNER_DELIM_KEYWORD = {"comma": "comma", "semicolon": "semicolon", "pipe": "vbar",
                        "caret": "caret", "tab": "tab"}

VALID_TASK_TYPES = {"multiclass_classification", "binary_classification",
                    "regression", "anomaly_detection"}
CLASSIFICATION_TASKS = {"multiclass_classification", "binary_classification"}
VALID_TECH = {"neuton", "axon"}


class ProfileError(ValueError):
    """A structurally invalid dataset profile."""


@dataclass
class DatasetProfile:
    dataset_name: str
    label_column: str
    sensor_columns: list[str]
    separator: str
    task_type: str
    session_column: str | None = None
    time_column: str | None = None
    sampling_rate_hz: float | None = None
    units: dict[str, str] = field(default_factory=dict)
    target_technology: str = "neuton"
    class_encoding: dict[str, Any] | None = None
    window: dict[str, Any] | None = None
    holdout_path: str | None = None
    notes: str = ""

    # --- convenience -------------------------------------------------------
    @property
    def sep_char(self) -> str:
        return SEP_CHAR[self.separator]

    @property
    def runner_delim_keyword(self) -> str:
        return RUNNER_DELIM_KEYWORD[self.separator]

    @property
    def is_classification(self) -> bool:
        return self.task_type in CLASSIFICATION_TASKS

    @property
    def is_axon(self) -> bool:
        return self.target_technology == "axon"

    @property
    def class_map(self) -> dict[str, int]:
        if self.class_encoding:
            return dict(self.class_encoding.get("map", {}))
        return {}

    @property
    def gesture_classes(self) -> list[int]:
        if self.class_encoding:
            return list(self.class_encoding.get("gesture_classes", []))
        return []

    @property
    def continuous_classes(self) -> list[int]:
        if self.class_encoding:
            return list(self.class_encoding.get("continuous_classes", []))
        return []

    @property
    def window_candidates(self) -> list[int]:
        if self.window:
            return list(self.window.get("candidates", []))
        return []

    @property
    def shift(self) -> int | None:
        if self.window:
            return self.window.get("shift")
        return None

    @property
    def frequency_domain(self) -> bool:
        if self.window:
            return bool(self.window.get("frequency_domain_features", False))
        return False

    # --- loading / validation ---------------------------------------------
    @classmethod
    def load(cls, path: str) -> "DatasetProfile":
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileError(f"cannot read profile {path!r}: {exc}") from exc
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DatasetProfile":
        if not isinstance(raw, dict):
            raise ProfileError("profile must be a JSON object")
        for key in ("dataset_name", "label_column", "sensor_columns", "separator", "task_type"):
            if key not in raw:
                raise ProfileError(f"profile missing required field: {key}")

        sep = raw["separator"]
        if sep not in SEP_CHAR:
            raise ProfileError(f"separator must be one of {sorted(SEP_CHAR)}, got {sep!r}")
        task = raw["task_type"]
        if task not in VALID_TASK_TYPES:
            raise ProfileError(f"task_type must be one of {sorted(VALID_TASK_TYPES)}, got {task!r}")
        tech = raw.get("target_technology", "neuton")
        if tech not in VALID_TECH:
            raise ProfileError(f"target_technology must be one of {sorted(VALID_TECH)}, got {tech!r}")

        sensors = raw["sensor_columns"]
        if not isinstance(sensors, list) or not sensors:
            raise ProfileError("sensor_columns must be a non-empty list")

        prof = cls(
            dataset_name=str(raw["dataset_name"]),
            label_column=str(raw["label_column"]),
            sensor_columns=[str(c) for c in sensors],
            separator=sep,
            task_type=task,
            session_column=raw.get("session_column"),
            time_column=raw.get("time_column"),
            sampling_rate_hz=raw.get("sampling_rate_hz"),
            units=dict(raw.get("units") or {}),
            target_technology=tech,
            class_encoding=raw.get("class_encoding"),
            window=raw.get("window"),
            holdout_path=raw.get("holdout_path"),
            notes=str(raw.get("notes", "")),
        )
        prof._validate()
        return prof

    def _validate(self) -> None:
        # Column-name charset (same rule the platform enforces on headers).
        names = [self.label_column, *self.sensor_columns]
        if self.session_column:
            names.append(self.session_column)
        if self.time_column:
            names.append(self.time_column)
        for n in names:
            if not NAME_RE.match(n):
                raise ProfileError(f"column name {n!r} has characters outside [A-Za-z0-9_-]")
        if len(set(names)) != len(names):
            raise ProfileError(f"profile column names are not unique: {names}")

        if self.sampling_rate_hz is not None and not (self.sampling_rate_hz > 0):
            raise ProfileError("sampling_rate_hz must be > 0 when set")

        # Class encoding: contiguous-from-0; gesture/continuous are subsets of the map's indices.
        if self.class_encoding is not None:
            cmap = self.class_map
            if not cmap:
                raise ProfileError("class_encoding present but 'map' is empty")
            idxs = sorted(cmap.values())
            if idxs != list(range(len(idxs))):
                raise ProfileError(
                    f"class indices must be contiguous from 0, got {idxs}")
            allowed = set(idxs)
            for label, group in (("gesture_classes", self.gesture_classes),
                                  ("continuous_classes", self.continuous_classes)):
                bad = [i for i in group if i not in allowed]
                if bad:
                    raise ProfileError(f"{label} {bad} are not indices in the class map")
            overlap = set(self.gesture_classes) & set(self.continuous_classes)
            if overlap:
                raise ProfileError(
                    f"a class is in both gesture_classes and continuous_classes: {sorted(overlap)}")

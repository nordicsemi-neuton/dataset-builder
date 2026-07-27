---
type: architecture
status: active
updated: 2026-07-27
implementation:
  - ../../src/data_builder/datatype.py
  - ../../src/data_builder/resample.py
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-windowing.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
  - owner-supplied platform knowledge (10.07.2026, direct, not in the doc bundle)
tags: [platform, preprocessing, data-type, normalization, task-type, metrics, contract]
---

# platform — Preprocessing options: data type, normalization, task & metrics

These are the configuration choices the user makes after upload. They are **driven by the shape of the prepared data**, so the data-builder should surface them (e.g. recommend the input data type, flag class imbalance). Set on the Data Preprocessing step.

Related: [dataset requirements](platform-dataset-requirements.md) · [signal processing](platform-signal-processing.md) · [task types & anomaly detection](../discovery/platform-task-types.md).

## Input data type (one type for the whole dataset)

Pick a **single** numeric type for **all** features: **INT8, INT16, or FLOAT32**. The platform auto-detects it; you can override.

| Type | Applies when | Value range |
|---|---|---|
| INT8 (8-bit integer) | all values fit | **-128 … 127** |
| INT16 (16-bit integer) | all values fit | **-32 768 … 32 767** |
| FLOAT32 (32-bit float) | **any** value is a float | floating point |

- Rule for mixed types: **choose the widest type present** (e.g. one FLOAT32 feature ⇒ whole dataset is FLOAT32).
- The data type used for prediction must match the training type.
- **Wrong type ⇒ metric degradation or larger footprint / lower accuracy.** This is why correct numeric preparation matters.
- **Axon technology: only FLOAT32 is available** (the docs say "Axon"; Axon runs the LiteRT framework — see [overview](../discovery/platform-overview.md)).

## Normalization type

- **Unique scale for each feature** — each feature scaled on its own range. Increases accuracy; may increase model size. (Demo uses this because features have different ranges.)
- **Unified scale for all features** — one scale for all; reduces size when features are already on the same scale.
- With **Signal Processing enabled**, default is **AutoSelect**; extracted features normalized within their own scale, raw data normalized per variable and axis.

## Task type & evaluation metric

**Task type** is fixed at solution creation (see [task types](../discovery/platform-task-types.md)): Regression, Binary Classification, Multi-class Classification, or Anomaly Detection. Each has a selectable **metric**; defaults: **Accuracy** (classification), **RMSE** (regression).

| Task type | Predicts | Available metrics |
|---|---|---|
| Binary Classification | one of two classes | Accuracy, AUC, Balanced Accuracy, F1, Gini, Lift, LogLoss, Precision, Recall |
| Multi-class Classification | one of ≥3 categories | Accuracy, Balanced Accuracy, F1 (weighted/macro), LogLoss, Precision (weighted/macro), Recall (weighted/macro) |
| Regression | continuous value | MAE, MSE, R², RMSE, RMSLE, RMSPE |
| Anomaly Detection | normal vs outlier | Reconstruction Accuracy |

### Metric notes relevant to data preparation
- **Class imbalance** → prefer **Balanced Accuracy** / weighted F1 **for reading results**, not as a training fix (the gesture demo picks Balanced Accuracy because gesture classes are imbalanced). The data-builder should report per-class counts so the user can choose. (Hard floor regardless: **≥20 samples/class** — see [dataset requirements](platform-dataset-requirements.md).)
- **The selected metric does not change how the model is trained.** Neuton's optimizer always minimizes cross-entropy internally regardless of which metric is selected in the UI — the metric is evaluation/model-comparison only. Recommending a metric switch can fix how a user *reads* an imbalanced result (a small-class gain hidden by Accuracy becomes visible under Balanced Accuracy/weighted F1); it will not make a retrain behave differently. See [Neuton framework](../discovery/platform-neuton-framework.md) and [domain P-13](../principles/domain.md).
- AUC ∈ [0,1] (1 perfect, 0.5 random); F1/Precision/Recall ∈ [0,1]; R²: 1 perfect, 0 no power; RMSE = √MSE (lower better); **RMSPE excludes rows whose target is 0**.
- Full metric definitions: see [raw](../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md) (tables reproduced verbatim there) — not duplicated here to keep this page atomic.

## Implementation

Data-type recommendation in [`datatype.py`](../../src/data_builder/datatype.py) — **Axon ⇒ FLOAT32**, else INT8/INT16/FLOAT32 from observed value ranges; class-balance and metric advice are surfaced by [`validate.py`](../../src/data_builder/validate.py). Engine: [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md). Raw docs remain in `sources:` for re-verification.

**Integer preservation on the resample path** ([ADR-0004](../decisions/adr-0004-resample-integer-preservation.md), B4): resampling interpolates, which turns whole-number sensor counts (raw INT16 is the platform's preferred storage) into fractional values and would push `recommend_dtype` to FLOAT32 for no real gain. So on the resample path only, [`resample_to_rate`](../../src/data_builder/resample.py) rounds back any column whose **every source value was integral** (it stays `float64`, is never cast — [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md)'s "never cast to int" is narrowed to "never cast so as to change the represented value"), emits a `resample_integer_preserved` INFO **only when the resample actually ran** ([process P-29](../principles/process.md)), and `recommend_dtype` then recovers INT8/INT16. The fix is at the source; the shared writer is unmodified and the non-resampled path is byte-identical ([process P-30](../principles/process.md)).

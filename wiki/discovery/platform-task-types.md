---
type: discovery
status: active
updated: 2026-07-23
sources:
  - ../../raw/platform-docs/2026-06-25-overview-neuton-axon-workflow.md
  - ../../raw/owner-notes/2026-07-23-signal-processing-default.md
  - ../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md
  - ../../raw/platform-docs/2026-06-25-anomaly-detection.md
  - ../../raw/platform-docs/2026-06-25-wake-word-detection.md
  - ../../raw/platform-docs/2026-06-25-analytics-tools.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
tags: [platform, task-types, anomaly-detection, wake-word, analytics, classification, regression]
---

# platform — Task types (and what each needs from the data)

Task type is chosen at solution creation and **changes the data shape the data-builder must produce**. Metrics per task: [preprocessing options](../architecture/platform-preprocessing-options.md).

| Task type | Neuton | Axon | Target/label needed | Notes |
|---|---|---|---|---|
| Binary Classification | ✓ | ✓ | yes — integer class label (cardinality/encoding rules → dataset requirements) | predicts 1 of 2 classes |
| Multi-class Classification | ✓ | ✓ | yes — integer class label (cardinality/encoding rules → dataset requirements) | predicts 1 of ≥3 categories |
| Regression | ✓ | ✓ | yes — continuous numeric target | e.g. HR, temperature |
| **Anomaly Detection** | ✓ | — | **no label** | unsupervised (below) |
| **Wake Word Detection** | — | ✓ (Axon) | data-free option | audio (below) |

Hard label rules (classification): see [dataset requirements](../architecture/platform-dataset-requirements.md).

**Task type is not the only mode choice.** Independently of it, **Signal Processing is a per-solution
option and is off by default** — with it off the platform trains on the CSV as a plain feature table
(one row = one training sample) and no windowing, shift or feature setting applies. Which mode a
dataset needs is a data question, decided before any preparation:
[SP applicability](../architecture/platform-signal-processing-applicability.md), [process P-12](../principles/process.md).

## Data modality — platform scope vs. our own experience

Two different questions, easily conflated. Answer both before proposing work ([process P-14](../principles/process.md)).

| Modality | In the platform's Signal-Processing scope? | Do our domain principles transfer? |
|---|---|---|
| Accelerometer / gyroscope (IMU) | yes | **yes** — P-01…P-25 were derived from exactly this |
| Magnetometer | yes (named in [dataset requirements](../architecture/platform-dataset-requirements.md)) | mostly; the scale/gravity probes ([P-11](../principles/domain.md), [P-22](../principles/domain.md)) assume an accelerometer reference that does not exist here |
| EMG and similar biopotential | yes (named in dataset requirements) | **partly, and state which** — event/window rules ([P-01](../principles/domain.md), [P-17](../principles/domain.md)) transfer; full-scale, gravity-probe and centering assumptions do not. Densely-packed short events are the known trap ([P-19](../principles/domain.md)) |
| Spatial grids (time-of-flight arrays, low-resolution imaging) | as data, yes — but usually **not** as a windowed signal | **no** — typically tabular; see [SP applicability](../architecture/platform-signal-processing-applicability.md) |
| Audio / microphone | only via Wake Word Detection on Axon (below) | **no** — out of our CSV-prep scope |

The rule this table encodes: a modality being in the platform's scope does **not** mean our principles
apply to it unchanged. Where they are being extrapolated, say so.

## What our own tooling covers, per task type

Distinct from what the *platform* supports. Recording it so the gap is visible rather than discovered
mid-task.

| | classification | regression | anomaly detection | wake word |
|---|---|---|---|---|
| platform supports | ✓ | ✓ | ✓ (Neuton) | ✓ (Axon) |
| **in our scope** | ✓ | **✓ (as of 23.07.2026)** | not yet | no — out of scope |
| intake / format validation | ✓ | ✓ | ✓ | n/a |
| label encoding | ✓ | must be **skipped** — a continuous target must not be relabelled | n/a (no target) | n/a |
| window-survival / class checks | ✓ | class-based; needs a target-distribution equivalent | n/a | n/a |
| outlier / quality report | ✓ | class-based; needs a regression mode | n/a | n/a |
| measured feature separability | ✓ | class-based; needs a regression mode | n/a | n/a |
| null-model baseline | n/a | **required** ([domain P-24](../principles/domain.md)) | n/a | n/a |
| holdout design | ✓ ([domain P-16](../principles/domain.md)) | ✓, stratified by target distribution | **no holdout supported** | n/a |

## Anomaly Detection (Neuton) — data implications

- **Unsupervised:** you do **not** label data normal/abnormal. **Upload only normal operational sensor data**; the model learns "normal," and at inference flags data outside learned patterns as abnormal.
- ⇒ **No target/class column required** for the training set (unlike classification/regression).
- **Always trains a single model and does NOT support a holdout validation dataset.** So the data-builder must **not** produce/expect a validation split for anomaly tasks.
- Validation is manual: run inference on separate datasets *with* and *without* anomalies and compare anomaly scores.
- Diagnostics: a **cosine distance distribution plot** (each point = a training sample; closer to center = more similar) and **Reconstruction Accuracy** (how well the model recreates input; closer to **1** = better). Metric for the task = **Reconstruction Accuracy**.

## Wake Word Detection (Axon NPU) — out of our inertial scope

- **Audio / microphone** domain (not inertial sensors), so largely **outside the data-builder's CSV-prep scope**.
- A **data-free pipeline** can generate a wake-word model **without uploading a dataset** (also a pre-built "Okay Nordic" model exists). Custom wake words, live testing, and on-device inference are supported.
- Captured for completeness; full detail: [raw](../../raw/platform-docs/2026-06-25-wake-word-detection.md).

## Analytics tools (post-training evaluation)

Background — used after training, not for data prep, but useful to interpret results:
- **Data analysis** — inspect dataset/data quality.
- **Model quality diagram** — overall model quality view.
- **Feature Importance Matrix (FIM)** — which features drive predictions.
- **Confusion matrix** — per-class prediction correctness (classification).

> Note: analytics-tools bodies were captured but are terse; treat as orientation and re-verify specifics against [raw](../../raw/platform-docs/2026-06-25-analytics-tools.md) before relying on numeric detail.

## Related

[overview](platform-overview.md) · [data-collection practices](platform-data-collection-practices.md) · architecture: [dataset requirements](../architecture/platform-dataset-requirements.md), [preprocessing options](../architecture/platform-preprocessing-options.md).

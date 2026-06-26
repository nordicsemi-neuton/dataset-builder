---
type: discovery
status: active
updated: 2026-06-25
sources:
  - ../../raw/platform-docs/2026-06-25-overview-neuton-axon-workflow.md
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

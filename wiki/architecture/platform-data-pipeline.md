---
type: architecture
status: active
updated: 2026-06-25
implementation:
  - ../../raw/platform-docs/2026-06-25-pipeline-overview.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-overview.md
  - ../../raw/platform-docs/2026-06-25-pipeline-solution-creation.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-uploading-and-setup.md
  - ../../raw/platform-docs/2026-06-25-pipeline-dataset-requirements.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-overview-neuton-axon-workflow.md
  - ../../raw/platform-docs/2026-06-25-neural-network-framework.md
  - ../../raw/platform-docs/2026-06-25-anomaly-detection.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
tags: [platform, pipeline, workflow, upload, solution, holdout, session-id]
---

# platform — Model-creating pipeline (end-to-end workflow)

The platform's documented pipeline is "several fully automated steps." This page is the **workflow contract**: where our data-builder's output plugs in (steps 2–3) and what the platform does before/after. Our tool's job ends at "a validated CSV ready to upload."

Steps (per the Model creating pipeline overview):

1. **Solution creation** — choose technology + task type (below).
2. **Dataset requirements** — the input contract → [dataset requirements](platform-dataset-requirements.md).
3. **Data uploading & setup** — upload, pick target column, session ID, holdout (below).
4. **Data preprocessing** — input type, normalization, task/metric → [preprocessing options](platform-preprocessing-options.md).
5. **Signal processing** — windowing/features → [signal processing](platform-signal-processing.md) + [feature extraction](platform-feature-extraction.md).
6. **Model training** — automatic (Neuton) or configured (LiteRT/Axon).
7. **Model settings** — bit depth, output format, target HW → [deployment/inference](platform-deployment-inference.md).
8. **Run inference on MCU** / **9. Run inference on desktop** → [deployment/inference](platform-deployment-inference.md).

Workflow as stated in the overview: **(1) select data for training → (2) train → (3) run inference on a device.** Required inputs for Neuton are minimal — **the data, a target variable, and a metric**; "training, validation, and model selection all happen automatically" (this last quote is from the Neuton-framework page → [neuton framework](../discovery/platform-neuton-framework.md)).

## Step 1 — Solution creation

- Click **Add New Solution**; **solution name must use Latin letters**.
- Choose **Task Type**, which depends on the technology:
  - **Neuton:** Classification, Regression, **Anomaly Detection**.
  - **Axon NPU:** Classification, Regression, **Wake Word Detection**.
- Technology + task type are fixed here and gate later options (e.g. Axon ⇒ FLOAT32 only; anomaly ⇒ no holdout). See [task types](../discovery/platform-task-types.md).

## Steps 2–3 — Upload & dataset setup (our integration point)

- **Upload one `.csv` or `.zip`** by button or drag-and-drop. **One dataset trains one model** — combine multiple recordings first (commands in [dataset requirements](platform-dataset-requirements.md)).
- The platform **auto-validates on upload**; errors must be fixed and re-uploaded; success = green check. **Our data-builder should pre-empt these errors** so the user never sees a rejection.
- Data is **encrypted and stored in the cloud**; duplicate filenames prompt a rename; upload each dataset once and reuse from storage.
- **Preloaded use cases**: demo datasets with fixed, non-editable settings — for learning only.
- **Dataset options after upload:** designate the **Target Column**; optionally a **Session ID** column; optionally exclude columns via **Remove variables**.

### Holdout validation

- Toggle on and **upload a separate validation CSV** that **matches the training format** — the holdout must have the same file structure and field order as the training set (per [dataset requirements](platform-dataset-requirements.md)).
- If **off**, the platform **auto-splits the training data 80% train / 20% validation**.
- **Anomaly detection does not support a holdout dataset** (single model only) — see [task types](../discovery/platform-task-types.md).

## Output of the pipeline

On completion the user gets a **downloadable archive**: a ready-to-use model, the **total footprint** of the ML solution, and the **nRF Edge AI Desktop Inference Runner** for validating on test data → [deployment/inference](platform-deployment-inference.md). Support: in-platform AI chatbot + Nordic DevZone.

## Implementation

No tool code yet. The data-builder targets steps 2–3: produce a single validated CSV (+ optional matching holdout CSV) that passes the upload auto-check on the first try. Authoritative source: `raw/platform-docs/` (see `sources:`).

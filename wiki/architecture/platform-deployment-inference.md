---
type: architecture
status: active
updated: 2026-06-25
implementation:
  - ../../src/data_builder/pipeline.py
  - ../../raw/platform-docs/2026-06-25-pipeline-model-settings.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-model-settings.md
  - ../../raw/platform-docs/2026-06-25-pipeline-inference-on-desktop.md
  - ../../raw/platform-docs/2026-06-25-pipeline-inference-on-mcu.md
  - ../../raw/platform-docs/2026-06-25-pipeline-model-training.md
  - ../../scripts/postprocessing/postprocessing_pipelines.py
  - ../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c
tags: [platform, deployment, inference, bit-depth, target-hardware, csv-runner, contract]
---

# platform — Model settings, deployment & inference CSV contract

The output side of the pipeline. Most of this is downstream of our data-builder, **except the desktop inference runner's CSV contract**, which the data-builder should match so users can validate locally with their prepared test data.

Related: [pipeline](platform-data-pipeline.md) · [dataset requirements](platform-dataset-requirements.md) · [preprocessing options](platform-preprocessing-options.md).

## Model settings (footprint-shaping)

- **Weights/coefficients bit depth:** 8-bit, 16-bit, or 32-bit. 8/16-bit allow integer **or** float math; 32-bit is float-only. Default matches dataset type. **LiteRT: locked to 32-bit float** (trains in float, final model quantized).
- **Output format:** Quantized 8-bit (probabilities 0–255), Quantized 16-bit (0–65 535), or Floating-point 32-bit (0–1). Quantized output requires quantized weights; 32-bit weights ⇒ float output only. **LiteRT: locked to 32-bit probabilities.**
- **Training stop options** (Neuton only; not available for Axon/LiteRT): Max number of coefficients (default unlimited), Max training duration (hours; best model saved at limit), Max evaluation-metric value.
- **Target hardware:** one or more of **Cortex-M0, Cortex-M4, Cortex-M33** (covers the Nordic wireless SoC lineup). **LiteRT: target is fixed to Axon NPU.**
- **LiteRT/Axon training parameters:** Epochs, Batch size, Epochs-without-improvement (early stopping), **Learning rate (must be 0–1)**.
- **Input layer** size is auto-computed from columns × features × window × feature-selection (see [feature extraction](platform-feature-extraction.md)). **Output layer** by task: Regression = 1 neuron (linear); Binary = 1 neuron (softmax); Multi-class = N neurons (softmax), N = #classes.
- **Architecture (Axon/LiteRT):** presets (Fully Connected, Simple Fully Connected) or custom layers — Dense, Dropout, Flatten, Reshape, Conv1D, MaxPooling1D. Full layer params: [raw](../../raw/platform-docs/2026-06-25-pipeline-model-settings.md).

## Run inference on MCU

Deploy the trained model's inference engine to the target SoC; integration guidance and code samples are in the **Edge AI Add-on**. (Detail beyond this is background for the data-builder.)

## Run inference on desktop — the CSV runner contract ⚠️

The **nRF Edge AI Desktop Inference Runner** (in the trained solution's `artifacts/` folder) validates inference without hardware. Builds: `nrf_edgeai_inference_runner_linux` (e.g. Ubuntu 20.04), `_win` (64-bit Windows), `_mac` (x86 macOS). **Axon-built models: Linux build only.**

This runner reads the user's **test CSV**, so its defaults define how a prepared test file is interpreted:

| Setting | Default | Override flag | Notes |
|---|---|---|---|
| Delimiter | **`comma`** | `-d` / `--delimiter` | keywords: `comma`,`semicolon`,`tab`,`caret`,`vbar` → `, ; \t ^ \|` |
| Target column name | **`target`** | `-t` / `--target` | — |
| Session column name | **`session`** | `-sn` / `--session` | — |
| Save results | — | `-s` / `--save <file>` | writes results CSV |

- **CSV requirements for the runner: must have a header and contain only numeric fields** (matches the [dataset contract](platform-dataset-requirements.md)). Two input formats: `.csv` and Edge AI Lab binary `.bin`.
- `metrics` command needs the dataset to include a **`target`** column (default name).
- Commands: `info` (solution info), `inference <dataset> [-t][-sn][-d][-s]`, `metrics <dataset> [-t][-sn][-d]`.

> **Data-builder implication:** if our tool names the label column `class` (as in the gesture demo) rather than `target`, the user must pass `-t class` to the runner. The data-builder should either default the target column to **`target`** for runner-compatibility, or clearly document the `-t`/`-sn`/`-d` flags it requires.

## Observed in practice: predictions format & on-device postprocessing

From field experience:

- **Runner predictions CSV** = a `target` column (when present) + one **`Probability of 0` … `Probability of N`** column per class. This is the input to [`postprocessing_pipelines.py`](../../scripts/postprocessing/postprocessing_pipelines.py).
- **Postprocessing has a hard ceiling.** It only reshapes the model's output probabilities — if a class's max probability ≈ 0 across the data, it is dead at the model level and no threshold/smoothing/consecutive-N can recover it. Check before promising a fix → [domain P-07](../principles/domain.md).
- **Recommended default on-device postprocessing:** EMA (α≈0.3) + unknown-margin suppression (prefer the best non-"unknown" class when "unknown" wins by < ~0.2). **No** threshold, **no** consecutive-N unless a specific failure mode requires them (they hurt accuracy in practice). ~15-line C: [`firmware_postprocessing_ema_unknown_margin.c`](../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c) → [domain P-08](../principles/domain.md).
- The model archive (`nrf_edgeai_generated/`, `artifacts/inference_runner/`, the on-device 4-call API, the `FEATURES_EXTRACTION_MASK` and input-scaling clamps) is documented in [model archive](../discovery/platform-model-archive.md).

## Implementation

The desktop-runner CSV contract (target/session column names, delimiter) is honoured by [`pipeline.py`](../../src/data_builder/pipeline.py): it keeps the user's reconciled label-column name and **reports the exact `-t/-sn/-d` runner flags** rather than silently renaming. Engine: [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md). The postprocessing tooling ([`scripts/`](../../scripts/README.md)) stays reference for advising on deployment; the rest is platform/firmware (Edge AI Add-on) concern.

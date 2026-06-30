---
type: architecture
status: active
updated: 2026-06-30
implementation:
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-features.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-features.md
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-windowing.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
  - ../../scripts/diagnostics/feature_mask_decoder.py
tags: [platform, feature-extraction, features, feature-selection, fft, contract]
---

# platform — Feature extraction & selection

After [windowing](platform-signal-processing.md), the platform automatically extracts the **selected features per column (axis/variable) per window**, and extracts the **same features at inference time**. The data-builder does **not** compute these features (the platform does) — but it must understand them because they drive the input-layer size, the frequency-domain window constraint, and feature-selection behaviour.

Manage features in the UI: enable/disable individually, **Select All**, **restore defaults**, **Edit** (per-feature settings), search. Defaults are tuned for an accuracy/footprint balance.

## Counting rule (input size)

Features are extracted **per axis**. Demo: **16 features × 6 axes = 96 features per sample** — so more enabled features ⇒ more model inputs ⇒ larger model/SRAM. The model's **input-layer size is computed automatically**; the exact factors that determine it live on the [deployment/inference](platform-deployment-inference.md) page (cited there).

## Feature catalogue (by domain)

**Time-domain — Statistical:** Max, Min, Mean, Range, Absolute Mean, Standard Deviation, Mean Absolute Deviation, Root Mean Square, Kurtosis, Skewness.

**Time-domain — Regression:** Linear Regression Intercept, Linear Regression Slope.

**Time-domain — Crossing-rate:** Zero-crossing Rate, Mean-crossing Rate, Threshold-crossing Rate, Positive Sigma Crossing Rate, Negative Sigma Crossing Rate. *(Sigma-based ones have an `n`-σ setting.)*

**Time-domain — Signal shape & variation:** Crest Factor, Root Difference Square, Average Magnitude Difference, Percentage of Signal over Mean, Percentage of Signal over Zero, Percentage of Signal over Sigma, Autocorrelation.

**Time-domain — Hjorth parameters:** Hjorth Mobility, Hjorth Complexity (→1 as signal approaches a pure sine).

**Time-domain — Peak-to-peak:** Global Peak-to-Peak of High Frequencies, Global Peak-to-Peak of Low Frequencies.

**Frequency-domain (FFT-based):** Spectral analysis (Amplitude Spectrum, Spectral Centroid, Spectral Spread, Spectral Crest, Spectral RMS); Dominant Frequency features (Dominant Frequencies, Amplitudes, Mean Distance, SNR, THD); Energy-ratio features (Low/High, Low/Mid, Mid/High frequency energy ratios).

> **Frequency-domain constraint:** enabling any frequency-domain feature forces **window size = a power of 2, 128–2048 samples** (this page's features source). Related interactions from the [windowing contract](platform-signal-processing.md): the **raw-data option is incompatible** with frequency-domain features, and **sub-windowing disables frequency-domain features**. Full per-feature descriptions: [raw](../../raw/platform-docs/2026-06-25-pipeline-signal-processing-features.md).

## Feature selection (automatic pruning)

Optional; reduces dataset size / improves performance. A feature is **removed** if **any** of:

- it is **constant**;
- its **correlation with another feature is exactly 1.00**;
- it causes a **metric loss of ≥ 0.875%** (by feature importance).

Auto-enabled when sub-windowing is on (per the [windowing contract](platform-signal-processing.md); can be disabled). The gesture demo leaves it off.

## Observed in practice: direction features are load-bearing

From field experience: **`LR_SLOPE` and `LR_INTERCEPT` (Linear Regression Slope/Intercept) are the only features that encode signed asymmetry within a window** — i.e. *direction* of motion. Magnitude features (STD, RMS, MAD, RANGE, ABSMEAN) carry none; MEAN/MIN/MAX are weak. With LR features off, opposite-direction gestures (left/right, up/down) sit nearly on top of each other in feature space → the model conflates them or leaves a class dead. Enabling them recovered previously-dead direction classes in a real model. They are also **orientation-invariant**, so they're essential when training data spans multiple device orientations (per-class axis-mean sign flips). The enabled set is encoded in `FEATURES_EXTRACTION_MASK` in the model archive — decode it with [`feature_mask_decoder.py`](../../scripts/diagnostics/feature_mask_decoder.py). See [domain P-06](../principles/domain.md) and the [model archive](../discovery/platform-model-archive.md).

## Recommending the enable-set (measured separability) — a required build step

Advising "which features to enable" is not an after-thought: as part of preparing a gesture/activity dataset, **measure** which families separate the classes and recommend a full enable-set with evidence ([domain P-12](../principles/domain.md)). Method on the centered data: window per class, compute the time-domain catalogue per axis, rank by multiclass ANOVA F + per-class one-vs-rest, and for **every class pair** compute the best **magnitude-only** separation — pairs magnitude can't separate (best Cohen's-d ≲ 1) are *direction* problems, not energy problems. Map to families:

- **Energy** (Standard Deviation, Root Mean Square, Range, Mean Absolute Deviation, Absolute Mean) — rest vs active, high vs low energy. Always on.
- **Signed level + direction** (Mean, Min, Max, **Linear Regression Slope**, **Linear Regression Intercept**, Percentage of Signal over Zero, Percentage of Signal over Mean) — the only direction carriers; required for mirror/opposite classes (magnitude is direction-blind). Linear Regression Slope/Intercept are orientation-invariant.
- **Impulse/shape** (Crest Factor, Hjorth Mobility, Hjorth Complexity) — sharp/impulsive classes (taps).

Current hold-backs: **INT16 input ⇒ do not recommend Skewness/Kurtosis** (higher moments are unstable on integers; revisit for FLOAT32); **do not enable feature-selection in the first experiment** (train the advised set, test in real conditions, then prune for size only if needed); **FFT** stays off unless a power-of-2 128–2048 window is justified. Footprint: each enabled feature × every axis adds inputs, so a smaller enabled set is a smaller model — but prune by *measured importance later*, not by guessing up front.

## Implementation

The measured enable-set is produced by the reviewed diagnostic [`scripts/diagnostics/feature_separability.py`](../../scripts/diagnostics/feature_separability.py) (windowed per-class features → ANOVA-F + per-class one-vs-rest + magnitude-blind-pair detection → mapped enable-set in full platform names; deterministic, built through the task cycle — see [domain P-12](../principles/domain.md)). The data-builder otherwise does **not** compute platform features (the platform does); it needs the **frequency-domain window constraint**, the **feature-count → footprint** relationship, and the **direction-feature** insight above when advising. Authoritative source: `raw/platform-docs/`. Feature-mask decoding tool: [`scripts/diagnostics/feature_mask_decoder.py`](../../scripts/diagnostics/feature_mask_decoder.py).

---
type: architecture
status: active
updated: 2026-07-25
implementation:
  - ../../src/data_builder/window_survival.py
  - ../../src/data_builder/resample.py
  - ../../src/data_builder/validate.py
  - ../../src/data_builder/normalize.py
  - ../../src/data_builder/combine.py
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-windowing.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-signal-processing-windowing.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md
  - ../../scripts/diagnostics/window_survival_sim.py
  - ../../scripts/preprocessing/center_training_data.py
  - ../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md
tags: [platform, signal-processing, windowing, sliding-shift, sampling-rate, sram, contract]
---

# platform — Signal Processing: windowing & sampling contract

Signal Processing (SP) is the platform stage that turns a raw, time-ordered sensor CSV into per-window feature vectors (see [feature extraction](platform-feature-extraction.md)). The **windowing parameters constrain the input data** the data-builder must deliver — especially sampling rate and minimum length. Enable it by selecting **Signal Processing (SP)**; a **Guided Setup** wizard can auto-configure it, or use **Manual Setup**.

**SP is optional and off by default** — everything on this page applies only once it is switched on. Whether it *should* be on for a given dataset is a separate, upstream decision: [signal-processing applicability](platform-signal-processing-applicability.md).

Upstream contract: [dataset requirements](platform-dataset-requirements.md). Downstream: [feature extraction](platform-feature-extraction.md).

## Windowing

Windowing groups N consecutive rows ("samples") into one feature-extraction window → one training row.

- **Window size = number of samples per window.** The platform groups training rows by this count and computes features per group.
- **Window size must be identical across all events** in the dataset, regardless of event duration.
- **Training and validation datasets must use the same window size** before upload.
- **Size limits: minimum 10 samples, maximum 1,000 samples** (max is a TinyML constraint). *(Frequency-domain features override this — see below.)*

### Three ways to set the window size

1. **Time interval** — enter duration in **milliseconds (ms)** and **frequency in Hz**. → window size in samples is derived from ms × Hz.
2. **Number of rows (samples)** — set directly from domain knowledge. Example: 100 Hz sampling with ~1 s max activity → **100 rows**. (Demo uses **99 records** = ~1 s at 100 Hz.)
3. **Auto Determination** — platform picks the optimal size; you may optionally bound min/max and set a sliding-shift percentage (classification & regression only).

### Sampling-rate rule (critical for our data-builder)

> **Sensors with different frequencies must be down-/up-sampled to a single common frequency *before* upload.** Window size is expressed in samples, so a consistent Hz across the dataset is mandatory. Always record the sampling rate (Hz) per dataset.

**Our method (not a platform rule):** *how* we perform that resampling matters. Measure the real rate from the timestamps first (`1/median(diff(t))` — jitter and nominal≠actual are normal), and **anti-alias before decimation when downsampling** — plain linear interpolation onto a coarser grid aliases and silently corrupts features. Prefer downsampling toward the lowest common rate that clears Nyquist over upsampling (which fabricates resolution). Full decision procedure: [domain P-14](../principles/domain.md#p-14--resampling-is-a-decision-procedure-measure-first-anti-alias-before-downsampling-validate); the scipy-based anti-alias implementation is tracked by [ADR-0003](../decisions/adr-0003-scipy-on-resample-path.md) and spec [databuilder-008](../../specs/databuilder-008-resampling-antialias.md).

### Frequency-domain features exception

If any frequency-domain feature is enabled, **window size must be a power of 2 and between 128 and 2048 samples.** The platform warns if this is violated.

## Sliding shift (window overlap)

- **Sliding shift = how many samples the window advances** to start the next window.
- `shift == window size` → **no overlap** (consecutive windows are adjacent). Every window yields one training row regardless of overlap.
- `shift < window size` → **overlapping** windows (more training samples via augmentation).
- **`shift` cannot exceed window size.**
- Available for **both training and inference**. The *inference* sliding shift controls how often the model is queried on streaming data — e.g. shift of **33** (at 100 Hz) → ~**3 inferences/sec**.

## Sub-windowing

Splits each window into smaller sub-segments to capture local peaks/dips (useful for gesture/activity recognition). Enable via **Sub-windowing**.

- **2 to 10 sub-windows.**
- **Each sub-window ≥ 10 samples**, i.e. `window_size / num_sub_windows ≥ 10` — otherwise adjust window size or sub-window count.
- When enabled: full-window features still allowed; **frequency-domain features are disabled**; **feature selection auto-enabled** (can be turned off); **lag features (raw-data option) incompatible** — disable sub-windowing to use lag features.

## Raw data option (lag features)

- **Disabled by default.** When enabled, raw values from all variables/axes are used directly as model inputs (alongside extracted features).
- **Not available for Axon (LiteRT) technology.**
- Cannot be used when: sliding shift ≠ window size; any frequency-domain feature is enabled; or window auto-determination is enabled.

> **Commonly misread as — do not restate it this way.** This constraint is about **the lag-feature
> option only**: those three conditions are when *lag features* become unavailable. It is **not** a
> rule that enabling frequency-domain features forces the sliding shift to equal the window size. No
> such rule exists in the documentation.
>
> The misreading is easy to make and expensive: acting on it means advising **zero-overlap inference**,
> contradicting the 50–70% inference-overlap guidance in [domain P-02](../principles/domain.md), on
> exactly the long windows where overlap matters most. The FFT constraints that *do* exist are the
> window range (128–2048, power of two) and the sub-windowing incompatibility above — nothing about the
> shift. See [harvested practice](../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md).

## Normalization defaults under SP

- When SP is enabled, **Normalization type defaults to AutoSelect**.
- Extracted features are normalized **within their own scale**; raw sensor data is normalized **separately per variable and per axis**. (More options: [preprocessing options](platform-preprocessing-options.md).)

## Estimated SRAM usage

- The platform estimates on-device **SRAM** from window size + selected features; the **actual** figure is known only **after training + compilation**.
- For Auto-Determination window mode, the SRAM estimate appears **only after training**. (No fixed numeric SRAM thresholds are stated in the docs.)

## Why this matters to the data-builder

The data-builder cannot fix window/shift settings (those are chosen in the platform UI), but it **must deliver data compatible with them**:
- single, consistent sampling rate (resample if mixed) and record it;
- enough consecutive rows per event to fill a window (≥10; ≥128 for frequency-domain);
- intact, unshuffled time order with a label per row;
- session boundaries marked (Session ID) so windows don't cross sessions — **sessions shorter than the window are dropped automatically**.

## Observed in practice (field scenarios — not documented platform rules)

From field experience; treat as working models, verify against the platform's "Processed Data" view:

- **Mixed-label windows don't survive.** The platform emits one label per window; a window spanning a label boundary appears to be dropped. So a class whose **longest contiguous run < window size produces zero windows** and silently disappears ("data removed" / "label has no data"). Diagnose with [`window_survival_sim.py`](../../scripts/diagnostics/window_survival_sim.py) → [domain P-01](../principles/domain.md). (Strict-pure assumption; the platform might instead keep majority-label windows.)
- **Set the training sliding shift = window size.** Small training shifts over-sample the dominant (idle) class and create severe imbalance. Reserve overlap for inference → [domain P-02](../principles/domain.md).
- **Centering for discrete gestures.** When a project centers gestures before training, the gesture peak must sit mid-window; idle/"unknown" stay raw; center per-class, never across boundaries. Verify with [`check_signal_centered.py`](../../scripts/diagnostics/check_signal_centered.py), produce with [`center_training_data.py`](../../scripts/preprocessing/center_training_data.py) → [domain P-05](../principles/domain.md).

## Implementation

Window-survival simulation in [`window_survival.py`](../../src/data_builder/window_survival.py) and single-rate resampling in [`resample.py`](../../src/data_builder/resample.py) (gesture centering in `center.py`). Resampling **anti-aliases downsampling** (`scipy.signal.resample_poly`, `padtype='line'`, per contiguous run; upsample stays `numpy.interp`); a run too short to filter cleanly, or a missing scipy on a downsample, is **refused** (FIX_REQUIRED) rather than shipping aliased data — [ADR-0003](../decisions/adr-0003-scipy-on-resample-path.md), [domain P-14](../principles/domain.md#p-14--resampling-is-a-decision-procedure-measure-first-anti-alias-before-downsampling-validate), databuilder-008. The broader measure-first/auto-select/jitter+gap procedure (rest of P-14) is a deferred follow-up. Engine: [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md). The strict-pure window-survival model remains an **upper bound** — findings are framed to verify against the platform's Processed Data view. The harvested diagnostic/centering scripts in [`scripts/`](../../scripts/README.md) stay as reference tooling.

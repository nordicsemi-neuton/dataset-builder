---
type: synthesis
status: active
updated: 2026-07-23
sources:
  - ../principles/domain.md
  - ../principles/process.md
  - ../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md
  - ../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md
tags: [synthesis, troubleshooting, checklist, symptom, support]
---

# Troubleshooting checklist — fast symptom→cause triage

**What this is:** a quick first-pass for common platform data-prep complaints, "cheapest to check first," each pointing to the canonical rule. For deep investigation use the [diagnostic playbook](support-diagnostic-playbook.md); for the underlying rules see [domain](../principles/domain.md) / [process](../principles/process.md) principles; for the documented contract see [`architecture/platform-*`](../architecture/platform-dataset-requirements.md). Abstracted from common field scenarios (field experience).

## Symptom → first thing to check

| User says | Check first | Canonical |
|---|---|---|
| "Data is removed during preprocessing" / "a label has no data" | Per-(session,label) run lengths vs window; a class with max-run < window produces zero pure windows | [domain P-01](../principles/domain.md), [playbook §3–4](support-diagnostic-playbook.md) |
| "A label is missing in the platform" | Stated mapping vs actual unique values; labels must be contiguous 0..N-1 | [domain P-03](../principles/domain.md) |
| "Different labels have different counts than I expected" | Sliding shift vs window — heavy overlap inflates the dominant (idle) class | [domain P-02](../principles/domain.md) |
| "Can't get good results on device" (multi-class gesture) | Decode feature mask; check per-class max-prob (dead classes?) | [domain P-06,P-07](../principles/domain.md) |
| "Model confuses left/right or up/down" | Feature mask — are `LR_SLOPE`/`LR_INTERCEPT` enabled? | [domain P-06](../principles/domain.md) |
| "I tried thresholding/smoothing, still bad" | Per-class max-prob — if ≈0, the class is dead; postprocessing can't help | [domain P-07](../principles/domain.md) |
| "Gyro shows ±saturation spikes in test only" | Median-Δ per axis (train vs test); "3 identical clipped samples" = sample-and-hold; check IMU full-scale-range register | [case patterns](support-case-patterns.md) |
| "Is this new data centered / should we re-center?" | `check_signal_centered.py`; if RAW for gesture classes, center per-class | [domain P-05](../principles/domain.md) |
| "Per-class accel mean flipped sign between sessions" | Different device orientation → enable orientation-invariant LR features | [domain P-06](../principles/domain.md) |
| "Should we add a median/low-pass filter on device?" | Training-vs-inference artifact-rate parity FIRST | [domain P-09](../principles/domain.md) |
| "L/R confusion in eval — model bug?" | Confirm which direction was executed first (protocol error?) | [process P-06](../principles/process.md) |
| "Best postprocessing pipeline?" | Default EMA α≈0.3 + unknown-margin suppression; add nothing else unless needed | [domain P-08](../principles/domain.md) |
| **"100% of my data was removed"** / "all sessions smaller than the window" | **Which column is set as Target?** A column that is unique per row (a timestamp) gives no window a consistent label, so every window is invalid — the platform reports this as sessions being too small, which points at the wrong cause. Then check run lengths | [domain P-01](../principles/domain.md), [signal processing](../architecture/platform-signal-processing.md) |
| **"A class is never predicted"** | Did it have **any validation windows**? An automatic split can leave a class with zero, which mimics a dead class but is an evaluation artefact with the opposite fix (supply a holdout, don't collect data) | [domain P-25, P-16](../principles/domain.md) |
| **`region 'RAM' overflowed` at compile/link** | **Dataset width.** The platform treats every non-target column as a sensor, so a wide/flattened layout multiplies the on-device window buffer: `window × columns × bytes_per_sample`. Long format (one row per timestep) is the contract | [dataset requirements](../architecture/platform-dataset-requirements.md), [signal processing](../architecture/platform-signal-processing.md) |
| "My windowed model trains well but replays badly" | **Is this a windowed-signal problem at all?** If one row is a complete observation, Signal Processing should be off. Run the single-row baseline before anything else | [SP applicability](../architecture/platform-signal-processing-applicability.md), [process P-12, P-13](../principles/process.md) |
| "Where are the window/shift/feature settings?" | **Signal Processing is off by default** — those settings only exist once it is switched on | [SP applicability](../architecture/platform-signal-processing-applicability.md) |

## Staged checklist (by pipeline stage)

**Upload fails.** Encoding UTF-8/ISO-8859-1 (no BOM weirdness); filename `[A-Za-z0-9_-]` only; one consistent separator (`,` `;` `|` `^` tab); CRLF/LF consistent; header row, unique `[A-Za-z0-9_-]` names; **no row-index column** (common pandas-export mistake); no empty / `NA` / `NAN` / `null` / `?` / `inf`; all numeric; EN-US locale (dot decimal, no thousands sep, no units in cells); dates as epoch/relative. → [dataset requirements](../architecture/platform-dataset-requirements.md).

**"Class samples insufficient" / training won't start.** Labels contiguous from 0; ≥20 samples/class; target column actually selected. → [dataset requirements](../architecture/platform-dataset-requirements.md).

**"Lost rows after configuration."** Session ID set with sessions shorter than the window (dropped silently)? → [data pipeline](../architecture/platform-data-pipeline.md).

**Window/feature errors.** "Window must be power of 2" → a frequency-domain feature is on with a non-conforming window (use 128/256/512/1024/2048 or disable freq features); "Raw data greyed out" → one of its blockers (shift≠window, freq feature, auto-window, sub-windowing, or Axon); "Sub-windowing complains" → `window/n_sub ≥ 10`, `n_sub ∈ [2,10]`. → [signal processing](../architecture/platform-signal-processing.md).

**"Model too big for my MCU."** Wrong input data type (e.g. FLOAT32 when data is INT16 — and check whether a handful of corrupt rows drove that recommendation, [domain P-23](../principles/domain.md)); wrong weight bit depth; quantized output not selected; too many features (enable feature selection); **too many input columns** — a wide/flattened layout multiplies the window buffer and can overflow RAM at link time rather than at upload; LiteRT is larger by design. → [preprocessing options](../architecture/platform-preprocessing-options.md) / [deployment](../architecture/platform-deployment-inference.md).

**"Accuracy poor / overfits."** Class imbalance with Accuracy metric → use Balanced Accuracy / weighted F1 (and quote imbalance **by surviving window**, not by row — [domain P-17](../principles/domain.md)); data too little or homogeneous → more, more diverse, more users; wrong window vs longest gesture; **missing idle/unknown class**; unrepresentative split → supply a holdout chosen by what it must prove ([domain P-16](../principles/domain.md)). If one class over-predicts at ~half precision, suspect a sink class rather than a settings gap ([domain P-20](../principles/domain.md)). For a continuous target, compare against the null model before judging anything ([domain P-24](../principles/domain.md)). → [preprocessing options](../architecture/platform-preprocessing-options.md), [domain P-10](../principles/domain.md).

**"False detections after deployment."** Add an **unknown** class with the user's real non-target activities; retrain (canonical iteration loop). → [domain P-10](../principles/domain.md).

**Inference-runner errors.** Axon model + Windows/macOS runner → Linux-only for Axon; wrong CSV header/order/target name → use `-t` / `-sn` / `-d`; "different input shape" → test must match training in column order, types, separator, locale. → [deployment/inference](../architecture/platform-deployment-inference.md).

**Holdout fails.** Not a structural match of training (names, order, types, separator, encoding); anomaly-detection task → holdout unsupported, validate with two CSVs. → [task types](../discovery/platform-task-types.md).

**Wake word won't trigger / over-triggers.** Word too common/short/long or non-English; browser-tuned threshold/period not ported to firmware; stopping mid-training discards progress. → [task types](../discovery/platform-task-types.md).

**Anomaly: "everything is anomalous."** Training set wasn't pure-normal (check the cosine-distance plot for contamination); too small/uniform. → [task types](../discovery/platform-task-types.md).

> Firmware setup, drivers, BLE/HID, on-device thresholding, sample apps → the separate **Edge AI Add-on** docs, not the Edge AI Lab docs ([model archive notes](../discovery/platform-model-archive.md)).

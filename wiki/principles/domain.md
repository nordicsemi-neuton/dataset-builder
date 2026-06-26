---
type: principles
status: active
updated: 2026-06-25
sources:
  - Field experience (practitioner knowledge; no external source document).
  - ../../scripts/diagnostics/window_survival_sim.py
  - ../../scripts/diagnostics/feature_mask_decoder.py
  - ../../scripts/preprocessing/center_training_data.py
  - ../../scripts/postprocessing/postprocessing_pipelines.py
  - ../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c
  - ../../scripts/firmware/firmware_median3_filter.c
tags: [principles, domain, signal, windowing, features, postprocessing, gesture]
---

# Domain principles — inertial data preparation & modeling

Rules drawn from field experience with common data-prep scenarios. These are **experiential**, validated on limited data; the documented platform contract is in [`architecture/platform-*`](../architecture/platform-dataset-requirements.md). Read before any non-trivial data-prep task. Worked anatomies: [case patterns](../synthesis/support-case-patterns.md). How to investigate: [process principles](process.md) + [diagnostic playbook](../synthesis/support-diagnostic-playbook.md).

## P-01 — Each class needs contiguous runs ≥ the window size, or it vanishes

**Rule:** Structure recordings so every gesture has contiguous label runs at least as long as the window size; prefer **isolated sessions per gesture**, concatenated afterward.
**Why:** The platform emits one feature vector + one label per window. A window spanning a label boundary does not survive as a clean sample (working assumption: dropped; it may instead be majority-labeled — verify against the "Processed Data" view). A class whose **longest contiguous run < window size** can produce **zero** pure windows and silently disappears — the user sees "this label has no data."
**When to apply:** any "data is removed" / "label has no data" symptom; before choosing a window size.
**Precedent:** a multi-class IMU gesture dataset where one class's longest run (140 rows) was below the window (150) → that class produced zero windows.
**Source:** field experience (practitioner knowledge); [`window_survival_sim.py`](../../scripts/diagnostics/window_survival_sim.py), [`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py).

## P-02 — Training sliding-shift = window size; heavy overlap is an inference-only tool

**Rule:** For training, set sliding shift equal to the window (non-overlapping samples). Reserve small shifts (heavy overlap) for inference, where they raise query frequency.
**Why:** A small training shift massively over-samples whichever class has the longest continuous runs (usually idle), producing extreme imbalance that masquerades as "data removal."
**Precedent:** shift=10 with window=150 left ~99.7% of surviving windows in the idle class.
**Source:** field experience (practitioner knowledge); see [signal-processing contract](../architecture/platform-signal-processing.md).

## P-03 — Labels must be contiguous from 0; reconcile the stated mapping against the actual data

**Rule:** Verify class labels are integers `0..N-1` with no gaps, and **cross-check the user's described class mapping against the actual unique values** in the label column.
**Why:** The platform requires contiguous-from-0 encoding; users frequently skip a value or carry an unmapped extra class without noticing.
**Precedent:** a user described five classes `0,1,2,4,5`; the data actually held six (`0,1,2,3,4,5`) including an unmapped class.
**Source:** field experience (practitioner knowledge); [dataset requirements](../architecture/platform-dataset-requirements.md).

## P-04 — One sampling rate across all sessions; resample before upload

**Rule:** Ensure every session shares a single sampling rate; resample (up/down) to a common Hz before upload, and always record the rate.
**Why:** The window is defined in rows, so mixed sampling rates mean the same window covers different physical durations per session → inconsistent features for the same gesture.
**Precedent:** one dataset mixed sessions at 244 Hz and 199 Hz; window=150 then meant 0.62 s vs 0.75 s.
**Source:** field experience (practitioner knowledge); [`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py).

## P-05 — Center discrete gestures; keep continuous classes raw; never center across class boundaries

**Rule:** For discrete-gesture classes, center each sample so the motion peak sits near the middle of the window. Leave continuous classes (idle, "unknown", rotations) as raw streams trimmed to a window multiple. Run peak detection **per class**, never across a multi-class file (peaks would straddle boundaries).
**Why:** The platform windows statically, so a gesture must occupy the position the trained features expect. Raw and centered datasets are not comparable for feature analysis. Verdicts: peak-position std small ⇒ CENTERED; mid-range ⇒ LOOSE (normal for tap); large/uniform ⇒ RAW (or a continuous class).
**When to apply:** any "is this data centered / should we re-center it?" question; before comparing feature distributions across datasets.
**Source:** field experience (practitioner knowledge); [`center_training_data.py`](../../scripts/preprocessing/center_training_data.py), [`check_signal_centered.py`](../../scripts/diagnostics/check_signal_centered.py).

## P-06 — Direction discrimination requires LR_SLOPE / LR_INTERCEPT (the only signed-asymmetry features)

**Rule:** For directional gestures (left/right, up/down), enable `LR_SLOPE` and `LR_INTERCEPT`. If per-class axis means flip sign between recording sessions (different device orientation), these become essential because they are orientation-invariant.
**Why:** Magnitude features (STD, RMS, MAD, RANGE, ABSMEAN) encode no direction; MEAN/MIN/MAX are weak. Slope/intercept are the only features capturing signed asymmetry within a window. Without them, opposite-direction gestures are nearly co-located in feature space → the model conflates them or leaves a class dead.
**Precedent:** an 8-class gesture model had two dead classes — one a *direction* class (swipe-left) and one a *fragile-magnitude-signature* class (tap, whose level barely exceeded idle). Retraining recovered both, but via a **bundle** of changes (LR_SLOPE/LR_INTERCEPT enabled **+** ~2× model capacity **+** recollected/merged data with sharper taps). Credit the LR features specifically for the **direction** recovery; the tap class's fix was mainly capacity + better samples — so this rule is about *direction*, not a claim that LR features alone fix every dead class.
**Source:** field experience (practitioner knowledge); [`feature_mask_decoder.py`](../../scripts/diagnostics/feature_mask_decoder.py); [feature extraction](../architecture/platform-feature-extraction.md).

## P-07 — Postprocessing has a hard ceiling at the model output

**Rule:** Before promising any postprocessing fix (threshold / smoothing / consecutive-N / majority-vote), check per-class **max probability** across the user's data. If a class's max prob ≈ 0 everywhere, it is **dead at the model level** — no postprocessing can create detections. Fix by retraining (more/better data, direction features, more capacity) or by removing the class.
**Why:** Postprocessing only reshapes existing probabilities; it cannot invent signal that the model never emits.
**Precedent:** a model with two classes at max-prob 0.06 and 0.0 — every postprocessing pipeline left them at zero detections; only retraining recovered them.
**Source:** field experience (practitioner knowledge); [`postprocessing_pipelines.py`](../../scripts/postprocessing/postprocessing_pipelines.py).

## P-08 — Default on-device postprocessing: EMA + unknown-margin suppression, nothing more

**Rule:** Start with **EMA smoothing (α ≈ 0.3)** of the probability vector + **unknown-margin suppression** (if the "unknown" class wins by < ~0.2 over the best real class, pick the real class). **No** confidence threshold and **no** consecutive-N gate unless a specific observed failure mode demands them.
**Why:** On real eval data, adding a threshold or consecutive-N on top of EMA consistently *hurt* accuracy by dropping legitimate detections. Simplicity won (≈80% strict / ≈87% direction-agnostic, zero idle/random false positives).
**When to apply:** designing device-side prediction handling for a multi-class gesture model. For one event per gesture (not per-window state), layer a state-change detector on top.
**Source:** field experience (practitioner knowledge); [`firmware_postprocessing_ema_unknown_margin.c`](../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c), grid search in [`postprocessing_pipelines.py`](../../scripts/postprocessing/postprocessing_pipelines.py).

## P-09 — Preprocessing parity: never filter only at inference

**Rule:** Do not add a firmware-side signal filter (median, low-pass, deadband) at inference unless the **training data was processed the same way**. Audit artifact rates first: if training vs inference artifact rates are comparable (within ~2×), don't filter; if they diverge strongly (≈5×+), either filter **both** sides and retrain, or skip — never inference-only.
**Why:** Inference-only preprocessing is a deliberate train/inference distribution shift that quietly degrades accuracy, and can suppress artifacts (e.g. natural gyro saturation during fast motion) that are part of a gesture's learned signature.
**Precedent:** a 3-tap gyro median filter was recommended, then retracted after auditing (training 0.62% vs eval 0.96% jump rate — comparable, so filtering would only shift the distribution).
**Source:** field experience (practitioner knowledge); [`firmware_median3_filter.c`](../../scripts/firmware/firmware_median3_filter.c) (read its parity warning).

## P-10 — Always include an idle / "unknown" class to prevent false detections

**Rule:** For gesture/event models, include an **idle** class and an **"unknown"** ("none of the above") class, the latter populated with the user's real non-target activities. Idle/unknown are continuous streams (not centered — see P-05).
**Why:** Without a catch-all, every input is forced into a gesture class, producing constant false detections in normal use. This is the canonical iteration loop: deploy → observe false triggers → add their patterns to "unknown" → retrain.
**Source:** field experience (practitioner knowledge); [data-collection practices](../discovery/platform-data-collection-practices.md).

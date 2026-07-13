---
type: principles
status: active
updated: 2026-07-10
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

**Rule:** For **training**, set sliding shift equal to the window (non-overlapping samples). For **inference** (gesture/activity recognition), always recommend an **overlapping** shift — **50–70% overlap** (shift ≈ 30–50% of the window) so a gesture isn't missed between queries; the exact overlap depends on the gesture/activity duration and variability (shorter/faster ⇒ more overlap). Heavy overlap is an inference tool, never a training one.
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

## P-11 — Reconcile sensor *scale* across sources; gravity-at-rest is the probe, but motion invalidates it

**Rule:** Treat each source's/file's sensor **scale** (accelerometer full-scale range or units) as a claim to reconcile against the data, alongside rate and labels ([P-03](#p-03--labels-must-be-contiguous-from-0-reconcile-the-stated-mapping-against-the-actual-data), [P-04](#p-04--one-sampling-rate-across-all-sessions-resample-before-upload)). The recordings of one dataset can silently mix scales — e.g. ±2g raw counts (gravity ≈16384), ±4g (≈8192) and physical units (m/s²×1000, gravity ≈9810). Probe each file's scale by its **gravity magnitude** `|acc| = √(ax²+ay²+az²)` at rest (= 1 g in that file's units). Bring **every** source onto the **one** scale the inference device emits, or exclude the mismatched files; never train a class across mixed scales. Calibrate from gravity only what gravity touches — the **accelerometer**; the **gyroscope reads ~0 at rest**, so it has no at-rest scale reference and an acc-only gravity rescale can leave the gyro mismatched — prefer re-export/exclude over a partial rescale.
**Ask up front (don't infer):** at the framing stage ask the user the **accelerometer full-scale** (±2g / 4g / 8g / 16g) and the **gyroscope full-scale in dps** (125 / 250 / 500 / 1000…). These fix counts-per-g and counts-per-dps, which lets you (a) keep the data as **raw INT16 and never convert it to floats** — the platform consumes raw integers, conversion only loses fidelity and footprint; (b) sanity-check scale and segment rest vs motion (at rest `|acc|` ≈ 1 g in counts **and** gyro ≈ 0). Record both in the profile (`accel_full_scale_g`, `gyro_full_scale_dps`).
**Method caveat (load-bearing):** the gravity probe is valid **only where the device rests**. In continuous motion (rotations, walking, vigorous gestures) linear acceleration adds to or opposes gravity, so `|acc|` swings around 1 g and a low-percentile estimate dips far below it — falsely flagging a physical-scale file as a smaller-range scale. Use the **histogram mode** (the baseline the signal returns to) and **validate the probe against known-at-rest sources** before trusting it. A file with no rest at all (continuous spin) is **undeterminable** from `|acc|`; infer its scale from rest-containing files of the **same capture session** rather than excluding it on a motion artifact.
**Why:** time-domain features (STD, RMS, RANGE, MEAN…) are scale-dependent, and the platform normalizes **per-axis globally**, which does **not** realign per-file scale differences *within* a class. At inference the device streams one scale, so off-scale training data — especially the idle/"unknown" background and the near-miss negatives — represents input the device never produces and teaches the wrong boundary. Same train/inference-consistency logic as [P-04](#p-04--one-sampling-rate-across-all-sessions-resample-before-upload) (one rate) and [P-09](#p-09--preprocessing-parity-never-filter-only-at-inference) (one preprocessing).
**When to apply:** combining multi-source / multi-file recordings; any "background misbehaves / false detections at inference" with mixed capture provenance; before centering or feature analysis (mixed scales corrupt both).
**Precedent:** an 8-person wrist-gesture dataset — gesture captures uniform at gravity ≈9810 (physical), but the idle/unknown background mixed all three scales; only ~28% of background matched the gestures. A 5th-percentile `|acc|` probe falsely flagged the continuous rotation classes as off-scale (motion, not scale); a mode-based probe **validated against the at-rest idle files** (which split cleanly 6/7/7 across ±2g/±4g/physical) corrected it. Off-scale background was excluded for a consistent first build, with the dropped near-miss negatives queued for re-export in the gesture units.
**Source:** this session (30.06.2026); field experience (practitioner knowledge). See [process P-03](process.md) (reconcile claims) and [case patterns](../synthesis/support-case-patterns.md).

## P-12 — Recommend the feature enable-set from a measured separability pass (and what to hold back)

**Rule:** When preparing a multi-class gesture/activity dataset — **not only after training** — run a **measured feature-separability pass** on the centered data and recommend a concrete platform enable-set with evidence; never just assert a feature or two. Method: window per class, compute the platform's time-domain catalogue per axis, rank by multiclass separability (ANOVA F) and per-class one-vs-rest, and for **every class pair compute the best magnitude-only separation** — pairs that magnitude can't separate (best magnitude Cohen's-d ≲ 1) are *direction/sign* problems, not energy problems. Map the evidence to platform families:

- **Energy/magnitude** (Standard Deviation, Root Mean Square, Range, Mean Absolute Deviation, Absolute Mean) — separates rest/background from active, and high- from low-energy gestures. Always include.
- **Signed level + direction** (Mean, Min, Max, **Linear Regression Slope**, **Linear Regression Intercept**, Percentage of Signal over Zero, Percentage of Signal over Mean) — the only features carrying *direction*; required whenever opposite/mirror classes exist (left/right, up/down, CW/CCW). Magnitude features are **direction-blind**. Linear Regression Slope/Intercept are additionally **orientation-invariant** ([P-06](#p-06--direction-discrimination-requires-lr_slope--lr_intercept-the-only-signed-asymmetry-features)).
- **Impulse/shape** (Crest Factor, Hjorth Mobility, Hjorth Complexity) — isolates sharp/impulsive classes (taps) that energy features miss.

**Hold back (current defaults):**

- **INT16 input ⇒ do not recommend Skewness or Kurtosis** (higher-moment features are unstable/noisy on integer data); the other signed features still carry direction. Revisit if storage moves to FLOAT32.
- **Do not enable the platform's feature-selection in the first experiment.** First train with the advised set and **test in real conditions**; only if optimization is then needed, re-run the *same* experiment **with** feature-selection to prune for size. Pruning before seeing real behaviour can drop a feature deployment needs.
- **Frequency-domain (FFT)** features need a power-of-2 window in 128–2048 ([feature page](../architecture/platform-feature-extraction.md)); don't switch windows just to unlock them unless time-domain separability is insufficient.

**Why:** the platform extracts and (optionally) selects features itself, but *which families are enabled* is the user's lever. A measured pass turns "enable the direction features" into an evidence-backed full set and catches the magnitude-blind pairs that silently conflate; the INT16 and first-experiment cautions avoid two common ways an early model is led astray (unstable moments, premature pruning).
**When to apply:** preparing any multi-class gesture/activity dataset (a required step of the build, [feature-advice](../../.claude/skills/feature-advice/SKILL.md)); any "which features should I enable / why don't classes separate?" question.
**Precedent:** the 8-person wrist-gesture build — magnitude-only Cohen's-d ≈ 0.5 on left/right, up/down and CW/CCW (blind); direction lived in signed level (acc_z mean for up/down, gyro_x mean for rotation) and gyro_y asymmetry (Percentage of Signal over Zero/Mean for left/right); double-thumb-tap isolated by Hjorth Mobility; INT16 ⇒ Skewness/Kurtosis held back.
**Source:** this session (30.06.2026); field experience (practitioner knowledge); [feature extraction](../architecture/platform-feature-extraction.md). Related: [P-02](#p-02--training-sliding-shift--window-size-heavy-overlap-is-an-inference-only-tool) (inference overlap), [P-06](#p-06--direction-discrimination-requires-lr_slope--lr_intercept-the-only-signed-asymmetry-features).

## P-13 — The platform's selected metric is evaluation-only; it never changes what Neuton optimizes

**Rule:** Never claim (or advise a user) that switching the platform's selected metric (e.g. Accuracy →
Balanced Accuracy / weighted F1) will change training behaviour, push the model to try harder on weak/rare
classes, or affect an automatic-stopping decision. **Neuton's internal optimization always minimizes
cross-entropy loss, regardless of which metric is selected in the UI.** The selected metric is computed
and shown for the user's evaluation/interpretation only — it plays no role in the training loop itself.
**What a metric change *is* good for:** correctly reading results the user already has (an improvement on
a small class can be invisible in plain Accuracy against big background classes) — advise it for that,
never as a lever expected to change the next training run's outcome.
**Why:** [the Neuton framework page](../discovery/platform-neuton-framework.md) states training/validation/
model-selection happen "automatically" from **(data, target, metric)**, which reads as if metric were a
training input on the same footing as data — it is not; only data and target shape what the network
learns. Metric is the third input in the sense of "what to report and compare across models," not "what
loss to descend." Getting this backwards produces a plausible-sounding but wrong diagnosis and a wasted
retrain.
**When to apply:** any "why didn't accuracy improve on an imbalanced dataset" diagnosis, before recommending
a metric change as a fix (as opposed to a measurement improvement); any explanation of what Neuton's
automatic training actually does.
**Precedent:** a remote-control gesture case (imbalance widened by new data, weakest class "up" showing no
improvement) — the metric-affects-training explanation was floated as part of the diagnosis and forwarded
in a draft customer recommendation, then corrected by the owner (direct platform knowledge: metric
selection is evaluation-only, optimization is always cross-entropy) before it reached the customer. The
imbalance finding itself stood independent of this — cross-entropy summed over an imbalanced training set
still gives more total gradient mass to the frequent classes, so imbalance remains a real, separate
concern; only the "changing the metric will fix it" mechanism was wrong.
**Source:** this session (10.07.2026); owner-supplied platform knowledge (direct, not from the doc bundle).
Related: [P-12](#p-12--recommend-the-feature-enable-set-from-a-measured-separability-pass-and-what-to-hold-back).

---
type: principles
status: active
updated: 2026-07-23
sources:
  - Field experience (practitioner knowledge; no external source document).
  - ../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md
  - ../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md
  - ../../scripts/diagnostics/window_survival_sim.py
  - ../../scripts/diagnostics/feature_mask_decoder.py
  - ../../scripts/preprocessing/center_training_data.py
  - ../../scripts/postprocessing/postprocessing_pipelines.py
  - ../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c
  - ../../scripts/firmware/firmware_median3_filter.c
tags: [principles, domain, signal, windowing, features, postprocessing, gesture, holdout, evaluation, regression]
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

**Rule:** Ensure every session shares a single sampling rate; resample to a common Hz before upload, and always record the rate. **Measure the actual rate from timestamps** (`1/median(diff(t))`) — do not trust the nominal rate in metadata (real logs jitter, and the true rate often drifts from the declared one). Prefer the **lowest common rate that still clears Nyquist** for the signal and **downsample** toward it; **never upsample low-rate files just to match high-rate ones** (that fabricates resolution the sensor never captured). *How* to resample safely — anti-aliasing, jitter handling, method choice, validation — is [P-14](#p-14--resampling-is-a-decision-procedure-measure-first-anti-alias-before-downsampling-validate).
**Why:** The window is defined in rows, so mixed sampling rates mean the same window covers different physical durations per session → inconsistent features for the same gesture.
**Precedent:** one dataset mixed sessions at 244 Hz and 199 Hz; window=150 then meant 0.62 s vs 0.75 s.
**Source:** field experience (practitioner knowledge); [`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py). Directional/anti-alias sharpening: embedded-engineer notes ([raw](../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md), 13.07.2026).

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
**When to apply:** preparing any multi-class gesture/activity dataset (a required step of the build, [feature-advice](../../.claude/skills/nrf-feature-advice/SKILL.md)); any "which features should I enable / why don't classes separate?" question.
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

## P-14 — Resampling is a decision procedure: measure first, anti-alias before downsampling, validate

**Rule:** Treat resampling as a *decision procedure*, not a single interpolation call. First separate two problems that both appear in real logs and need different handling:

- **Different nominal rates** across files (e.g. some at 100 Hz, some at 128 Hz) → *rational resampling* to a common rate.
- **Non-uniform / jittery timestamps** (jitter, dropped samples, a real rate that drifts from the nominal) → *interpolation onto a uniform grid at the true times*.

Almost every real dataset has **both**, so **step 1 is always to measure the actual rate from timestamps (`1/median(diff(t))`) and check uniformity** — never trust the nominal rate ([P-04](#p-04--one-sampling-rate-across-all-sessions-resample-before-upload)). Then apply, in order:

1. **Target rate = lowest common rate that still clears Nyquist** for the signal (human-motion energy is mostly < ~15–20 Hz; sharp taps/impacts reach ~50 Hz, so 50–100 Hz has margin). **Downsample high-rate files toward it; never upsample low-rate files for "uniformity"** — you cannot restore information the sensor never captured, only fabricate its illusion.
2. **Downsampling requires an anti-alias filter *before* decimation.** Taking every N-th sample — or interpolating straight onto the coarse grid, which is what a plain `numpy.interp` does — folds frequencies above the new Nyquist back into the band (aliasing) and silently corrupts the platform's statistical features (it looks like mysteriously degraded features on classification). Use `scipy.signal.decimate` (integer factor) or `resample_poly` (fractional); both filter internally ([ADR-0003](../decisions/adr-0003-scipy-on-resample-path.md) permits scipy on this path).
3. **Order of operations for non-uniform data being downsampled** (easy to violate): interpolate onto a uniform grid **at the source (high) rate first**, *then* anti-alias + `resample_poly` down to the target. Interpolating directly onto the low grid skips the anti-aliasing entirely.
4. **Upsampling = interpolation + imaging protection.** `resample_poly` is spectrally cleaner than a spline; a **cubic spline overshoots on sharp peaks**, so for impact/shock gestures prefer **linear** interpolation, and poly/sinc for smooth signals.
5. **Keep labels in time (seconds), not row indices,** and resample every channel on the **one** grid (axis sync). Recompute event boundaries at the end (`new_index = round(t_sec · target_rate)`); our engine already achieves this by resampling per contiguous same-label run and re-labeling the new grid — preserve that.
6. **Validate every file after resampling:** duration preserved (`n_new ≈ duration · target_rate`); PSD before/after shows no energy above the new Nyquist after a downsample; a visual overlay of a signal slice; labels still land on real events. **Record per file:** measured source rate, target rate, method, filter params, and direction (up/down) — for reproducibility.

**Why:** Aliasing from unfiltered decimation is invisible in the CSV but shows up as degraded features and accuracy — the worst kind of silent corruption for a tool shipped to third parties (the exact failure [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md) refuses to ship). Upsampling for uniformity manufactures data; getting the operation order wrong disables the anti-aliasing you added. These are standard DSP facts, not platform rules.
**When to apply:** any dataset with mixed or jittery sampling rates; before choosing a window size (counted in samples, so it depends on the final rate); designing or reviewing the resampling path in [`resample.py`](../../src/data_builder/resample.py).
**Precedent:** an embedded engineer's review of the current `resample.py`, which resampled via a bare `numpy.interp` straight onto the target grid — correct for upsampling and label alignment, but with **no anti-aliasing on the downsample path** (silent aliasing) and no rate-measurement / jitter / provenance step. Drove [ADR-0003](../decisions/adr-0003-scipy-on-resample-path.md) and spec [databuilder-008](../../specs/databuilder-008-resampling-antialias.md).
**Source:** embedded-engineer notes ([raw](../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md)); this session (13.07.2026). Related: [P-04](#p-04--one-sampling-rate-across-all-sessions-resample-before-upload), [signal-processing contract](../architecture/platform-signal-processing.md).

## P-15 — Establish each class's real-world physical meaning before any class-nature-dependent step

**Rule:** Before centering — or any step that depends on *what a class is* — get the user to state, in plain physical terms, the real-world motion each class represents, and confirm it in one batched pass (a table: *class → physical description → continuous or discrete*). This human-confirmed meaning is the required input **upstream of three later decisions, not one**: the continuous/discrete centering split ([P-05](#p-05--center-discrete-gestures-keep-continuous-classes-raw-never-center-across-class-boundaries)); whether opposite/mirror pairs exist that need the signed **direction features** ([P-06](#p-06--direction-discrimination-requires-lr_slope--lr_intercept-the-only-signed-asymmetry-features) / [P-11](#p-11--reconcile-sensor-scale-across-sources-gravity-at-rest-is-the-probe-but-motion-invalidates-it)); and whether an **idle/"unknown"** class is present ([P-10](#p-10--always-include-an-idle--unknown-class-to-prevent-false-detections)). **Never infer a class's nature from its filename, its column name, or a demo/example preset** — a class named "rotate" reads like a discrete gesture but is a continuous stream, and you cannot pre-judge which names mislead without the description, which is why you ask about *every* class, not only the suspicious ones. Make the confirmation **structural** (an explicit stop the flow cannot skip, echoed back for approval), because the failure mode is a *glossed* gate, not a missing one.
**Why:** Centering is default-on and class-nature-dependent: send a continuous class into it and its "peak" never sits mid-window (P-05); miss a mirror pair and the direction features that separate it are never enabled (P-06/P-11); forget the idle/unknown design and you invite false detections (P-10). All of that is decided from the physical meaning, so getting the meaning wrong silently poisons the split, the feature recommendation, and the false-detection design at once — the worst kind of error for a tool shipped to third parties.
**When to apply:** any classification/gesture dataset before centering or feature-separability analysis; whenever a profile arrives with a `gesture_classes`/`continuous_classes` split already filled in (confirm it, do not trust it). Not applicable to regression (no classes) or anomaly detection (unlabeled) — skip cleanly.
**Precedent:** a real `build-dataset` run centered a dataset without ever asking the physical meaning of each class or the continuous/discrete split — the Stage 0 "hard gate" existed only as prose and was walked past to the auto-centering `prep`. Drove [skills-007](../../specs/skills-007-class-nature-gate.md): the gate became a structural always-stop with a batched echo-back, the same confirmation was added to `prep-dataset`, and this rule — previously only in `build-dataset` skill prose (`SKILL.md:41`) — was lifted into the wiki here.
**Source:** this session (13.07.2026); [skills-007](../../specs/skills-007-class-nature-gate.md). Related: [P-05](#p-05--center-discrete-gestures-keep-continuous-classes-raw-never-center-across-class-boundaries), [P-06](#p-06--direction-discrimination-requires-lr_slope--lr_intercept-the-only-signed-asymmetry-features), [P-10](#p-10--always-include-an-idle--unknown-class-to-prevent-false-detections), [P-11](#p-11--reconcile-sensor-scale-across-sources-gravity-at-rest-is-the-probe-but-motion-invalidates-it).

## P-16 — Choose the holdout axis by what you need to prove; report the withheld fraction per class

**Rule:** Decide the holdout **before the first training run**, and pick its axis from the data's grouping structure, in descending order of what the score proves: **unseen people** > **unseen sessions** > **time-tail within a session** > the platform's automatic split. State the claim the chosen rung actually licenses — a holdout whose held-out contributors also appear in training through other recordings is a new-session result, not a cross-user one, however it is labelled. Report the **per-class withheld fraction**, never only the aggregate, and preserve the class ratio (for a continuous target, the target distribution) across the split. **A class with two or fewer recordings cannot be held out interpretably** — say so rather than reporting its score.
**Why:** On continuous windowed data an automatic per-window split places near-identical neighbouring windows on both sides and inflates the result; the gap between a strict holdout and the easy split *is* the generalization cost the easy split hides. And "one whole recording per class" is uniform in recordings while being wildly non-uniform in data — it can withhold ~40% of a thin class and ~7% of a fat one, so the design damages exactly the classes least able to absorb it and then measures the damage as a model weakness.
**When to apply:** every dataset build, before the export — not after results come back. Reversing toward a stricter holdout once results look good is not an honest move.
**Precedent:** a four-class activity set where a uniform per-class recording holdout withheld ~41% of the thinnest class and ~7% of the fattest; the thin classes then scored worst, and the split had caused part of the result it was measuring.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §1.

## P-17 — Class survival is not event yield; imbalance is a window-level quantity

> **Retracted 24.07.2026 — this principle originally also asserted that the platform's *minimum samples
> per class* counts windows. That clause is withdrawn as unproven, in either direction.** The captured
> platform docs use "sample" in **both** senses (see the `[needs clarification]` box in
> [dataset requirements](../architecture/platform-dataset-requirements.md)), so neither reading is
> established. The tool currently counts rows; treat that as unverified rather than confirmed, and make
> **no change in either direction** until the empirical check recorded there is run. Do not cite this
> principle for the minimum-samples rule.
>
> *Twice-wrong history, kept as the precedent for [process P-18](process.md): the first claim came from
> our own paraphrase; the "correction" then asserted the opposite and wrongly stated the docs were
> consistent. Both were unsourced generalisations from a partial read.* Everything below — event yield
> and window-level imbalance — is independent of this and stands.

**Rule:** [P-01](domain.md) asks whether a class *survives* (longest contiguous run ≥ window). Also report **event yield**: the fraction of that class's labelled events that actually produce a pure training window. The platform's window grid is fixed from the start of the file, so an event only slightly longer than the window lands one only occasionally. Separately, **class imbalance is a window-level quantity**, since classes differ in how much data survives windowing and how many windows are discarded for crossing a boundary — so quote the ratio the model actually trains on, not the row ratio. (The platform's ≥20-samples-per-class minimum is *not* part of this: it counts rows. See the box above.)
**Why:** "The class survives" and "every event is kept" are different claims, and stating the second from the first is wrong in the user's favour, which is the dangerous direction. A row-level imbalance figure can understate what the model sees by more than a factor of two.
**When to apply:** any window-survival report, and any imbalance figure quoted to a user.
**Precedent:** a two-class set whose events were all longer than the chosen window — the class survived comfortably while roughly a third of its events yielded no pure window; and the same file reading ~5:1 imbalance by row against ~11:1 by surviving window, with about a fifth of candidate windows dropped as mixed.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §2.

## P-18 — Centering is also segmentation: announce the discard, then quantify it

**Rule:** Centering does not merely shift rows — it detects events, emits one window per event, and **discards everything between events**. On a sparse recording that is legitimately most of the file. Say so **before** the pass, and after it report rows in, rows out, and events detected **per class**. No separate trimming step is needed.
**Why:** A large silent shrink is indistinguishable from a bug, and a *partial* loss that goes unreported is worse than a total one, which at least fails loudly. Users whose data "gets demolished by preprocessing" are the reason this tool exists; producing that experience ourselves, without explanation, is the failure mode to avoid.
**When to apply:** every centering pass, in the skill flow and in any report the user reads.
**Precedent:** sparse gesture recordings shrinking by roughly two thirds to over nine tenths under centering — every discarded row correct, none of it announced in advance.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §3.

## P-19 — Confirm event separability against the detector, not only physical meaning

**Rule:** [P-15](domain.md) establishes each class's physical meaning; that is necessary and **not sufficient**. Gap-less rhythmic repetition is **continuous to the detector** whatever the class is called: if the events are performed without pauses the signal envelope never falls below threshold and the whole block is detected as one active region. After the class-nature table is confirmed, run the centering pass and **read the segment count per class** — a class yielding about one segment per recording is continuous to the pipeline no matter how the user described it. Densely-packed short events are also strongly window-dependent: shorter windows recover far more of them.
**Why:** The user's physical description and the detector's view can disagree, and the detector's view determines the outcome. A user can correctly say "one tap, fire once per tap" and still produce a single undivided block.
**When to apply:** the class-nature gate, before committing to a centering configuration.
**Precedent:** a tap class described correctly as discrete whose envelope exceeded threshold across the entire block, yielding ~1 segment; and a set of a few hundred short events where a long window recovered barely a dozen while shorter windows recovered most.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §3.

## P-20 — A class with wide cross-subject spread can invert into an over-predicting sink

**Rule:** Watch for a class with near-total recall and roughly half precision that absorbs its neighbours. Cause: its amplitude varies widely across people, so weak instances resemble the quiet class and strong ones resemble the energetic class, and it spreads across everyone else's territory. **This is a data-consistency problem — no feature set or window size addresses it.** The fix is consistency at the source: recollect with a controlled execution, or merge the class. Related: a quiet/"unknown" class **carved out of rest periods is narrower than real background** — record it on purpose ([P-10](domain.md)).
**Why:** Distinct from the familiar weak-class-dies pattern ([P-07](domain.md)) and it points the opposite way — adding such a class has been observed to *lower* overall accuracy substantially, so the instinct to add a class to fix confusion makes it worse.
**When to apply:** reading back a confusion matrix; deciding whether to add an idle/background class.
**Precedent:** a two-class model that dropped from ~86% to ~68% holdout accuracy when a third class was added, the new class reaching ~100% recall at ~51% precision and absorbing both others.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §4.

## P-21 — When direction features are confirmed enabled and a mirror pair still collapses, merge rather than tune

**Rule:** [P-06](domain.md) says a mirror pair needs the signed/direction features. If those features are confirmed enabled — **read from the actual configuration, not assumed** — and the pair still collapses, the distinction is not resolvable by that sensor in that placement. **Merge the two classes**: it is a relabel, costs no re-collection, and removes the confusion outright. Further feature or window tuning does not.
**Why:** Without the confirmation step the same symptom has two opposite treatments (enable features vs. merge), and guessing wrong costs either a wasted training round or an unnecessary class merge. With it, the call is decided by evidence.
**When to apply:** any persistent left/right, up/down or clockwise/counter-clockwise confusion after the first trained result.
**Precedent:** a multi-zone recognition set where every direction feature was verified enabled from the uploaded configuration and a left/right pair still confused; merging the pair removed the dominant error and the remaining classes were unaffected.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §4.

## P-22 — The gravity probe cannot see a gyroscope or single-axis unit slip; use two further probes

**Rule:** [P-11](domain.md)'s at-rest gravity probe detects a mismatched **accelerometer range** and nothing else — the gyroscope reads near zero at rest and offers no reference. Add two probes that do work: compare **per-source, per-axis distributions** (spread and range) against the cohort, and check for **fractional values on an axis that should be integral**. And **validate any rescale by where you put it**: route the **un-rescaled** batch into the holdout, so a correct factor shows that class scoring normally on data the correction never touched.
**Why:** A single-axis unit slip is invisible to the standard probe and survives into training as a systematically wrong feature for one contributor. The holdout-routing trick converts a judgement-call transform into a checkable one at no extra cost.
**When to apply:** the scale-reconciliation step, whenever sources come from more than one device or contributor.
**Precedent:** one contributor's single gyroscope axis stored in physical units while everyone else's was in raw counts — invisible to the gravity probe, obvious to both added probes.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §5.

## P-23 — Inspect the rows driving a storage-type recommendation before accepting it

**Rule:** Storage-type recommendation is driven by extreme and fractional values, so **a handful of malformed rows can push an entire integer dataset to floating point**, doubling model input footprint for no benefit. Read the rows responsible before accepting FLOAT32 over INT16. Two related signatures: a **frozen column** — one or two axes stuck at a fixed value, jumping between discrete regimes while the other axes move normally, which is a per-column export fault and not a property of the motion; and **resampling**, which produces fractional values by interpolation and so silently converts an integer dataset to floats — round back where every source column was integral, or the file carries many digits of fabricated precision ([P-11](domain.md) keeps data raw INT16 for exactly this reason).
**Why:** The recommendation is a summary of the extremes, so it reports the corruption rather than the data. Accepting it silently costs the user footprint and fidelity, and hides a genuine data fault behind a plausible-looking type choice.
**When to apply:** whenever a dtype recommendation comes back wider than expected, and after every resampling pass.
**Precedent:** a set where three corrupt rows were the sole reason FLOAT32 was recommended over INT16; and a resampled export carrying ~16 significant digits from a sensor whose true resolution was one count.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §5.

## P-24 — For a continuous target, report the null model before training

**Rule:** Before training a regression task, compute and report the **null model** — the error of always predicting the training mean — on the same data the model will be scored on. A model that does not beat it has learned nothing, whatever its absolute error reads. Also check the split: a holdout whose **target variance is far below** the training set's makes the constant predictor hard to beat and produces an uninterpretable result.
**Why:** An error figure is meaningless without the baseline it must beat, and reporting it alone invites a model that is worse than a constant to be read as a working result. Both numbers are cheap and available before any training run.
**When to apply:** every regression build, at the holdout-design step.
**Precedent:** a wrist-motion regression whose trained error was roughly twice the constant-predictor error on the same holdout — a result only visible once the baseline was computed, and computed only after training.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §6.

## P-25 — A class that is never predicted may be an evaluation artefact, not a dead class

**Rule:** Before diagnosing a never-predicted class as a data or modelling problem ([P-07](domain.md)), **check it had validation windows at all**. An automatic split can leave a class with **zero** windows on the validation side, which makes the reported accuracy a broken average rather than a measurement. It is predictable before training from the number of recording **sessions per class**, and the remedy is an explicit holdout ([P-16](domain.md)) — not a change to the data.
**Why:** The symptom is identical to a genuine dead class, and the two have opposite treatments: one calls for more or better data, the other for a different evaluation. Treating an evaluation artefact as a data problem sends the user to collect data they do not need.
**When to apply:** first read of any confusion matrix, especially where some classes have few recordings.
**Precedent:** a continuous multi-class recognition set where two classes ended with no validation windows and the headline accuracy was meaningless; supplying an explicit per-class holdout made the same data report an honest — and higher — number.
**Source:** [dataset preparation lessons](../../raw/harvested-practice/2026-07-23-dataset-preparation-lessons.md) §1; [data pipeline](../architecture/platform-data-pipeline.md).

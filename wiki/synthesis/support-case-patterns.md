---
type: synthesis
status: active
updated: 2026-06-25
sources:
  - Field experience (practitioner knowledge; no external source document).
  - ../principles/domain.md
  - ../../scripts/README.md
tags: [synthesis, cases, patterns, gesture, postprocessing, worked-examples]
---

# Case patterns — common data-prep scenarios

**What this is:** three reusable patterns abstracted from common field scenarios (field experience). Each shows the symptom, the diagnostic path, the root causes, and the fix, so a similar case is recognizable fast. Numbers are illustrative of the real case (validated on limited data — treat as indicative, not universal). Tools: [`scripts/`](../../scripts/README.md). Rules: [domain principles](../principles/domain.md). Investigation order: [playbook](support-diagnostic-playbook.md).

---

## Pattern A — "Data is removed at preprocessing / a label has no data"

**Setup:** multi-class IMU gesture dataset, `session_id` + time + 6 axes + label; the user has a few long sessions with all gestures interleaved.

**Symptom (typical wording):** *"some data is removed during training and I don't know which/why; for one of my labels there's no data; I tried different windows and it didn't help."*

**Diagnostic path:**
1. Profile → labels not contiguous (e.g. the file has a class the user never mentioned), and only a few long **mixed-label** sessions.
2. Run-length per (session,label) → the shortest gesture's longest contiguous run (~140 rows) is **below the window** (150). That class can't form a single pure window.
3. Window-survival sim at the user's settings → ~60% of candidate windows dropped as mixed; of those kept, ~99.7% are idle (because training shift was tiny, e.g. 10, with window 150). The user's "20% removed" was actually ~48%.
4. Sampling rate differs across sessions (e.g. 244 Hz vs 199 Hz).

**Root causes (ranked):** (1) interleaved sessions → short per-label runs < window ([domain P-01](../principles/domain.md)); (2) tiny training shift inflates idle ([domain P-02](../principles/domain.md)); (3) an unmapped/non-contiguous class ([domain P-03](../principles/domain.md)); (4) mixed sampling rates ([domain P-04](../principles/domain.md)); (5) a partial session missing several classes.

**Fix:** record isolated sessions per gesture and concatenate; set training shift = window; resolve the extra class to contiguous 0..N-1; resample to one rate; drop the partial session. If re-recording isn't possible now, a smaller window+shift (e.g. 50/50) revives the starved classes at the cost of shorter gesture coverage.

**Recognize it by:** "data removed"/"label missing" + multi-class IMU + `session_id` + many short gesture segments per session.

---

## Pattern B — "Model can't get good results on device" (dead classes, postprocessing can't recover)

**Setup:** small multi-class gesture model (Neuton), tested on device against a recording covering all trained gestures.

**Symptom:** *"a user can't get good results after deploying this model."* Runner output has multiple classes, but some are **never predicted**.

**Diagnostic path:**
1. Read the model setup from `nrf_edgeai_user_model.c` (window, shift, input type, neuron/weight counts, input-scaling min/max = the saturation clamp). Small capacity (e.g. ~24 neurons) for 8 classes.
2. Decode the feature mask → `LR_SLOPE`/`LR_INTERCEPT` **off on every axis**: no signed-asymmetry features ([domain P-06](../principles/domain.md)).
3. Probability audit of runner output → two classes with max-prob ≈ 0 everywhere = **dead** ([domain P-07](../principles/domain.md)).
4. Pairwise separability (Cohen's-d) on training features → opposite-direction gesture pairs are borderline on average, *but* a single feature (e.g. "percent-of-window signal positive" on one axis) separates them strongly → the directional signal **exists in the data**, the feature pipeline just isn't capturing it, and the tiny model can't carve the fine boundary.
5. Test-data quality → **gyro saturation spikes** ("3 identical clipped values surrounded by quiet") absent from training; inflate per-window STD → push predictions toward "unknown."
6. Postprocessing grid → cleans jitter but **cannot create** detections for the dead classes.

**Root causes (ranked):** (1) missing direction features; (2) model capacity too small for the confusable pairs; (3) one class's training signature too close to idle; (4) inference-only gyro saturation artifact (compounds, separate issue).

**Fix (iterate one cycle):** retrain with `LR_SLOPE`/`LR_INTERCEPT` enabled and more capacity; collect sharper/contrast-rich samples for the weak classes and a varied "unknown"; address the gyro artifact at the *source* (firmware), not inference-only ([domain P-09](../principles/domain.md)). Don't promise a postprocessing fix for a dead class.

**Recognize it by:** multi-class output with categorical zero recall on specific classes; confusable directional pairs; saturation patterns in test gyro/accel; small model (<50 neurons) on >5 classes.

---

## Pattern C — Iteration outcome: recovering dead classes + choosing the postprocessing pipeline

**Setup:** the follow-up to Pattern B after acting on the recommendations.

**What changed:** merged the prior centered training set with a newly centered set (centered **per class**; schema + per-class STD-ratio + mean-sign-flip checks before merging — [domain P-05](../principles/domain.md)); roughly doubled model capacity; enabled `LR_SLOPE` on all axes and `LR_INTERCEPT` on several.

**Outcome:** both previously-dead direction-related classes recovered (max-prob 0.06→1.0 and 0.0→1.0), confirming the missing-direction-feature diagnosis ([domain P-06](../principles/domain.md)).

**Postprocessing grid search** (α × consecutive-N × threshold × unknown-margin): the **winner was EMA α=0.3 + unknown-margin suppression, with no threshold and no consecutive-N** (≈80% strict / ≈87% direction-agnostic window accuracy, zero idle/random false positives). Adding a threshold or consecutive-N **hurt** — they dropped legitimate detections ([domain P-08](../principles/domain.md)). The ~15-line C implementation is [`firmware_postprocessing_ema_unknown_margin.c`](../../scripts/firmware/firmware_postprocessing_ema_unknown_margin.c).

**Rejected on parity grounds:** a 3-tap gyro median filter — after auditing, training vs eval gyro artifact rates were comparable (0.62% vs 0.96%), so an inference-only filter would only introduce distribution shift ([domain P-09](../principles/domain.md)).

**Residual:** one weak class remained (high precision, low recall) → collect more distinctive samples for it; and an apparent L/R confusion turned out to be a **protocol-execution order** issue, not a model bug, once the user confirmed execution order ([process P-06](../principles/process.md)).

**Recognize it by:** "we retrained with feature X / more capacity — what postprocessing should we ship?" and "should we add a gyro filter?"

---

## Cross-cutting lessons (promoted to principles)

- Mixed-label windows + short runs ⇒ silent class loss → [domain P-01](../principles/domain.md).
- Direction needs LR_SLOPE/LR_INTERCEPT → [domain P-06](../principles/domain.md).
- Postprocessing has a hard ceiling at the model output → [domain P-07](../principles/domain.md).
- EMA + unknown-margin is the default; complexity hurts → [domain P-08](../principles/domain.md).
- Preprocessing parity before any inference-only filter → [domain P-09](../principles/domain.md).
- Symmetric L/R confusion may be a protocol error → [process P-06](../principles/process.md).

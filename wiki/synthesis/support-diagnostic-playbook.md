---
type: synthesis
status: active
updated: 2026-06-25
sources:
  - ../../scripts/README.md
  - ../principles/process.md
  - ../principles/domain.md
tags: [synthesis, playbook, diagnosis, support, signal-processing]
---

# Diagnostic playbook — investigating an inertial data-prep problem

**What this is:** the ordered set of moves for figuring out why a user's data isn't behaving on the platform, distilled from field experience. The *rules* these moves enforce are in [process principles](../principles/process.md) and [domain principles](../principles/domain.md); the *tools* are in [`scripts/`](../../scripts/README.md); the *documented contract* is in [`architecture/platform-*`](../architecture/platform-dataset-requirements.md). Worked examples: [case patterns](support-case-patterns.md). For fast triage instead, use the [troubleshooting checklist](support-troubleshooting-checklist.md).

## 0. Read the whole request

Read the prose **and** any attachment (screenshot/config/CSV). Map the user's exact phrasing to a cause area; note contradictions between what they say and what the data shows ([process P-01](../principles/process.md)).

## 1. Inventory the inputs

List everything provided. `*.csv` → read header + first rows, count rows. Screenshot → open it (vision) to read the actual platform settings (window, shift, task, metric, feature selection). `*.zip` (model archive) → unpack and inventory ([model archive structure](../discovery/platform-model-archive.md)).

## 2. Profile the dataset

Run [`analyze_csv_signal.py`](../../scripts/diagnostics/analyze_csv_signal.py) for a fixed report, or do it by hand. Check:

- **Schema/types** — expected columns present? all numeric? header unique? object dtypes hint at NaNs/locale issues.
- **Class distribution** — `value_counts().sort_index()`; **cross-check the user's stated mapping vs actual unique values** (contiguous from 0?); ≥20 samples/class? ([domain P-03](../principles/domain.md)).
- **Session structure** — count/lengths; any session shorter than the window (dropped)? per-session class composition; a class confined to one session may be isolated by the split.
- **Sampling rate** — median Δ of the time column per session; mismatches across sessions distort fixed-row windows ([domain P-04](../principles/domain.md)).

## 3. Run-length encoding per (session, label)

The key move for "data removed" complaints. For each (session, label): total rows, n_runs, max_run, runs ≥ window. **Any class whose `max_run < window` cannot produce a single pure window** and disappears ([domain P-01](../principles/domain.md)).

## 4. Simulate window survival

[`window_survival_sim.py`](../../scripts/diagnostics/window_survival_sim.py): given window + shift, count pure windows per label and total dropped. Try the user's current settings **and** alternatives (smaller window, shift=window). Put the per-label numbers straight into the reply. Flag the assumption: the strict "drop mixed windows" model is an upper bound on the issue; the platform may keep majority-label windows — verify against its "Processed Data" view ([process P-04](../principles/process.md)).

## 5. Is the training data centered? (discrete-gesture datasets)

Before any feature/separability analysis, confirm centering with [`check_signal_centered.py`](../../scripts/diagnostics/check_signal_centered.py): discrete gestures should read CENTERED (or LOOSE for tap-like), continuous classes (idle/unknown) read RAW. If raw, center per-class with [`center_training_data.py`](../../scripts/preprocessing/center_training_data.py) before comparing anything ([domain P-05](../principles/domain.md)).

## 6. Decode the feature mask (when a model archive is provided)

For "class N is never predicted" or "confuses left/right (up/down)": run [`feature_mask_decoder.py`](../../scripts/diagnostics/feature_mask_decoder.py) on `nrf_edgeai_user_model.c`. If `LR_SLOPE`/`LR_INTERCEPT` are off on all axes, the model has no signed-asymmetry signal → directional classes conflate or die. Fix = retrain with those features, not recollect data ([domain P-06](../principles/domain.md)).

## 7. Postprocessing-ceiling check (before promising a postprocessing fix)

On the runner predictions CSV, run [`postprocessing_pipelines.py`](../../scripts/postprocessing/postprocessing_pipelines.py). For each class get max-prob / mean-prob / rank distribution. **Max-prob ≈ 0 ⇒ dead class ⇒ no postprocessing helps** (retrain or drop). If a class fires occasionally as top-1, postprocessing is the right tool — start with the simplest pipeline ([domain P-07, P-08](../principles/domain.md)).

## 8. Distribution-shift check (predictions uniformly wrong)

Run [`windowed_feature_distribution_comparison.py`](../../scripts/diagnostics/windowed_feature_distribution_comparison.py): per-axis STD envelopes (how many test windows fall outside the training-class p5–p95 band) and mean Cohen's-d from test data to each training class. If even the closest class has large d, the recording is in a different feature regime (often a sampling-rate mismatch or a firmware artifact). Watch for **gyro saturation spikes** — "3 identical clipped values surrounded by quiet" = a sample-and-hold / FIFO-overrun footprint that inflates STD/RMS and pushes predictions toward "unknown" ([case patterns](support-case-patterns.md)).

## 9. Decide preprocessing changes with the parity rule

If tempted to recommend a firmware median/low-pass filter, run the parity audit first ([domain P-09](../principles/domain.md)): comparable train/inference artifact rates ⇒ don't filter; large divergence ⇒ filter both sides + retrain, or skip. Never inference-only.

## 10. Compose the reply

Root cause in one sentence (user's vocabulary) → the numbers from their data → numbered fixes in priority order, each linked to the exact [platform rule](../architecture/platform-dataset-requirements.md) → secondary issues they didn't ask about → collaborative tone ([process P-07](../principles/process.md)).

## 11. Capture what's new

If a ticket taught something not here: add a domain/process principle, a case pattern, and/or a new script. The goal is that the next similar ticket takes minutes, not an hour.

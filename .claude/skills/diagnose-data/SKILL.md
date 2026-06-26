---
name: diagnose-data
description: >-
  Figure out why a user's data or trained model is misbehaving on Nordic Edge AI Lab, with the
  check-before-you-promise guardrails (dead-class ceiling, train/inference parity). Use when the user
  reports symptoms like "data is being removed", "a label has no data", "a class is never predicted",
  "the model confuses left and right", "the model is too big for the chip", "false detections after I
  deployed", or "I tried thresholding and it's still bad".
---

# Diagnose a data / model problem

Map the symptom to a cause, prove it with the user's own numbers, and propose prioritised fixes — without
promising a fix the data can't support. The ordered moves are the
[diagnostic playbook](../../../wiki/synthesis/support-diagnostic-playbook.md); fast triage is the
[troubleshooting checklist](../../../wiki/synthesis/support-troubleshooting-checklist.md); worked anatomies
are the [case patterns](../../../wiki/synthesis/support-case-patterns.md). The rules behind them are the
[domain](../../../wiki/principles/domain.md) and [process](../../../wiki/principles/process.md) principles.

## 1. Read everything and reconcile

Read the prose AND any attachment (a screenshot of the platform settings, the CSV, a model archive ZIP).
Map the user's exact wording to a cause area, and **re-derive every number yourself** — treat their stated
class map / rate / durations as hypotheses ([process P-01/P-02/P-03](../../../wiki/principles/process.md)).

## 2. Profile first, then escalate

Run the profiler (pass the user's real column names — the scripts default to `label`/`session_id`, but
gesture data usually uses `class`):

```
python3 scripts/diagnostics/analyze_csv_signal.py <file.csv> --label-col class --session-col <s> --time-col <t>
```

Then pick the move that fits the symptom (cheapest first):
- **"data removed" / "label has no data"** → [`window_survival_sim.py`](../../../scripts/diagnostics/window_survival_sim.py)
  at the user's window/shift and a few alternatives ([domain P-01/P-02](../../../wiki/principles/domain.md)).
- **"is it centered?"** (before any feature analysis) → [`check_signal_centered.py`](../../../scripts/diagnostics/check_signal_centered.py).
- **"a class is never predicted" / "left-right confused"** with a model archive →
  [`feature_mask_decoder.py`](../../../scripts/diagnostics/feature_mask_decoder.py) on `nrf_edgeai_user_model.c`
  (are LR_SLOPE/LR_INTERCEPT off?). See **feature-advice**.
- **"predictions uniformly wrong"** → [`windowed_feature_distribution_comparison.py`](../../../scripts/diagnostics/windowed_feature_distribution_comparison.py)
  (distribution shift / sampling-rate mismatch / gyro saturation).
- **postprocessing questions** → [`postprocessing_pipelines.py`](../../../scripts/postprocessing/postprocessing_pipelines.py).

## 3. Run the guardrail checks BEFORE promising a fix

- **Dead-class ceiling** (any "class never fires" / "thresholding didn't help"): check per-class max
  probability first — if it's ≈0 the class is dead at the model level and **no** postprocessing recovers it;
  retrain or drop ([domain P-07](../../../wiki/principles/domain.md)).
- **Train/inference parity** (before recommending a firmware median/low-pass filter): audit artifact rates;
  never filter inference-only ([domain P-09](../../../wiki/principles/domain.md)).

## 4. Reply

[Process P-07](../../../wiki/principles/process.md) shape: root cause in one sentence (their words) → the
numbers from their data → numbered prioritised fixes, each citing the exact
[platform rule](../../../wiki/architecture/platform-dataset-requirements.md) → secondary issues →
collaborative tone. Mark experiential heuristics as "from experience, verify" — not platform law. Hand off
to **prep-dataset** (re-assemble), **collection-advice** (collect better data), or **feature-advice**
(feature/window settings) as the fix requires.

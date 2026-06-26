---
name: validate-upload
description: >-
  The pre-upload gate: check whether a CSV will be accepted by the Nordic Edge AI Lab platform and
  whether it will silently lose data, returning PASS / FIX-REQUIRED / WILL-LOSE-DATA with each problem
  tied to the exact platform rule. Use when the user asks "is this ready to upload?", "will the platform
  accept this?", "validate my CSV", "check this before I upload", or "did I prepare this correctly?".
---

# Validate a CSV before upload

Run the ordered pre-flight so the user never hits a platform rejection or a silently dead class. This
wraps `src/data_builder`'s validator, which checks the full contract in
[_shared/platform-contract.md](../_shared/platform-contract.md) (canonical source:
[wiki/architecture/platform-*](../../../wiki/architecture/platform-dataset-requirements.md)). Cite rules;
don't restate them from memory.

## 1. Confirm the parameters

You need a dataset profile (label column, sensor columns, separator, sampling rate, class encoding,
intended window, and whether frequency-domain features will be on). Reconcile it against the file
([process P-02/P-03](../../../wiki/principles/process.md)) — don't trust stated values. Start from
[the schema](../../../data/skill-presets/dataset-profile.schema.json) /
[the worked example](../../../data/skill-presets/nordic-gesture-demo.json); write the profile to
`output/<name>.profile.json` if there isn't one.

## 2. Run the check

```
PYTHONPATH=src python3 -m data_builder.cli validate <file.csv> \
    --profile output/<name>.profile.json --window <N> [--holdout <holdout.csv>] [--json]
```

The verdict and exit code: `0` = PASS, `2` = FIX_REQUIRED (the platform would reject it or a value must be
corrected), `3` = WILL_LOSE_DATA (accepted, but a class/window would silently disappear — an **upper
bound** to confirm in the platform's Processed Data view). The checks run in three buckets — file-format
hard-rejects, silent-loss (window survival), and model-quality advisories.

## 3. Report back

In [process P-07](../../../wiki/principles/process.md) shape: verdict first, then the numbers from their
data, then a numbered, prioritised fix list each citing its rule, then advisories (recommended data type,
metric for imbalance, direction features). Keep it plain — the user should know exactly what to change and
why, and which items are hard platform rules vs recommendations.

## Guardrails
- Frame window-survival losses as "verify against the platform's Processed Data view", never as a guarantee.
- Distinguish a hard reject (must fix) from an advisory (better model) explicitly.
- If a fix means re-assembling the file, hand off to **prep-dataset**; if it means understanding *why* a
  class behaves badly, hand off to **diagnose-data** / **feature-advice**.

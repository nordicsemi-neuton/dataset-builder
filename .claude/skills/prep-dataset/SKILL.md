---
name: prep-dataset
description: >-
  Turn one or more raw inertial-sensor recordings (CSV) into a single upload-ready training file for
  the Nordic Edge AI Lab platform — combine files, fix encoding/format/labels, optionally center
  gestures or resample, and check nothing will be silently dropped. Use when the user says things like
  "prepare my data for the platform", "combine these recordings", "merge my gesture files", "make this
  upload-ready", "center my gestures", "resample to one rate", or "get my CSV ready to train".
---

# Prepare a dataset for upload

Assemble raw recordings into ONE upload-ready CSV plus a readiness report and the saved class-encoding
dictionary. The platform's rules are the law here — they live in the canonical wiki, summarised with
sources in [_shared/platform-contract.md](../_shared/platform-contract.md). Do **not** restate rules from
memory; cite that file (and re-read the linked `wiki/architecture/platform-*` page when a detail matters).

## 1. Gather and RECONCILE the dataset parameters (do this first)

You need: the label column, the sensor-axis columns, the separator, the sampling rate (Hz), the class
encoding, and the intended window size. A starting template is
[data/skill-presets/nordic-gesture-demo.json](../../../data/skill-presets/nordic-gesture-demo.json) and
the schema is [dataset-profile.schema.json](../../../data/skill-presets/dataset-profile.schema.json).

**Never inherit a preset's values silently.** Confirm every field against the actual file — especially the
class indices (the `idle=0/unknown=1/gestures=2..7` convention is illustrative, not a platform rule).
Treat the user's stated class map / rate / durations as hypotheses to check
([process P-02/P-03](../../../wiki/principles/process.md)). If the user has no profile, write one to
`output/<name>.profile.json` from what they tell you, then confirm it back to them in plain language.

## 2. Run the engine

The production engine is `src/data_builder`. From the repo root:

```
PYTHONPATH=src python3 -m data_builder.cli prep <recording1.csv> [recording2.csv ...] \
    --profile output/<name>.profile.json --out output/<name>_upload_ready.csv --window <N> [--json]
```

- **Centering is default-on for gesture datasets** (it centers the classes the profile marks as
  `gesture_classes` so each gesture's motion peak sits mid-window, and trims `continuous_classes` like
  idle/unknown) — this is a near-universal, essential step for discrete gestures
  ([domain P-05](../../../wiki/principles/domain.md)). Pass `--no-center` to skip it (e.g. data already
  centered, or a non-gesture dataset). It uses the validated centering algorithm (auto work-axis,
  peak-tolerance QC); confirm the result on real data with
  [`check_signal_centered.py`](../../../scripts/diagnostics/check_signal_centered.py).
- Add `--resample <HZ> [--time-unit s|ms|us]` if sessions have different sampling rates
  ([domain P-04](../../../wiki/principles/domain.md)).
- It **combines into a single header, repairs the numeric format, encodes labels contiguously from 0**, and
  **refuses to write** if the data would be rejected or would silently lose a class — unless you pass
  `--write-anyway` (which the report will note). Exit codes: `0`=ready, `2`=must fix, `3`=will lose data.
- Use `--json` when you want to read the structured findings; show the user plain language, not the JSON.

## 3. Report back (plain language, in this order)

Follow the [process P-07](../../../wiki/principles/process.md) shape:
1. One sentence: is it ready, or what's the one thing blocking it.
2. The numbers from their own data (per-class counts, longest runs, detected rate, recommended data type).
3. Numbered fixes in priority order, each pointing at the exact rule (the report already carries the
   `rule_ref`).
4. Secondary notes (e.g. the desktop-runner flags the engine prints, the recommended metric).

If it wrote the file, tell them the path of the CSV **and** the saved dictionary, and the runner flags
(e.g. `-t class`). If it refused, explain why in their words and what to change — do not pass
`--write-anyway` without telling them it ships a known-bad file.

## Guardrails
- Confirm before writing anything; the engine only writes after validation passes (or on explicit override).
- Never present an experiential default (centering, shift=window) as a platform rule — say which is which.
- If the user needs deeper diagnosis ("why is a class disappearing?", "left/right confused"), hand off to
  the **diagnose-data** or **feature-advice** skill.

---
type: decision
status: active
updated: 2026-07-25
sources:
  - ../architecture/platform-dataset-requirements.md
  - ./adr-0003-scipy-on-resample-path.md
tags: [decision, architecture, data-builder, pipeline, validation, engine]
---

# ADR-0002 — data-builder engine: two-layer validation, refuse-on-loss, numpy/pandas-only

Status: active
Date: 25.06.2026

> **Amendment (13.07.2026):** the "numpy/pandas-only (no scipy)" constraint below is **narrowed** by
> [ADR-0003](adr-0003-scipy-on-resample-path.md) — `scipy.signal` is permitted on the resampling path
> (`resample.py`) for anti-aliasing. Everything else in this ADR stands (pytest/jsonschema still rejected).
>
> **Amendment (25.07.2026):** the raw-bytes intake layer (`check_raw_file`/`csv_io.sniff_raw`) is
> **extended** by [ADR-0005](adr-0005-zip-intake-and-head-bound.md) — it now unwraps a `.zip`
> container to its single member (both `sniff_raw` and `read_table` through one helper) and checks
> the inner member name, in addition to encoding / line endings / header / delimiter / field-count.
> The field-count head bound is raised from 64 KB to 1 MiB (line-aligned). The two-layer split,
> Finding/Report taxonomy and exit codes 0/2/3/4 are unchanged.
>
> **Amendment (25.07.2026):** [ADR-0006](adr-0006-signal-processing-mode.md) narrows two clauses for
> Signal-Processing mode. (a) `check_dataframe`'s "window range, window survival" (below) are
> **conditional** on the profile's `signal_processing` mode — skipped on `validate` when it is off.
> (b) "**nothing … is auto-applied**" (below) is narrowed: reading `signal_processing: false` and
> suppressing the window checks is an auto-application, disclosed via an `sp_off_unverified` advisory
> rather than performed silently. Scope is the `validate` surface only in B5a; `prep`/`quality-report`
> are unchanged until B5b (`databuilder-016`). Exit codes and the Finding/Report contract stand.
>
> **Amendment (25.07.2026):** [ADR-0007](adr-0007-sp-off-prep-quality-surface.md) narrows the
> **"Centering (gesture datasets) … default-on when the profile is classification and declares
> `gesture_classes`"** clause below: centering is default-on only when Signal Processing is **not off**.
> With `signal_processing: false`, `prep` **skips centering** and refuses `--resample` (both are windowing
> / continuous-signal operations that corrupt tabular rows); an SP-off profile that still declares
> `gesture_classes` is a contradiction (`sp_off_contradicts_profile`), not a centering trigger. The
> incentive gradient (the honest tabular file still writes) is load-bearing. Exit codes and the
> Finding/Report contract stand.
>
> **Amendment (27.07.2026).** [ADR-0004](adr-0004-resample-integer-preservation.md) narrows the
> "**sensor values are never cast to int (floats preserved bit-for-bit)**" clause below (in "Flag, never
> silently drop/truncate"): on the **resampling path only**, a sensor column whose every source value is
> a whole number has its resampled estimates **re-quantized** (`np.round`) to the sensor's integer
> resolution — **the column stays `float64`, never cast to an integer storage dtype** — so resampling
> does not fabricate decimal precision, disclosed via a verdict-neutral `resample_integer_preserved`
> finding. The non-resampled path is unchanged (byte-identical). The writer is unmodified. Exit codes and
> the Finding/Report contract stand. *(Dated after the ADR-0005/0006/0007 notes above: ADR-0004's number
> was reserved for this task while those landed first.)*

## Context

The user-facing skills (`prep-dataset`, `validate-upload`) needed a production engine to assemble raw
inertial-sensor recordings into one upload-ready CSV and validate any CSV against the platform contract
([dataset requirements](../architecture/platform-dataset-requirements.md) and the other `platform-*`
pages). Built through the task cycle (spec → 4 independent reviews → implement → re-review running the
suite). Scope: gesture multiclass classification first. Key forces surfaced by the two review gates:
pandas **hides** the very things the platform rejects on (it collapses line endings and silently
truncates ragged rows); silent data corruption shipped to a third party is the worst outcome; and the
five skills bind to a CLI/verdict contract that must be stable.

## Decision

`src/data_builder/` (numpy + pandas only; stdlib `unittest`; **no scipy, no pytest**), with:

- **Two-layer validation.** `check_raw_file` inspects the **raw bytes** (encoding, line endings, header,
  delimiter, field-count, file name) because pandas hides them; `check_dataframe` checks the semantic
  contract (numeric values, contiguous-from-0 target, class minimums, window range, window survival,
  sampling rate, data type). `run_checks` composes both for the CLI; `prep` calls `check_dataframe` on the
  prepared frame.
- **Frozen contract the skills bind to:** `Finding(group, severity, code, message, rule_ref, data)` →
  `Report(verdict ∈ {PASS, FIX_REQUIRED, WILL_LOSE_DATA})`; CLI `prep|validate` with `--json` and exit
  codes `0/2/3/4`. `rule_ref` is a `wiki/...#anchor` so any finding is traceable (a test enforces every
  anchor resolves).
- **Refuse-on-loss by default.** `prep` does not write on FIX_REQUIRED **or** WILL_LOSE_DATA without an
  explicit `--write-anyway` (the silent-loss case is the most damaging for a third party).
- **Flag, never silently drop/truncate.** Empty/NA/unrepairable values, calendar timestamps, and ragged
  rows become findings; sensor values are never cast to int (floats preserved bit-for-bit). Combine
  **aborts** on column mismatch; resample preserves class boundaries and a consistent column set.
- **Centering (gesture datasets).** `center.py` ports the validated algorithm from
  [`center_training_data.py`](../../scripts/preprocessing/center_training_data.py) (envelope + threshold
  segmentation + NMS + peak-tolerance QC + auto-work-axis); it is **default-on** when the profile is
  classification and declares `gesture_classes` (`--no-center` to skip), and keeps only sensor + label
  columns (dropping time/session, which the row-reorder would scramble) — [domain P-05](../principles/domain.md),
  databuilder-003. The peak-detection thresholds are the
  reference tool's, tuned on limited real data — confirm on real recordings with `check_signal_centered.py`.
- **Confirm-first config.** A `DatasetProfile` (schema in `data/skill-presets/`) is loaded then reconciled
  against the file; nothing (class map, rate, window) is auto-applied
  ([process P-02/P-03](../principles/process.md)).

## Consequences

Easier: the skills shell out to one stable CLI; one wiki edit updates validator behaviour (rules are
referenced, not restated); format issues are caught before pandas can mask them; floats survive.
Harder / watch: the window-survival model is an unverified upper bound (framed as "verify in the Processed
Data view"); `--write-anyway` can still emit a non-conforming file (documented override); centering and
resampling are gesture-first heuristics, not yet validated on real platform output; no holdout/regression
for non-classification task types yet.

## Alternatives considered

- **Single-layer validation on the parsed DataFrame** — rejected: pandas universal-newline mode and
  ragged-row truncation hide line-ending / comma-decimal violations the platform rejects on.
- **`jsonschema` for the profile / `scipy` for resampling / `pytest`** — rejected: keep the dependency
  surface to numpy + pandas + stdlib so the tool is trivially installable for third parties.
- **Rename the user's label column to `target` on export** — rejected: silent data-shape change with a
  collision risk; instead the engine keeps the reconciled name and reports the runner flags (`-t …`).
- **Write on WILL_LOSE_DATA** — rejected: a silently dead class is the worst third-party outcome; refuse
  by default, override explicitly.

## Sources

Specs databuilder-001, databuilder-002, SPRINT-data-builder-pipeline; the spec-gate and impl-gate
reviews (this session). Builds on [ADR-0001](adr-0001-user-facing-skills-mechanism.md).

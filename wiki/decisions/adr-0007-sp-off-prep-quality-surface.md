---
type: decision
status: active
updated: 2026-07-25
sources:
  - ../../specs/databuilder-016-prep-quality-sp-off.md
  - ./adr-0006-signal-processing-mode.md
  - ./adr-0002-data-builder-engine-architecture.md
  - ../architecture/platform-signal-processing-applicability.md
tags: [decision, data-builder, signal-processing, tabular, prep, quality, engine]
---

# ADR-0007 — Signal-Processing mode governs the prep / quality-report write-analysis surfaces

Status: active
Date: 25.07.2026

Extends [ADR-0006](adr-0006-signal-processing-mode.md) (which scoped the mode to `validate`) to the
`prep` / `quality-report` surfaces. Amends [ADR-0002](adr-0002-data-builder-engine-architecture.md)
`:64-70` (centering default-on). Extracted from spec `databuilder-016` (sprint task B5b).

## Context

B5a (ADR-0006) recorded the Signal-Processing mode in the profile and made `validate` skip the nine
window-based checks when it is off. The write/analysis surfaces were left for B5b: `prep` and
`quality-report` still resolved a window as before, so a tabular (SP-off) dataset had **no honest path**.
Two failure modes were measured:

- **Silent corruption when a window was present.** `prep` centered a gesture-declared tabular profile
  (re-ordering rows into windows, discarding the rest — 680 → 440 rows) and `prep --resample` fabricated
  rows (interpolating a signal that tabular data does not have) — **both under a PASS verdict**.
- **A blocked honest user when no window was present.** `prep`/`quality-report` exited 4 ("no window
  given") for a genuinely tabular profile — the very incentive gradient ADR-0006 exists to prevent.

## Decision

1. **`prep`/`quality-report` resolve the mode, not just a window.** `cli._resolve_mode` returns
   `(sp_on, window)`; `signal_processing: false` → `(False, None)` — no window is needed, the platform
   does not window a tabular dataset.
2. **`prep` honours the mode on the write path.** With SP off it **skips centering** and **refuses
   `--resample`** (`sp_off_resample_refused`, FIX_REQUIRED) — both are windowing / continuous-signal
   operations that corrupt independent rows — and passes `sp_on` to `check_dataframe`, which then skips
   the window checks and discloses via `sp_off_unverified` (ADVISORY) / `sp_off_contradicts_profile`
   (FIX_REQUIRED when gesture classes are declared). **No `validate.py` change** — those findings are
   B5a's.
3. **The ADR-0006 incentive gradient is load-bearing and preserved.** The honest tabular file (rate
   known, no gesture classes, no `--resample`) **writes** at PASS with only the `sp_off_unverified`
   advisory. Declaring `signal_processing: false` is therefore never *worse* than concealing it: where
   concealment silently corrupts (centers/resamples) or the old code blocked with exit 4, declaring
   writes a correct file. The FIX_REQUIRED refusals fire only on a **contradictory operation within the
   mode** (`--resample`, gesture classes), each of which corrupts under concealment — not on the mode
   itself. `sp_off_unverified` stays ADVISORY.
4. **A supplied window is disclosed, not silently ignored.** `sp_off_window_ignored` (ADVISORY, emitted
   by the CLI because `--window` is a CLI input) fires when SP is off and a window is supplied via
   `--window` or the profile's `window.candidates`.
5. **`--window 0` / negative is a usage error (exit 4), not a silent substitution** of the profile
   candidate; `center_per_class` guards a `None`/`<1` window with a clear `ValueError` (P-21 — the
   crash-guarded branch is made a legible contract check, and `prep` structurally never reaches it).
6. **Back-compatibility by the legacy contract.** `prep(sp_on=None)` = SP on = exactly prior behaviour;
   every existing caller is byte-identical (measured: SP-on prep output + dictionary SHA-256 unchanged).

## Rejected alternatives

- **Keep `prep`/`quality` exiting 4 on SP-off (as B5a left it).** Rejected: it blocks the honest tabular
  user while concealing the mode silently corrupts — the incentive gradient inverted, exactly what
  ADR-0006 forbids.
- **Suppress centering/resample silently for SP-off.** Rejected: silent suppression is itself the
  corruption pattern (a misleading PASS). The tool **refuses loudly** on the contradictory operation
  instead, and writes the honest tabular file.
- **Make `sp_off_unverified` blocking.** Rejected by ADR-0006 (the incentive gradient) and kept rejected.
- **Fold the non-classification `gesture_classes` gradient fix in.** `sp_off_contradicts_profile` (B5a,
  `check_dataframe`) fires with no `is_classification` guard, so a regression/anomaly profile with a stray
  `gesture_classes` is refused under SP-off though centering never engages for it — a gradient dip that
  averts no corruption. The one-line fix is a `validate.py` edit outside B5b's scope; **split to B1a**
  (P-23 — an adjacent, non-monotone repair on a surface this task does not own).

## Consequences

- ADR-0002 `:64-70` ("Centering … **default-on** when the profile is classification and declares
  `gesture_classes`") is **narrowed**: default-on only when Signal Processing is *not* off;
  `signal_processing: false` with `gesture_classes` is a contradiction (`sp_off_contradicts_profile`),
  not a centering trigger — see the amendment note on ADR-0002.
- ADR-0006's Consequences line *"`sp_off_*` appear only on the `validate` surface"* is **superseded**:
  `sp_off_unverified` / `sp_off_contradicts_profile` now also appear on `prep`, and two new codes
  (`sp_off_resample_refused`, `sp_off_window_ignored`) on `prep`/`quality-report`. Supersession note added
  to ADR-0006 (Discipline §2).
- A **known gradient dip remains** for a non-classification profile carrying a stray `gesture_classes`
  (B5a-inherited), carried out to B1a.
- Four `sp_off_*` finding codes now span the skills contract; the skills reference findings by rendered
  message + `rule_ref`, not by an enumerated code list, so no skill file changes.

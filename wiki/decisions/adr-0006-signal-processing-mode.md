---
type: decision
status: active
updated: 2026-07-25
sources:
  - ../../specs/databuilder-012-signal-processing-field.md
  - ./adr-0002-data-builder-engine-architecture.md
  - ../architecture/platform-signal-processing-applicability.md
tags: [decision, data-builder, signal-processing, tabular, validate, profile, engine]
---

# ADR-0006 — Signal-Processing mode is a profile-declared check scope

Status: active
Date: 25.07.2026

> **Amendment (25.07.2026, B5b):** [ADR-0007](adr-0007-sp-off-prep-quality-surface.md) extends this mode
> to the `prep` / `quality-report` surfaces. The Consequences line below — *"`sp_off_*` appear only on the
> `validate` surface"* — is **superseded**: `sp_off_unverified` / `sp_off_contradicts_profile` now also
> fire on `prep`, and two new codes (`sp_off_resample_refused`, `sp_off_window_ignored`) on
> `prep`/`quality-report`. The incentive gradient recorded here (declaring the mode is never worse than
> concealing it; `sp_off_unverified` stays ADVISORY) is **load-bearing on those surfaces too** and was
> preserved by B5b.

Narrows two Decision clauses of [ADR-0002](adr-0002-data-builder-engine-architecture.md). Extracted
from spec `databuilder-012` (sprint task B5a).

## Context

Signal Processing (windowing) is a per-solution platform option that is off for a tabular dataset
([applicability](../architecture/platform-signal-processing-applicability.md)). The validator applied
the window-based checks unconditionally, so a tabular file (or a windowed file whose window the user
had not yet set) was reported against rules that do not apply to it. There was no way for the profile
to state the mode.

## Decision

1. **The mode is a tri-state profile field.** `signal_processing: true | false | absent`. A non-bool
   value is a load error, so the field is never silently coerced.
2. **The mode scopes the checks, it does not gate access.** On `validate`, when SP is off the nine
   window-based checks are skipped; every mode-independent platform rule still fires. `prep` and
   `quality-report` are unchanged in B5a (their tabular support is B5b / `databuilder-016`).
3. **Suppression is disclosed, never certified.** Declaring `signal_processing: false` emits an
   ADVISORY `sp_off_unverified`: the tool has not itself reconciled "is this actually tabular?"
   against the file (the tabular-tells check is unbuilt). It is **not** blocking — blocking would
   punish the one user who declared the mode honestly and push them to conceal it. A profile that
   declares SP off **and** gesture classes is a contradiction (`sp_off_contradicts_profile`,
   FIX_REQUIRED).
4. **Back-compatibility by a legacy contract, not a migration.** `check_dataframe`/`run_checks` take
   `sp_on=None` meaning "SP on, no mode findings" = exactly prior behaviour, so every existing caller
   is byte-identical (measured: 80/80 scenarios, output + dictionary SHA-256).

## Rejected alternatives

- **Default the field on the platform's stated default (off).** Rejected: it would flip the installed
  base and read as a documented platform claim the docs do not make. No schema `"default"` is set.
- **Block on SP-off until verified.** Rejected in gate round 4 by execution: it made honest
  declaration strictly worse than concealment (the incentive gradient), and `true`/absent still
  reached PASS unreconciled. The principle that resolved it: unverified *suppression* of checks is
  unsafe and must be surfaced; unverified *addition* (declaring SP on adds checks) is safe.
- **Gate prep/quality-report in the same task.** Rejected: those are the write/analysis surfaces where
  every prior gate round found a new corruption path. Split to B5b so the `validate` fix — which
  touches nothing that writes — lands proven. (P-22 / P-23.)

## Consequences

- ADR-0002 `:35-39` (`check_dataframe` "window range, window survival") is now conditional on the
  mode — see the amendment note on that ADR.
- ADR-0002 `:56-58` ("nothing is auto-applied") is narrowed: reading `signal_processing: false` and
  suppressing checks is an auto-application. It is disclosed via `sp_off_unverified` rather than
  silent. Note the clause already did not describe the shipped engine — `sampling_rate_hz` suppresses
  `rate_unknown` on profile say-so today — so this records reality as much as it changes it.
- A new persisted profile field: every future default/semantics change reinterprets profiles already
  in users' hands. `sp_unspecified` must never be treated as a version marker.
- Two finding codes join the frozen skills contract; `sp_off_*` appear only on the `validate` surface.

---
type: architecture
status: active
updated: 2026-06-25
implementation:
  - ../../src/data_builder/profile.py
  - ../../data/skill-presets/dataset-profile.schema.json
  - ../../data/skill-presets/nordic-gesture-demo.json
sources:
  - ../decisions/adr-0001-user-facing-skills-mechanism.md
  - platform-dataset-requirements.md
  - platform-signal-processing.md
  - platform-preprocessing-options.md
  - ../../CLAUDE.md
tags: [architecture, config, preset, dataset-profile, skills, contract]
---

# data — Dataset-profile (skill preset) contract

The **contract** for the per-dataset parameters the user-facing skills and the `src/`
exporter/validator consume. The runtime file lives in `data/skill-presets/` (CLAUDE.md rule 8:
runtime data in `data/`, not `wiki/`); this page is the spec it must satisfy and how to update it.
The decision to make presets confirm-first data (not the invocable surface) is [ADR-0001](../decisions/adr-0001-user-facing-skills-mechanism.md).

## What it is

A `dataset-profile` is a small JSON object describing one dataset: the label column, sensor-axis
columns, optional session/time columns, separator, sampling rate, units, task type, class encoding
(with the continuous-vs-gesture split), and the intended window settings. It carries **no platform
facts of its own** — those stay in [`platform-*`](platform-dataset-requirements.md); the profile only
records the per-dataset values that the hard rules are checked against.

- Schema: [`data/skill-presets/dataset-profile.schema.json`](../../data/skill-presets/dataset-profile.schema.json)
- Worked example: [`data/skill-presets/nordic-gesture-demo.json`](../../data/skill-presets/nordic-gesture-demo.json)

## Invariants (the load-bearing contract)

- **Confirm-first, never auto-applied.** A skill loads a profile, then reconciles every field
  against the actual file before using it ([process P-02/P-03](../principles/process.md)). The
  worked example's `idle=0/unknown=1/gestures=2..7` indices are an *illustrative convention*
  ([scripts README](../../scripts/README.md)), not a default to apply silently.
- **Names obey the header charset.** `label_column`, `sensor_columns`, `session_column`,
  `time_column` match `^[A-Za-z0-9_-]+$` — same rule the platform enforces on column names
  ([dataset requirements](platform-dataset-requirements.md)).
- **Classification encoding starts at 0, contiguous.** `class_encoding.map` values are integers
  from 0 with no gaps; `continuous_classes` + `gesture_classes` partition the indices for the
  centering step ([signal processing](platform-signal-processing.md)).
- **One sampling rate.** `sampling_rate_hz` is a single number for the whole dataset; mixed rates
  must be resampled before upload.
- **Window compatibility, not control.** `window.candidates`/`shift`/`frequency_domain_features`
  record what the data must be *compatible* with (the user sets the real values in the platform
  UI). Conditional hard rule the validator enforces: frequency-domain **off** ⇒ window ∈ [10,1000];
  **on** ⇒ power-of-2 in [128,2048]. `shift` cannot exceed the window; `shift = window` for training.
- **Target technology drives the data type.** `target_technology` (neuton|axon) is recorded because
  **Axon/LiteRT accepts only FLOAT32** ([preprocessing options](platform-preprocessing-options.md));
  the data-type recommendation must force FLOAT32 for an Axon target regardless of value ranges.
- **File name, not just column names.** The platform forbids a larger special-character set in the
  uploaded **file name** (space and dot included) than in column names — a separate rule the
  exporter/validator checks on the output path ([dataset requirements](platform-dataset-requirements.md)).

## How to update it

1. A new per-dataset parameter is needed by a skill or the exporter/validator → add a property to
   `dataset-profile.schema.json` (keep `additionalProperties: false`), update this page's invariants,
   and add it to the worked example if it has a sensible illustrative value.
2. A new platform rule changes how a field is validated → fix the rule in the relevant
   [`platform-*`](platform-dataset-requirements.md) page; this profile only holds the value, so it
   usually does not change.
3. Never copy a platform threshold into the schema description as the source of truth — reference
   the `platform-*` page. The schema descriptions paraphrase for usability only.

## Implementation

The runtime artifacts are [`data/skill-presets/dataset-profile.schema.json`](../../data/skill-presets/dataset-profile.schema.json)
and [`data/skill-presets/nordic-gesture-demo.json`](../../data/skill-presets/nordic-gesture-demo.json)
(see `implementation:`). The `src/` exporter/validator load and validate a profile against this
schema; when that code lands, this page's invariants are the tests it must pass. Lint checks the
`implementation:` paths exist (code-drift), without semantic assessment.

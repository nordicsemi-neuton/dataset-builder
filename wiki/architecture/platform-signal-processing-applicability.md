---
type: architecture
status: active
updated: 2026-07-25
implementation:
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-solution-management.md
  - ../../src/data_builder/profile.py
  - ../../src/data_builder/validate.py
  - ../../src/data_builder/cli.py
  - ../../src/data_builder/pipeline.py
  - ../../src/data_builder/quality.py
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-solution-management.md
  - ../../raw/owner-notes/2026-07-23-signal-processing-default.md
  - ../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md
tags: [platform, signal-processing, applicability, tabular, task-framing, contract]
---

# platform — Signal Processing applicability: when to use it, when to switch it off

Signal Processing (SP) is a **per-solution option**, not a mandatory pipeline stage. Everything the
data-builder normally produces — windows, sliding shifts, an enabled feature set — exists **only when
SP is on**. With SP off the platform trains on the CSV as a plain feature table: one row = one
training sample.

Choosing the mode is upstream of every other data decision. Get it wrong and the whole preparation is
misdirected — see the ToF case below. The windowing contract itself is
[signal processing](platform-signal-processing.md); the feature catalogue is
[feature extraction](platform-feature-extraction.md); the pipeline position is step 5 of
[data pipeline](platform-data-pipeline.md).

## The switch — and its two provenances

Keep these distinguishable; they are not equally established.

| claim | provenance | status |
|---|---|---|
| SP is conditional — an option on the solution, not a fixed stage | `raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md:45` — *"**If** Signal Processing (SP) is enabled:"*; `2026-06-25-solution-management.md:29` lists SP as an on/off indicator of a solution | documentation-sourced |
| SP is **off** unless the user turns it on | [owner note, 23.07.2026](../../raw/owner-notes/2026-07-23-signal-processing-default.md) | **owner-stated, not doc-confirmed** — open verification task |

The default state is not stated anywhere in the captured docs. Until it is confirmed in the UI, treat
"off by default" as reliable enough to act on (the owner is on the platform team) but say so when it
matters, and do not present it as a documented rule.

## The two modes

| | **SP ON** | **SP OFF** |
|---|---|---|
| unit of training | one **window** of N consecutive rows | one **row** |
| windowing | yes — window size, sliding shift, sub-windowing | none; those settings do not apply |
| feature extraction | platform computes features per window per axis | none; the columns *are* the features |
| row order | must be time-ordered, never shuffled | irrelevant to the model |
| what the data must look like | a continuous time-ordered signal stream | a table of independent observations |
| our tooling | the whole gesture/activity flow targets this mode | only intake/format checks apply |

## The decision rule

Ask three questions of the data, not of the user's description:

1. **Does a single row already determine the label?** If one row is a complete observation (a full
   sensor frame, a set of derived measurements), it is tabular.
2. **Does the label vary within what a window would span?** If every run/session carries one constant
   label and the label only changes between sessions, there is no within-window structure to learn.
3. **Is there a per-sample sequential dependency to exploit?** Accelerometer and audio streams have
   one — the value at t depends on t−1. A sequence of independent snapshots does not.

Two "yes" answers to 1–2 mean **switch SP off and train it as a tabular classifier**.

### Tells that the data is tabular, not a signal

- Sensor columns are a **spatial grid or image-like** enumeration (`zone_0…zone_63`, `pixel_*`), and
  there are far more of them than the 3–9 axes of an inertial set.
- **Every session is exactly one window long, or an exact multiple of it** — a strong sign the rows
  were already grouped into events upstream.
- **The label is constant within every session.**
- The user calls the rows "frames", "images", "scans" or "snapshots".

### The cheap decisive test

Train a trivial classifier on a **single row** — no windowing — and report per-class recall.

- A class near ceiling from one row is tabular; its label carries no temporal information.
- A class near chance from one row is where the temporal or directional signal actually lives.

This costs about a minute and settles the question that hours of window-survival analysis cannot.
Measured on a spatial-grid presence dataset: the stationary class reached **~0.98 recall from a single
frame** while the two direction classes stayed at ~0.62–0.77 — establishing that presence is per-frame
and only direction needs temporal context ([harvested practice](../../raw/harvested-practice/2026-07-23-framing-and-evaluation-lessons.md)).

### The hybrid case

"Tabular" and "windowed" are not the only options. When a single row settles most classes but one
distinction needs context (as with enter vs. exit above), the right answer is a tabular model plus a
targeted amount of temporal context for that sub-problem — not windowing the entire task because one
part of it needs sequence.

## The failure this prevents

A dataset arrives described as "N Hz time-series". The description is taken at face value and a full
windowing analysis follows — window survival, class run-lengths, overlap advice. Every step is
internally correct and all of it is misdirected, because each row was already a complete observation.

The visible symptom is a windowed model that scores well during training and poorly on replay, which
invites the conclusion that the platform's export pipeline is defective. It is not: windowing N
consecutive independent rows groups unrelated samples into meaningless composites, and the training
score is overfitting to the validation slice of a set that should never have been built. No
window-survival number can surface this, because window survival assumes the frame is correct.

Worked shape: a low-resolution distance-sensor grid used for presence and direction, one full frame per
row, three classes. Every tell above was present — dozens of grid columns, every session an exact
multiple of the window, label constant per session — and the single-row baseline settled it in a minute.

## Consequence for deliverables

**Every dataset prepared for windowed gesture, activity or regression work requires SP to be switched
on.** Since it is off by default, a user handed a window size, a sliding shift and a feature enable-set
without being told to turn SP on will not find those settings at all — or will train a tabular model on
data prepared for windowing and get a meaningless result.

Therefore **"Signal Processing: ON" is the first row of the recommended-settings table in a prepared
dataset's README**, ahead of window size and shifts. Symmetrically, when the data is tabular the README
must say **"Signal Processing: OFF"** and omit the window/shift/feature rows entirely rather than
leaving them at defaults.

## Implementation

The data-builder does not set this option (the user does, on the platform), but as of B5a
([ADR-0006](../decisions/adr-0006-signal-processing-mode.md), `databuilder-012`) it **records** it: the
profile carries `signal_processing: true | false | absent` ([`profile.py`](../../src/data_builder/profile.py)),
and on the `validate` surface ([`cli.py`](../../src/data_builder/cli.py) →
[`validate.py`](../../src/data_builder/validate.py)) an SP-off profile skips the window-based checks
and emits an `sp_off_unverified` advisory.

As of **B5b** ([ADR-0007](../decisions/adr-0007-sp-off-prep-quality-surface.md), `databuilder-016`) the
`prep` and `quality-report` surfaces honour the field too: [`cli.py`](../../src/data_builder/cli.py)'s
`_resolve_mode` returns `(sp_on, window=None)` for a tabular profile; [`pipeline.py`](../../src/data_builder/pipeline.py)'s
`prep` then **skips centering and refuses `--resample`** (both would corrupt independent rows) while still
writing the honest tabular file at PASS — the ADR-0006 incentive gradient — and passes the mode to
`check_dataframe`; [`quality.py`](../../src/data_builder/quality.py)'s `quality_report` skips the windowed
source-comparison when there is no window. A supplied window is disclosed (`sp_off_window_ignored`), not
silently ignored.

Two obligations remain **unimplemented** (both SPRINT-2):

1. **Detect the tabular tells during framing** and stop, rather than preparing the wrong thing. The
   tells above are all computable from the file (column count and naming, session lengths against the
   intended window, label variance within session); none is checked today. This is what
   `sp_off_unverified` stands in for — building it is what would let that advisory be removed.
2. **State the required mode in the deliverable**, as the first row of the settings table. Ownerless.

Authoritative source: `raw/platform-docs/`, plus the open verification task in
[the owner note](../../raw/owner-notes/2026-07-23-signal-processing-default.md).

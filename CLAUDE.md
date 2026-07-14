# CLAUDE.md — LLM wiki for developing the data-builder product

> **Maintenance:** on lint, Claude re-checks that our compiled knowledge of the Nordic Edge AI Lab documentation still matches the live docs (the platform's rules are law for our output) — [methodology/lint.md](methodology/lint.md).

Core idea: don't re-derive the same knowledge from raw materials every time a question comes up. Instead, compile each source once into a permanent, interlinked wiki. From then on Claude reads the wiki, not the raw materials, when it answers. It returns to the raw only to integrate new data or resolve a contradiction.

The root file holds **always-on rules and pointers**. Detailed procedures live in [methodology/](methodology/) and are read on trigger.

---

## About the project

`data-builder` is a tool for preparing data from inertial sensors (accelerometer, gyroscope of smartwatches, etc.) for upload to an ML platform that uses that data to automatically build models recognizing states/activity (walking / running / swimming, etc.). The tool analyzes raw CSVs and brings them into line with the platform's requirements and constraints (analysis + preprocessing). It is meant to be distributed to platform users as a data-preparation assistant.

**Constraints that shape every decision:**
- **The platform's rules are law.** Output data must conform to the platform's requirements and constraints; these are extracted from its documentation and live in `wiki/architecture/` (+ `wiki/discovery/`). Preparation relies on them, not on guesswork.
- **The maintainers' code is the source of truth.** Preprocessing code comes from Nordic and lives in `src/`; the wiki stores knowledge about it (what it does, its contracts), not a copy of it.
- **Correctness over speed.** The tool is used by third parties — code goes only through the task execution cycle (spec → independent review → implementation → re-review).
- **Domain.** Inertial time series; the sampling rate in Hz differs between datasets (always record it explicitly); training sets are usually ≤ ~100 MB.
- **Default units.** Acceleration — *g* or *m/s²*; angular velocity — *°/s* or *rad/s*; time — timestamp/rate (Hz). If the platform dictates otherwise — its rules take priority.

### The target platform — Nordic Edge AI Lab

The platform is **Nordic Semiconductor's Edge AI Lab** ([docs](https://docs.nordicsemi.com/bundle/edge-ai-lab/page/index.html)) — a no-code TinyML service that auto-builds compact models (the **Neuton** framework; **Axon NPU** via LiteRT) for Nordic wireless SoCs (Cortex-M0/M4/M33). Full, verified knowledge lives in `wiki/architecture/platform-*` and `wiki/discovery/platform-*` — **that wiki is canonical; the bullets below are orientation only, trust the wiki on any conflict, and read the relevant `platform-*` page before any data task.**

**Always-on essentials — the input-CSV contract our output must satisfy:**
- One **CSV** (combine multiple recordings first; one dataset → one model), **UTF-8 / ISO-8859-1**, **header row first**, separator ∈ {`,` `;` `|` `^` tab}, **dot** decimal (no thousands sep), **CRLF/LF**; column names unique & `[A-Za-z0-9_-]`.
- **All values numeric; no empty / `NA` / `NAN`.** Storage types **INT8 / INT16 / FLOAT32** (Axon ⇒ FLOAT32 only). Timestamps as epoch/relative, not calendar strings.
- **Inertial layout:** one row = sensor readings at one timestamp + a label column; rows **time-ordered, never shuffled** (the platform does the windowing). **Single sampling rate** — resample if mixed; always record the Hz.
- **Classification target** starts at **`0`**, contiguous encoding; **≥2 classes, ≥20 samples each**.
- **Windowing (platform-side):** window **10–1000** samples (**128–2048, power-of-2** when frequency-domain features are on). **Holdout** must match the training file's structure/field order, else the platform auto-splits **80/20**. **Anomaly detection** = unlabeled normal-only data, single model, **no holdout**.
- **No platform-stated file-size limit** (the "≤~100 MB" above is *our* assumption, not a platform rule).

---

## Architecture

```
input/           ← Drop zone for incoming material. Toss any new material in here as-is —
                   on "process this" Claude sorts it into raw/ (by type + name) and absorbs it into wiki/.
                   Empties out after processing. Not an archive (the archive is raw/).
raw/             ← Raw sources, read-only. Subfolders are set up by bootstrap for the project's
                   sources; they grow as needed (depth is free).
  platform-docs/ (platform documentation: capabilities, rules, constraints on data)
  samples/       (sample sensor CSVs — to understand the input format)
wiki/            ← Compiled knowledge. Managed by Claude. Flat, depth = 1.
  decisions/     (ADRs — what was decided and why; linked via supersession)
  discovery/     (knowledge about the outside world: sensors, formats, scenarios, the platform as a product)
  synthesis/     (written-back answers, cross-cutting analyses)
  principles/    (rules drawn from incidents; read before a non-trivial task)
  architecture/  (CENTRAL TYPE: modules, contracts, invariants, multi-step workflows
                  of the tool + platform rules/constraints as a contract on the data;
                  the ## Implementation section and the implementation: field are mandatory)
  index.md       (catalog — one line per page)
  log.md         (operation log, append-only)
methodology/     ← Instructions for Claude (read on trigger). Part of the template.
  ingest.md  query.md  lint.md  page-conventions.md
  state-rules.md  index-log-format.md  bootstrap.md
  spec-lifecycle.md    (task flow: pending/active/completed/rejected)
output/          ← Root of working files — always present. Created empty;
                   subfolders (drafts/ etc.) appear as they are actually needed. A FINISHED dataset goes
                   in its own folder output/<name>/ (upload CSV + its dictionary + profile recipe + a
                   plain-language README naming the one file to upload) — never loose/duplicated files
                   beside it (wiki/principles/process.md P-09). Rebuild overwrites the folder in place.
specs/           ← Task working documents: one spec per task <feature>-NNN-<slug>.md,
                   status in frontmatter (active/completed/rejected), NOT in subfolders.
                   STATE.md — index of active ones. Flat.
src/             ← Production code of the tool (preprocessing, pipeline). Source of truth on
                   disk; appears when code arrives/is written. Only knowledge about it goes into the wiki.
data/            ← Runtime data (configs, dictionaries, templates), if any appear. Not wiki.
  skill-presets/ (per-dataset profile schema + worked examples the user-facing skills load
                  then CONFIRM against the file — never auto-applied. Contract lives in
                  wiki/architecture/data-skill-preset-contract.md via implementation:.)
scripts/         ← One-off/experimental scripts (draft code) — except the reference diagnostics the
                   skills drive (validated through the task cycle, e.g. feature_separability.py via
                   databuilder-005; treat those as shipped tooling, not draft).
data-builder.py  ← Root launcher: a no-logic delegation shim into src/ (one cross-platform command
                   form, no PYTHONPATH). Production code still lives in src/.
.claude/skills/  ← The SHIPPED data-preparation assistant: one <slug>/SKILL.md per user-facing
                   skill (nrf-prep-dataset, nrf-validate-upload, nrf-diagnose-data, nrf-collection-advice,
                   nrf-feature-advice, nrf-build-dataset). Distinct from methodology/ (that is wiki-MAINTENANCE for
                   Claude, not for the end user). Skills REFERENCE the wiki by path, never
                   restate it. _shared/ holds the cited platform-contract.md digest and runtime.md
                   (environment setup + the per-OS command form the skills use). See
                   wiki/decisions/adr-0001-user-facing-skills-mechanism.md.
CLAUDE.md        ← This file.
STATE.md         ← Operational state (intentions, not facts; not canonical).
```

Rules:

- **`raw/` is immutable.** Append only. The original wording matters during re-verification.
- **`wiki/` is managed by Claude.** A human reads it but does not edit it by hand. It grows through: (a) ingest of a source from `raw/`; (b) write-back of an answer into `synthesis/` after a query; (c) extraction of an ADR from an accepted decision; (d) recording a principle from an incident. If there's an error in the wiki — fix the source in `raw/` (or tell Claude), and it recompiles.
- **Wiki depth = 1.** One level of topical subfolders (types are above that), no deeper. 30+ homogeneous pages in one type → horizontal expansion (a new top-level type or name prefixes), not subfolders.
- **`raw/` is the exception.** Inside `raw/`, depth is allowed as needed (storage meant for human navigation).
- **`methodology/` is part of the template, not a work area.** Edited only by a human when revising the methodology.
- **`specs/` are task working documents, not code and not wiki.** Mutable while `active`; after `completed`/`rejected` it is frozen. Details — [methodology/spec-lifecycle.md](methodology/spec-lifecycle.md).
- **Code beats the wiki.** For the code itself, truth is on disk (`src/`); only knowledge about it (contracts, invariants, facts) goes into the wiki. Code/wiki divergence → truth is in the code, refresh the wiki.
- **git is optional.** Under version control — Claude commits after ingest/bootstrap; otherwise history lives in `wiki/log.md` and page dates, and the "commit" steps are skipped.
- **Structure grows as needed.** A source doesn't fit the existing `raw/` subfolders — set up a new one (depth is free in `raw/`; flat in `wiki/`). Changed the layout — reflect it in this file's tree and in the affected context files.
- **File names.** Descriptive, with underscores/kebab-case. Raw files are prefixed `YYYY-MM-DD-` when the source date is known.

---

## Source hierarchy

1. **CLAUDE.md** — always-on rules and context.
2. **`methodology/`** — operation details. On trigger, not in the background.
3. **Wiki** (`wiki/`) — canonical knowledge from ingest.
4. **Raw sources** (`raw/`) — first source when in doubt.

**wiki vs source:** re-verify the source and fix the wiki (don't assume the wiki "knows better" — that's how drift sets in). New knowledge goes into `wiki/` first via ingest.

**`STATE.md` is a separate axis**, not part of the hierarchy: intentions and progress, not claims about the world. It doesn't conflict with the wiki (different domains).

---

## Operational state

`STATE.md` in the root is the single place for current plans and progress. **The structure is a fixed set of sections** (Stage · Path to goal · In progress · Next · Completed this past week · Blockers and risks · Known tech debt; mechanics — in [methodology/state-rules.md](methodology/state-rules.md)). Empty sections stay, marked `_empty_`.

**Triggers (for Claude):**
- At session start — silently read STATE.md (context on "where we left off").
- On questions like "where did we leave off / what's in progress / what's next / blockers" — STATE.md is the primary source.
- If `_Updated:_` is older than 7 days — in the first reply, offer "STATE is N days stale, what changed?".

**All startup checks are silent.** STATE freshness and lint freshness (§5 "Discipline") are mentioned in the first reply **only on deviation**. If there's nothing to say, Claude stays silent — it does not list "all good".

---

## Wiki: page types and operations

Types — see the "Architecture" tree (the central type is `architecture/`; plus `decisions/ discovery/ synthesis/ principles/`). Frontmatter, per-type formats, journal pages, cross-references, name prefixes — [methodology/page-conventions.md](methodology/page-conventions.md).

**Three operations** (triggered by a plain phrase; Claude infers from meaning):
- **Ingest** ("process this", "remember this", "add to the wiki") → [methodology/ingest.md](methodology/ingest.md).
- **Query** ("what do we know about X", "write me a brief", "compare A and B") → [methodology/query.md](methodology/query.md).
- **Maintenance** ("run maintenance"; also understands "run lint", "check the wiki") → [methodology/lint.md](methodology/lint.md).

**Domain flow of a unit of work:**
- **Task-spec flow** — backlog in STATE → file in `specs/` with `status: active` → ADR extraction on acceptance, the spec is frozen as `completed`. Details — [methodology/spec-lifecycle.md](methodology/spec-lifecycle.md).
- **Sprints** — a milestone from "Path to goal" with ≥3 tasks is set up as `specs/SPRINT-<NAME>.md` (`kind: sprint`); the task list lives in the sprint spec, not in STATE. Same file — [methodology/spec-lifecycle.md](methodology/spec-lifecycle.md).

**Format of `index.md`/`log.md`** — [methodology/index-log-format.md](methodology/index-log-format.md).

---

## Discipline (what keeps the wiki from rotting)

1. **Filter at the input.** Only what you're ready to defend gets into the wiki.
2. **Supersession instead of silent disappearance.** The old stays, marked `superseded` and linked to its replacement.
3. **No false precision.** No numeric confidence scores — credibility is visible from the source chain.
4. **Human in the write loop.** Claude proposes; a human confirms a non-trivial wiki mutation.
5. **Maintenance (lint) is not optional.** Once a week. At startup Claude reads the date of the last `lint` in `wiki/log.md`; > 7 days — it offers a run.
6. **Schema first, then mechanism.** Something's off — first fix this file or `methodology/`, don't breed workarounds.
7. **Schema extension is horizontal only.** A new top-level type in `wiki/` (flat) or a new top-level folder. Deepening types is forbidden. `raw/` is the exception.
8. **Runtime data goes in `data/`, not `wiki/`.** Configs, dictionaries, templates live in top-level `data/`; the runtime consumes them, Claude does not read them as knowledge. In `wiki/architecture/` goes the **contract** (schema + how to update it) via the `implementation:` field. Putting a runtime file into `wiki/` is a typical mistake.
9. **Knowledge synthesis at the close of a unit of work.** When a unit of work closes, Claude must review what new knowledge it produced and propose entering it into `wiki/` across all relevant types — not just the obvious one. A human confirms (ADRs/principles — never silently). Skipping = the wiki lags behind what we actually know. What a "unit of work" is and how knowledge is assessed at close — [methodology/spec-lifecycle.md](methodology/spec-lifecycle.md) (task-spec/sprint) and the close of a research milestone in [methodology/ingest.md](methodology/ingest.md).

---

## Principles of how Claude works on tasks

Every non-trivial task goes through two phases: first **stop and think**, then act.

**Non-trivial** — where a choice is needed (between approaches, wordings) or a plan (several steps/files). **Trivial** (no "think" phase needed): a typo, a rename, restating one page. When in doubt — treat it as non-trivial.

### Before starting — the "think" phase

**Close every request in the message (even for trivial tasks).** If there are several requests — list them at the start of the reply and close each one; give concrete action items (commands, paths) first, before the analysis. Don't burrow into one sub-question and lose the rest — a recurring mistake.

1. **Re-read the relevant principles** (`wiki/principles/<applicability>.md`) — rules extracted from past cases.
2. **State your assumptions.** Uncertainty — ask, don't guess.
3. **Show the different readings** if the request is ambiguous.
4. **Don't make things up.** Numbers and facts come only from sources/wiki; no data — `[needs clarification]`.
5. **One option at a time**, starting with the simple one.
6. **Object when warranted**, rather than silently carrying out a bad decision.

### During — the "act" phase

1. **One task at a time.**
2. **Simplicity first.**
3. **Surgical changes.**
4. **Execution from the goal** (success criteria before starting).
5. **Code only through the task execution cycle**: spec → independent review by subagents (3 on correctness + 1 on impact to modules) → implementation → re-review by running tests → report; an error → loop back through the cycle; a scope gap → into the spec; a blocker outside scope → to the human with options. Full version — [methodology/spec-lifecycle.md](methodology/spec-lifecycle.md).
6. **In human terms** — explain through action and benefit, not the inner kitchen (tool names, sandbox/permissions, technical reasons, folder/type/operation names as jargon). Need permission or something didn't work — say the meaning in plain words.

### After — recording a principle

A rule "always X / never Y" was born — propose recording it in `wiki/principles/<applicability>.md` with its source. Only from concrete cases, not from general considerations.

---

## Documents and naming

This concerns Claude's work products. Artifacts inside `wiki/` follow [methodology/page-conventions.md](methodology/page-conventions.md).

- **Where to put things:** sent from outside, not edited by us → `raw/`; knowledge → `wiki/` via ingest; working files → `output/` (+ `specs/` for tasks, `src/` for production code).
- **File names.** Descriptive, in English, with underscores; with a date when appropriate.
- **Dates.** In prose `DD.MM.YYYY`, in names/YAML `YYYY-MM-DD`.
- **Domain units (sensors).** Acceleration — *g* or *m/s²*; angular velocity — *°/s* or *rad/s*; time — timestamp or sampling rate (Hz). The rate differs between datasets — record it explicitly. The platform requires other units/format — its rules take priority (from `wiki/architecture/`). There are no monetary quantities in this project.
- **Numbers in documents.** Always with a source; without one — `[needs clarification]`.

---

## Bootstrap

No `wiki/`, no working layer, or no `STATE.md` (or partially destroyed) — Claude follows [methodology/bootstrap.md](methodology/bootstrap.md). Once at initialization; again — only on recovery.

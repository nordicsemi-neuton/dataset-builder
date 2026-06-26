---
type: decision
status: active
updated: 2026-06-25
sources:
  - ../../CLAUDE.md
  - ../architecture/platform-dataset-requirements.md
  - ../synthesis/support-diagnostic-playbook.md
  - ../principles/process.md
  - ../../scripts/README.md
tags: [decision, skills, packaging, distribution, mechanism, user-facing]
---

# ADR-0001 — User-facing capabilities ship as Skills, not instructions or presets

Status: active
Date: 25.06.2026

## Context

The data-builder is "meant to be distributed to platform users as a data-preparation
assistant." Nordic asked for built-in capabilities covering: (1) process one/many files
into upload-ready training data; (2) data-quality analysis + collection advice; (3) feature-
engineering advice for class separability; (4) other useful capabilities. And asked the
mechanism question directly: **Skills? Instructions? Presets?**

Constraints that shape the answer:
- The four asks are *distinct user intents* with distinct entry conditions ("prepare my
  files" vs "is my data any good" vs "which features separate my classes" vs "my model
  misbehaves"). They need routing on the user's wording.
- The load-bearing parameters (label column, class encoding, sampling rate, window size) are
  **per-dataset** and must be reconciled against the file. [process P-02/P-03](../principles/process.md)
  is explicit: re-derive the number yourself, treat stated values as hypotheses. The
  [scripts README](../../scripts/README.md) flags `idle=0/unknown=1/gestures=2..7` as an
  *illustrative convention, not a platform rule*.
- The wiki is the single source of platform facts; CLAUDE.md forbids duplication and deepening
  the schema (extension is horizontal only). The word "methodology" is already taken by the
  wiki-MAINTENANCE manual addressed to Claude, not the end user.

## Decision

**User-facing capabilities ship as Claude Code Skills** — one `<slug>/SKILL.md` per skill under
a new top-level `.claude/skills/`. A skill's `description` is the routing primitive that selects
the right procedure from the user's literal wording.

Catalog (covers the four asks): `prep-dataset`, `validate-upload`, `diagnose-data`,
`collection-advice`, `feature-advice`. (Five skills: "process files" splits into *transform*
+ *gate*; the pre-upload gate and post-deploy triage are the highest-value "other" capabilities.)

Supporting roles, deliberately demoted:
- **Presets = confirm-first DATA**, not the invocable thing. A per-dataset profile schema +
  worked examples live in `data/skill-presets/` (CLAUDE.md rule 8: runtime data in `data/`,
  not `wiki/`). A skill *loads* a preset then *confirms it against the file* — never
  auto-applies it (that would re-introduce the exact overfit P-02/P-03 exist to catch).
- **Instructions = one shared cited reference**, `.claude/skills/_shared/platform-contract.md`,
  so the skills don't each restate the contract (drift risk). It cites `wiki/architecture/
  platform-*` per line; on any conflict the skill re-reads the wiki. It is NOT placed under
  `methodology/` and does not reuse the word "methodology" in user-facing copy.

The unifying rule: **skills reference the wiki by path, never copy it** — one wiki edit updates
skill behaviour with no fan-out and no rot.

Authoring line (recorded as [process P-08](../principles/process.md)): narration / orchestration /
reference = authored directly in `SKILL.md`; any new data-*transform* a user relies on is `src/`
code built through the spec → review → implement → re-review cycle.

## Consequences

Easier:
- The right procedure fires from the user's words; one wiki edit propagates to every skill.
- The pre-upload gate (`validate-upload`) and post-deploy triage (`diagnose-data`) pre-empt the
  failure modes users actually hit (silent data loss, dead classes).
- Three skills (`diagnose-data`, `collection-advice`, `feature-advice`) need no new code — they
  wrap the existing `scripts/` and cite the wiki.

Harder / new obligations:
- Two new top-level locations to keep documented in the CLAUDE.md tree (`.claude/skills/`,
  `data/skill-presets/`) — done in this change.
- `prep-dataset` and `validate-upload`'s hard-reject checks need new `src/` code (no validator/
  exporter exists today); each goes through the task cycle.
- **No versioning story** yet for skills once distributed to third parties — they could drift
  from the canonical wiki. Flagged as known tech debt; revisit before wide distribution.

## Alternatives considered

- **Instructions only** (a paragraph in CLAUDE.md or a `methodology/` file) — cannot trigger-
  dispatch on user wording; read every turn yet still aimed at the wrong moment; `methodology/`
  is template + human-edited-only and addresses Claude-as-maintainer (wrong audience + name
  collision). Survives only as the shared cited reference.
- **Presets as the primary primitive** (a profile that auto-applies) — encodes per-dataset
  assumptions as defaults, the precise failure mode P-02/P-03 catch; carries no procedure and no
  reporting contract. Kept only as confirm-first data.
- **A wiki page / new wiki type for the skills** — a skill is an executable procedure, not
  compiled knowledge a human reads; filing it in `wiki/` is the "runtime file into wiki/" mistake
  (rule 8).
- **One mega-skill / eight stage skills** — a mega-skill loses routing; eight over-fragments
  (combine/check/prep/validate/export are moves of one "prepare my data" intent). Five is the
  fewest that keeps the four intents separate.

## Sources

Design analysis, this session (understand → 3-lens design panel → synthesis). Rests on
[CLAUDE.md](../../CLAUDE.md) discipline, the [dataset-requirements contract](../architecture/platform-dataset-requirements.md),
the [diagnostic playbook](../synthesis/support-diagnostic-playbook.md), [process principles](../principles/process.md),
and the [scripts README](../../scripts/README.md).

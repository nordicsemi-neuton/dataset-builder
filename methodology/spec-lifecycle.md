# Task-spec flow

A spec is the document of a specific feature or task: the problem, what will change, the implementation, the acceptance criteria. Specs live in the top-level folder `specs/` — this is a **third class of artifact**: not a disposable scratch (like `output/`) and not compiled knowledge (like `wiki/`), but long-lived development working documents — mutable while the task is active, frozen afterward.

**Why a separate folder, and not `output/` or status subfolders.** An active spec is a document against which code is written for weeks; "a desk you can tidy up" doesn't suit it. At the same time `active/completed/rejected/` subfolders would duplicate STATE.md, and parallel lists are forbidden ([state-rules.md](state-rules.md), rule 1). The solution: a flat `specs/`, **status in frontmatter**, STATE.md as the index of active ones.

## Spec frontmatter

```yaml
---
feature: auth
status: active | completed | rejected
updated: YYYY-MM-DD
adr: [adr-0012]          # link to the extracted ADR; appears on completed/rejected
---
```

Status is mandatory — by it STATE and `grep "status: active" specs/*` find what's in progress.

## Stages

| Stage | status | Where | What |
|---|---|---|---|
| **Backlog** (not taken) | — | STATE.md "Next" / "Path to goal" | One line. No file. |
| **In progress** | `active` | `specs/<feature>-NNN-<slug>.md` + STATE "In progress" | Full spec, mutable. |
| **Landed** | `completed` | `specs/...` (frozen) + ADR in `wiki/decisions/` + code in `src/` | Core → ADR; the spec is kept as a snapshot. |
| **Rejected** | `rejected` | `specs/...` (frozen); optionally an ADR | A unique record of "why we did NOT do it". |

## Sprints — sets of tasks

When a milestone from "Path to goal" requires **≥3 task-specs**, it is set up as a **sprint spec** — a plan container. A single task doesn't need a sprint (needless overhead); a sprint is needed when the work breaks into several verifiable steps.

**File:** `specs/SPRINT-<NAME>.md`, frontmatter `kind: sprint` + `status: pending | active | completed`. Flat in `specs/`, next to the task-specs.

**Contents:** the sprint goal; a **task list** (with status and a link to the task-spec once it's set up); the sprint acceptance; a log of decisions/edits (what was learned along the way). The sprint spec is **mutable while `active`** — edited as tasks are done (its nature, unlike a frozen `completed` task-spec).

**Execution algorithm:**
1. The sprint spec defines the set of tasks (in broad strokes; detailed along the way). **The plan passes the independent-review gate before tasks start** (the same mechanics as the cycle below): is the decomposition correct; are the design's conditions and assumptions too broad/narrow; which modules does the task bundle touch as a whole. Plan-level defects (a wrong gate condition, a missed dependency) are cheapest to catch here — before the first line of code.
2. Take the next task → **write the task-spec** (`<feature>-NNN-...`, as usual) → run it through the **task execution cycle** (see below: spec → independent-review gate → implementation → re-gate → report) → close it by the task's acceptance.
3. Learned something new along the way → **edit the sprint spec** (added/removed/reworded tasks).
4. The next task. When all are closed and the sprint acceptance is met — the sprint spec → `completed`.

**No duplication with STATE.** The task list lives **only in the sprint spec**. STATE "In progress" links to the active sprint + the active task (by a line), not repeating the list; "Path to goal" lists the milestones, the active milestone = the active sprint.

**ADRs** are extracted from individual task-specs on their acceptance, as usual. A sprint spec produces no ADR — it's a plan, not an architectural decision.

**File skeleton** (copy whole; `depends_on`/`blocked_by` are optional):

```
---
kind: sprint
status: pending | active | completed     # pending = set up, not yet started
updated: YYYY-MM-DD
depends_on: [SPRINT-X, FEATURE-NNN]      # opt.: sprints/specs it stands on
blocked_by: "<what blocks the start>"    # opt.: remove once the blocker is cleared
---
# SPRINT-<NAME> — <goal in one line>

**Goal:** <what we consider achieved at the end>.

## Tasks

| #  | Task                                | Status | Depends |
|----|-------------------------------------|--------|---------|
| N1 | <broad stroke; task-spec when taken> | 📥     | —       |
| N2 | …                                   | 🟡     | N1      |

Statuses: 📥 queued · 🟡 in progress/partial · ✅ done.
The "Depends" column — task numbers or external specs.

## Sprint acceptance
- [ ] <verifiable exit criterion>
- [ ] Regression gate: <what must not degrade>

## Log
- **DD.MM.YYYY** — <decision / edit to the task set / finding along the way>.
```

## Working file

When a task is taken into work — a `specs/<feature>-NNN-<slug>.md` is set up (for example, `auth-012-pkce-flow.md`; the number is continuous, not reset). While `status: active` — it lives freely, appended to and rewritten. A large spec can be split into files with a common prefix (`auth-012-spec.md`, `auth-012-tests.md`, `auth-012-rollout.md`).

## Task execution cycle (mandatory for code)

Between "spec set up" and `completed`, a task with code goes through a **fixed cycle with independent-review gates**. The steps are not skipped. "Independent review" = separate subagents (Agent/Task), each with its own context, not seeing each other's verdicts; each is told to look for *what's wrong*, not to confirm.

**How to invoke this (for the human).** Listing the steps — "review with agents, re-check, report" — isn't needed: the cycle is mandatory by default. It's enough to name the task ("take task X" / "let's implement X, it's a sprint"), and Claude unfolds the cycle itself.

1. **Spec before code.** Code isn't written until there's a task-spec: the problem, what changes, how we implement, **acceptance criteria**. (A trivial edit — a typo, a rename, a comment fix — needs no spec or cycle; the cycle kicks in as soon as the task grows to a spec. See "Don't breed specs speculatively" below.)
2. **Spec gate — ≥4 independent reviews (before implementation), in parallel:**
   - **3 subagents — correctness and completeness:** does the spec solve the posed task, are any requirements missed, are the acceptance criteria realistic;
   - **1 subagent — impact on other modules:** what else in the system is affected, which contracts/invariants/calls break, where the regressions are (input — `wiki/architecture/`); **flags irreversibility and blast radius** (pinned forever, silent data corruption, breaks consumers' contracts).

   Comments are gathered → the spec is edited (mutable while `active`) → the gate **repeats** until the review is clean. **The gate scales with risk:** an irreversible or broad-impact change (flagged by the impact reviewer) gets a reinforced gate — more verifiers and a separate adversarial round aimed at *refuting* that the change is safe; a routine local edit — the baseline 3+1.
3. **Implementation** — strictly per the accepted spec.
4. **Implementation gate — re-review (after the code):** the same structure — correctness + impact on modules. Correctness is checked **by execution**: run the tests and acceptance criteria (no tests — write and run them), reproduce the behavior, not just re-read the code. Agent review is on top of the run, not instead of it; "no regressions" is confirmed by the same run over the affected modules.
5. **Report.** Claude reports the result **in the user's language** (what was done, what was checked, where we deviated from the spec) — see "Principles of how Claude works → In human terms".

**Loop on errors.** An error at any step → the task returns to the start of the cycle and goes through it again, until the implementation is error-free. Doesn't converge in a reasonable number of passes — that's a **blocker** (below), not an infinite loop.

**Gap within scope.** It turned out the spec didn't account for something that **falls within the task's scope** → write it into the spec, implement it in the same cycle (that's what the active spec is mutable for).

**Blocker outside scope.** The task runs into work **beyond its own scope** (for example, another module needs reworking) → **don't drag it silently**: raise it to the human, propose options (a separate stand-alone task / a separate sprint), record it in `STATE.md` "Blockers and risks" and in the `blocked_by:` of the spec/sprint. The human's decision spawns a new spec or `SPRINT-<NAME>.md`.

## The "active → completed" transition (the main gesture)

When a feature is landed in code and the acceptance criteria are met, **Claude proposes extracting an ADR** (never automatically — only on confirmation): the architectural core (the chosen approach, rejected alternatives, consequences) moves to `wiki/decisions/adr-NNNN-<slug>.md`. Bidirectional links: the ADR in `sources:` points to the spec or PR, the spec in its `adr:` field points to the ADR.

Then the spec is **frozen, not deleted**: `status: completed`, and an anti-rot inoculation is added to the header:

> **⚠ Snapshot of intent at development time (DD.MM.YYYY). Current behavior is in the code and in [ADR-NNNN](../wiki/decisions/adr-NNNN-....md). This spec is not updated; later changes to the same area get their own specs.**

Why we keep it rather than delete it: the ADR is deliberately terse and doesn't hold the full problem statement, the considered edge cases, the rollout plan. The snapshot stays valuable as a history of the iteration. The rot risk (a stale spec looks authoritative) is neutralized by the inoculation — the spec honestly declares itself a snapshot, not a source of truth about current behavior. Future changes to the same code area spawn new specs; the old one remains the record of its iteration.

In STATE the task moves to "Completed this past week", from where after a week it collapses into a link to the ADR.

## Assessing new knowledge at completion (mandatory)

**At the close of any work — an individual task-spec OR a sprint (as well as a standalone task without a spec) — Claude must review the new knowledge and propose entering it into `wiki/`.** Not just the ADR. Go through all five types:

- **decisions/ (ADR)** — was an architectural/product choice made (with rejected alternatives)?
- **architecture/** — did a contract, module, or multi-step product workflow change?
- **discovery/** — did we learn something new about the user, a segment, the input data format, a competitor?
- **synthesis/** — is the outcome of the work worth recording as a cross-cutting analysis, retrospective, or comparison?
- **principles/** — was a rule born from an incident/near-miss ("always X / never Y")?

Claude **proposes** specific entries (type + title + gist) — a human confirms (CLAUDE.md: "human in the write loop", ADRs/principles — never silently). The goal — that knowledge from completed work doesn't stay only in the code/spec/chat, but makes it into the wiki. Skipping this step = the wiki lags behind what we actually know.

This is the **development-layer** close. The symmetric close of the **research layer** (a batch of interviews, a market/competitor breakdown) is the synthesis pass, see [ingest.md](ingest.md).

## Rules

- **Don't breed specs speculatively.** A full spec is written when the task is taken into work or right before it. Ideas for the future are one-liners in STATE, not files.
- **`completed`/`rejected` are frozen.** After freezing, substantive changes go through a new ADR or a new spec, not by editing the frozen file after the fact.
- **`rejected` is always recorded when the refusal is meaningful** ("decided not to do X, because Y"). It's the only record of the un-built — there will never be code for it, and git won't show anything either. Optionally duplicated by an ADR with `status: rejected`, if the decision is large.
- **`specs/` is not `wiki/`.** No mandatory lint/ingest and no `sources:` requirements like in the wiki; these are working documents, edited by human and Claude. But the frontmatter with `status` is mandatory.

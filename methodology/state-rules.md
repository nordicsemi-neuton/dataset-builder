# STATE.md — structure and update rules

`STATE.md` in the root is the single place for current plans and progress. The wiki holds knowledge (append-mostly, with sources, atomic); STATE holds intentions (frequent rewrites, no sources, all in one file for an at-a-glance view).

## Structure

A fixed set of sections, always in the same order. Empty ones — marked `_empty_`, not deleted (the eye gets used to the layout).

**7 sections (task flow):**

1. **Stage** — where we are in the lifecycle and what the current goal is (idea / prototype / MVP / beta / v1 / v2).
2. **Path to goal** — milestones from the current moment to the goal, in order. The whole path in one place.
3. **In progress** — what's in flight right now (usually one or two tasks). The spec file is in `specs/` (`<feature>-NNN-...`, `status: active`). For a sprint — a link to the active sprint spec (`SPRINT-<NAME>.md`) + the active task; the sprint's task list is not duplicated in STATE (it's in the sprint spec).
4. **Next (1–2 weeks)** — backlog; one-liners here, the spec file is set up when taken into work.
5. **Completed this past week** — a buffer zone before collapsing.
6. **Blockers and risks**.
7. **Known tech debt** — a list of links to ADRs with status `active` and the `tech-debt` tag.

**Granularity reflects the horizon.** Early on — broad strokes; as it gets closer it breaks down. Don't atomize prematurely (false precision).

## Update rules

1. **Source of truth.** STATE is the single place for the current plan. No parallel lists.
2. **Claude updates at three moments:** (a) silently reads it at the start of a session; (b) after completing a significant item, moves it from "In progress" to "Completed this past week"; (c) after an ingest that shifts priorities — proposes an edit, a human confirms.
3. **A human updates at two:** a priority change; a new blocker. Via chat or by hand.
4. **Freshness by date.** The `_Updated:_` field is mandatory. The startup freshness trigger (what to do if stale) is in CLAUDE.md (always-on); not duplicated here.
5. **Link to the wiki via markdown links.** An item that references knowledge does so via `[Title](wiki/type/slug.md)`. Knowledge lives in the wiki; in STATE — the wording and the link.
6. **The "completed" buffer.** Hangs for a week, then collapses: one that produced a wiki page → a link to it; under git, routine with no trace → a line "N tasks over period …, see git log"; without git — deleted. The memory of the work is in the wiki/git, not in STATE.
7. **STATE is not canonical.** On conflict with the wiki/code — truth is there. Lint may flag a divergence, it doesn't fix it automatically.

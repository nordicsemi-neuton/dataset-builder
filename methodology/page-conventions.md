# Wiki page conventions — frontmatter, types, format

Read before creating a page, editing frontmatter, revising rules.

## Frontmatter

```yaml
---
type: architecture | decision | discovery | synthesis | principles
status: active | superseded | draft   # + domain-specific as needed (open/validated/invalidated, inactive…)
updated: YYYY-MM-DD
sources:                  # mandatory
  - ../../raw/<concern>/2026-05-18-slug.md
  - https://...
supersedes: [adr-0007]    # optional
superseded_by: [adr-0014] # optional
tags: [topic1, topic2]
---
```

**`sources:` is mandatory.** A claim without a source is a hallucination dressed up as a fact; lint does not let pages without sources through.

## Atomicity

One concept per page. Soft limit 400 lines, hard 800. Past 400 — split into subpages and link them. Any single read stays within the context window.

## Cross-references

Markdown links with relative paths: `[Title](../type/slug.md)` for wiki, `[Description](../../raw/.../file.md)` for raw, `[Title](https://...)` for URLs. Anchor text is mandatory and human-readable.

## Journal pages

A page that accumulates observations: each entry starts with `## [YYYY-MM-DD] Heading` — so it's clear what's fresh.

## File name prefixes

Inside a flat type folder, pages are grouped by a **name prefix** — the leading token of the file (`<prefix>-<slug>.md`). The prefix replaces subfolders (depth = 1) and serves as a filter key: visible in `index.md` links and via `ls <type>/<prefix>-*`. This way a query finds a slice without reading the whole wiki.

## Page types — format

### decisions/ — ADR (universal)

```
# ADR-0012 — <decision in one phrase>

Status: active
Date: 2026-05-18
Context: <problem and constraints>
Decision: <what was decided>
Consequences: <what gets easier, what gets harder>
Alternatives considered: <briefly, with the reason for rejection>
Sources: <quotes/links>
```
Decisions are marked `superseded`, not deleted. The flow leading up to an ADR — [spec-lifecycle.md](spec-lifecycle.md).

### synthesis/ — written-back answers

Comparisons, retrospectives, cross-cutting analyses, briefings. Mandatory: an introduction (what the question is) and links to the sources/pages it's built on. Synthesis is rewritten (edit the existing one, don't breed a new one).

### principles/ — rules from the work

A rule "always X / never Y" from an incident → a page by applicability (`process.md`, `domain.md`, …). Entry format: `## P-XX — name`, **Rule / Why / When to apply / Precedent / Source**. Without a source the principle isn't recorded. Read before a non-trivial task (the "think" phase).

### discovery/ — knowledge about the outside world

A segment, competitor, fact, regulation, insight. Grouped by prefixes. Hypotheses have a status `open`/`validated`/`invalidated`.

### architecture/ — central type (modules, contracts, invariants)

One page = a module / service / contract / multi-step workflow of the tool — or a **platform rule/constraint as a contract on the data** (what the platform requires of the input: columns, units, sampling rate, size, file format). Mandatory:

- a `## Implementation` section — where this is in the code;
- a YAML `implementation:` field — path(s) to the code in `src/` (or to a runtime file in `data/`). Lint checks that the path exists (code-drift), without semantic assessment. For platform-rule pages that don't yet have code, `implementation:` points to the source in `raw/platform-docs/`.

Name prefixes by subsystem, e.g.: `ingest-` (CSV intake), `validate-` (checking against the platform's rules), `preprocess-` (transformations), `export-` (export format), `platform-` (platform requirements/constraints from the documentation).

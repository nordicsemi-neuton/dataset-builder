# Format of `index.md` and `log.md`

## index.md

Grouped by type (`architecture`, `decisions`, `discovery`, `synthesis`, `principles`), alphabetical within a type. Each line:

```
- [Page title](<type>/<slug>.md) — one-line summary. _Updated: YYYY-MM-DD_
```

The link is **relative to `index.md` itself** (which sits in `wiki/`): no `wiki/` prefix needed. Same for links between pages: the path is relative to the current page (from `wiki/decisions/foo.md` to `wiki/discovery/bar.md` it's `../discovery/bar.md`).

## log.md

Append only, new entries at the bottom. Prefix `## [YYYY-MM-DD] <op> | <subject>` — for grep (`grep "^## \[" wiki/log.md | tail -20`).

The entry date is the environment date at the moment of writing, not the file mtime and not the date the work itself was done. Append-only mode implies an invariant: the date of each new entry ≥ the date of the previous one. A fresh entry with an earlier date almost always means the date was taken from mtime — a violation that lint catches.

Operations in the log:
- `ingest | <source>` — after each ingest, with a list of cascade-updated pages.
- `lint | found N issues, fixed M` — after each lint.
- `bootstrap | initialization` — once, when the structure is first set up.

# Maintenance (lint) — wiki health check

Triggered by phrases like: "run maintenance", "do a maintenance pass", as well as "run lint", "check the wiki", "check integrity". The freshness trigger for when to offer a run yourself is in CLAUDE.md, §5 "Discipline".

A periodic check. Two levels with different degrees of authority.

## Auto-fix (deterministic — Claude fixes it itself)

- Pages missing from `wiki/index.md` → add with a `(no summary)` stub.
- Index entries for deleted files → mark `[MISSING]` (don't delete).
- Broken internal links with a single same-named file elsewhere → fix the path.
- Links in `sources:` to moved raw files with a single candidate → fix.
- Missing mutual links between obviously related pages → add.

## Report-only (heuristic — requires human judgment)

- Orphan pages with no incoming links.
- Concepts mentioned on several pages but with no page of their own.
- Stale claims contradicting a newer source.
- ADRs with status `active` contradicting a newer ADR.
- Pages over 800 lines.
- Pages without a `sources:` field.
- **Depth violation:** any `.md` in `wiki/<type>/<subdir>/...` (pages must be flat in the type folder). Exception — `wiki/index.md` and `wiki/log.md`.
- **Log not in ascending date order:** in `wiki/log.md`, an entry date earlier than the previous one → report it (the date was probably taken from the file's mtime or the work date, not from the environment). Don't sort automatically — whether to fix the date stamp or the entry position is the human's call.

**Domain checks for the central type.** Code drift in `architecture/`: pages with `type: architecture` lacking an `implementation:` field or with a broken path in it (code renamed/deleted — the page points into the void). The presence of the path is checked, not the semantics.

## Platform-contract drift check (does our knowledge of Nordic's docs still hold?)

The wiki's `architecture/platform-*` and `discovery/platform-*` pages are compiled from a **dated snapshot** of the Nordic Edge AI Lab documentation in `raw/platform-docs/` (each file stamps its `> - Source URL:` and capture date). The platform's rules are law for the data we produce — if Nordic changes the upload contract, data prepared against the old snapshot can start being **rejected or silently dropped**. This check asks one question: **has the documentation changed since our snapshot?**

This is the check that keeps a *downloaded copy of this tool* trustworthy over time — it is the platform-facing analogue of a software dependency update. Run it on every lint.

**This block is best-effort, not unconditional** — it depends on a live read of an external site. When the docs are unreachable, say so and skip; never invent a verdict.

1. **Build the URL manifest.** Read the `> - Source URL:` header from every file in `raw/platform-docs/`. That set of pages is what our platform knowledge rests on. (The pages are a Cloudflare-protected Zoomin SPA whose bodies load per-section by `contentId`; the raw files retain those `contentId`s in their provenance segments — fetch the same content so you compare like with like.)
2. **Re-fetch each page by a live read.** Use `WebFetch` (a live GET that goes around the local sandbox, so it works where `curl` is blocked). Don't use `WebSearch` — its index is days stale, which is exactly the kind of skew that hides a fresh change.
3. **Diff against the snapshot and classify.** Compare each fetched body to its dated `raw/platform-docs/` copy. Report, per page: **unchanged / changed (which sections) / unreachable.** A wording change that doesn't move a rule is `[cosmetic]`; a change to a number, an allowed value, a constraint, a field, or a required format is `[contract]` — those are the ones that can break a user's prepared data.
4. **On a real change — re-ingest, don't hand-patch.** A `[contract]` change means the snapshot is stale:
   - `raw/` is **append-only** — never overwrite the old snapshot. Add the fresh capture as a **new dated file** in `raw/platform-docs/` (`YYYY-MM-DD-<slug>.md`, same header format).
   - Re-ingest so the change cascades to every `wiki/.../platform-*` page that cited it — follow [ingest.md](ingest.md). Update those pages' `sources:` and dates; supersede, don't silently overwrite, any claim that changed.
   - A `[cosmetic]` change needs no wiki edit — note it and move on.
5. **Report to the human in plain language.** For each changed page the human should understand three things, with no jargon (`contentId`, `[contract]`, "cascade", "ingest", "snapshot"):
   - **What changed** — in terms of the data contract: "the platform now accepts X", "Y is no longer allowed", "the window range moved from … to …".
   - **Does it affect them** — does data they've already prepared still pass, or do they need to re-run preparation?
   - **What I'll do** — refresh our knowledge of that rule, on confirmation.

   Without a live read this check is **NOT done** — say "couldn't reach the platform docs to compare", do not output a "no changes" verdict, and do not log a clean result.

After lint — append to `wiki/log.md`:
```
## [YYYY-MM-DD] lint | found N issues, fixed M | platform-docs drift: <none | pages X, Y changed | not checked>
```

# Ingest — adding new knowledge

Triggered by phrases like: "process this document", "remember this", "capture this", "add to the wiki".

When a human tosses files into `input/` (drop zone for incoming material), points at a source, or puts a file into `raw/`:

1. **Read the source.** A long one (multi-page material, a long transcript) — read it in parts, don't skim. First discuss the key takeaways and confirm intent before changing the wiki.
2. **Recognize the input and place it — sorting is Claude's job, not the human's.** Before sorting, recognize: is this **working source code** (a code tree, a deployable site, scripts, a project with a build/manifest) or **ordinary material** (a document, a transcript, data, someone else's example code to study)?
   - **Working code** — do NOT bury it in `raw/`. Ask the human in plain words: "is this code you'll maintain and develop here, or someone else's example to study?". If we **maintain / change / deploy** it → the code lives in a **root folder named by its essence** (`landing/`, `src/`, `scripts/`), created by the human's decision; **not** `raw/` and **not** `output/`. The files on disk are the source of truth; only knowledge about it goes into the wiki (what it is, key facts — offer, prices, operations), not the code itself. For this project the home of production code is `src/`; the code layout and work cycle are run by [spec-lifecycle.md](spec-lifecycle.md). If the human says "this is an example to study" — proceed as with ordinary material.
   - **Ordinary material** — move the source from `input/` (or the one pointed at) into a suitable `raw/` subfolder `raw/<concern>/YYYY-MM-DD-slug.md`; no suitable one — set up a new one and write it into the `CLAUDE.md` tree (the "Structure grows as needed" rule). The human doesn't need to know the `raw/` subfolders — they toss things into `input/`. Preserve the original. **Remove secrets** (passwords, keys, excess personal data). Add a metadata header: source (URL, if any), date received, publication/document date (if known), authors. After placement `input/` empties out (files are moved into `raw/`).
3. **Compile into the wiki.** The unit of knowledge is a **page**. For each affected unit:
   - **Same claim** → merge, add the source to `sources:`, update surgically.
   - **New concept** → a new page in the suitable type folder, named after the concept (not after the file name). For types with prefix grouping — use the prefix. Type choice and format — [page-conventions.md](page-conventions.md).
   - **Contradiction** → annotate the conflict in the text, lay out both sides, raise it for the human to resolve. Don't choose silently.
4. **Cascade.** Scan the same type folder and the index for materially affected pages. Update them, refresh `updated:`.
5. **Update `wiki/index.md`** — entries for the affected pages. Format — [index-log-format.md](index-log-format.md).
6. **Append to `wiki/log.md`:**
   ```
   ## [YYYY-MM-DD] ingest | <title of the main page>
   - Updated: <cascade-updated page>
   ```
7. **Commit — if the project is under git.** One commit, message `ingest: <source>`. Without git the step is skipped (history lives in `log.md` and page dates).

Important rule: **when updating any claim — re-read the raw source it references.** Don't treat the wiki text as the primary source — that's how drift sets in.

**Large source** (an hour+ interview, a detailed report): don't extract everything in one pass — 3–5 key points per ingest, mark the rest right in the raw file ("min. 45:00: about X — to review") and come back later.

## Closing a research milestone: synthesis pass

The ingest above is **per-item**: one source → pages. But the research layer also has a **milestone close** (a batch of interviews done, a competitor breakdown finished, market research completed) — symmetric to the close of a task-spec/sprint in [spec-lifecycle.md](spec-lifecycle.md). At this step knowledge isn't appended one source at a time, but **brought together across sources**:

1. **All milestone sources are ingested** — each interview / survey / competitor page has gone through the per-item ingest above.
2. **Synthesis pass across sources.** Update hypothesis statuses based on the accumulated evidence (`open → validated | invalidated`, with links to the supporting sources). Pull the findings into a `synthesis/` page — a milestone retrospective: what was confirmed, what was refuted, what's new about segments / JTBD / competitors, which hypotheses opened up.
3. **STATE.** The research milestone moves to "Completed this past week"; "Path to goal" marks it closed.

Like any non-trivial wiki mutation — Claude **proposes** specific pages and status updates, a human confirms. Without the synthesis pass, research stays a scatter of ingest pages with no cross-cutting conclusion.

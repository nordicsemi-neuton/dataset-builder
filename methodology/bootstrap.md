# Bootstrap — initialization for a specific project

Triggered on the first ingest into a project with no structure, or on request ("initialize the structure", "set up the wiki"). **Never** from `query`/`lint`. Once; again — only recovery.

Bootstrap is not stamping out fixed folders, but a **short setup for the project**. The template already contains `CLAUDE.md`, `STATE.md`, `methodology/`; bootstrap builds out the working layers.

## Step 1 — short interview (3–5 questions, wait for answers)

- What is the product and for whom; current stage?
- What sources will be coming in (platform documentation, sample CSVs, decision notes, technical documentation)?
- Is there already code (`src/`) or runtime data (`data/`)?
- Domain conventions, if not the defaults (sensor units/format — the "Documents and naming" section in [CLAUDE.md](../CLAUDE.md)).

**No need to ask about code** — working with code is already wired in (task flow). The home of production code is `src/`, task working documents are in `specs/`; the code work cycle is run by [spec-lifecycle.md](spec-lifecycle.md).

## Step 2 — propose a structure

Based on the answers, Claude **proposes** a layout (does not create it silently): `platform-docs/` (platform documentation), `samples/` (sample sensor CSVs); as sources appear — `discovery/`, `technical/`. No `misc/`. Special folders — if they came up. A human confirms/edits.

## Step 3 — create (what's missing, without overwriting what exists)

- `input/.gitkeep` — drop zone for incoming material (a human tosses any material here; Claude sorts it into `raw/` on ingest, the human doesn't need to know the subfolders).
- `raw/.gitkeep` + the agreed subfolders.
- `wiki/` + the class's type folders (`decisions/`, `discovery/`, `synthesis/`, `principles/`, `architecture/` — each with a `.gitkeep`); `wiki/index.md` (`# Wiki Index`); `wiki/log.md` (`# Wiki Log` + `## [YYYY-MM-DD] bootstrap | initialization`).
- `output/.gitkeep` — **the root of working files, present for all classes**; created empty, subfolders (`drafts/`, folders for live documents) appear as they actually occur, not in advance.
- `specs/.gitkeep` — task working documents (flat, status in frontmatter). `src/` / `data/` / `scripts/` are **not** created empty — they appear by the human's decision, when needed (see "What is NOT created").

## Step 4 — fill in the accompanying files

- "About the project" in `CLAUDE.md` from the interview answers. After filling it in, **delete the instructional footnote** — the `>` block under the "About the project" heading (it's for the author, not for the project).
- **The "Architecture" tree in `CLAUDE.md`** — write in the created `raw/` subfolders (they aren't in the template).
- The starting section of `STATE.md` (profile/stage); `_Updated:_` = today.

## What is NOT created at bootstrap

- **`src/` / `data/` / `scripts/`** — not created empty; they appear when code, runtime data, or a script arrives/is written, by the human's decision (`specs/` is created empty — it's the task index).
- Folders beyond the minimum, **including working-layer subfolders** (`drafts/`), appear as the need arises (the "Structure grows as needed" rule in [CLAUDE.md](../CLAUDE.md)).

After bootstrap — if under git — commit `bootstrap: structure initialization`; without git it is skipped.

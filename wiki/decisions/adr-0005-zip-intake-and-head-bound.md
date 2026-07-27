---
type: decision
status: active
updated: 2026-07-25
sources:
  - ../../specs/databuilder-013-intake-robustness.md
  - ./adr-0002-data-builder-engine-architecture.md
  - ../architecture/platform-dataset-requirements.md
tags: [decision, data-builder, intake, csv_io, zip, validation, engine]
---

# ADR-0005 — `.zip` intake through one shared member helper; a raised, line-aligned head bound

Status: active
Date: 25.07.2026

Amends the intake half of [ADR-0002](adr-0002-data-builder-engine-architecture.md) (`check_raw_file`
"inspects the raw bytes"). Extracted from spec `databuilder-013` (sprint task B3).

## Context

Two intake defects reproduced against real customer files:

1. **64 KB head truncation.** `csv_io.sniff_raw` decoded only `data[:65536]` and field-counted the
   first 50 rows. On a wide file (~5 KB/row at 513 columns) that window ends mid-row around row 12,
   and the trailing partial line was inspected as a ragged row → a false `field_count_mismatch`
   HARD_REJECT on a valid file.
2. **`.zip` blindness.** The platform accepts `.csv` **or `.zip`**
   ([dataset requirements](../architecture/platform-dataset-requirements.md)), but `sniff_raw`
   scanned the archive's compressed bytes (→ `encoding_not_supported` on every zip), the inner file
   name was never checked, and a corrupt/encrypted/misnamed `.zip` crashed with an uncaught traceback
   (exit 1) on every entry point.

## Decision

**Head bound.** Raise the field-count decode window from 64 KB to **1 MiB, line-aligned** (drop a
trailing partial row). The check always intended to sample 50 rows; 1 MiB covers 50 rows of a
~1800-column file and is always ≥ the old 64 KB, so the sample only ever **grows** versus today — it
cannot open a silent PASS a whole-file check would then have to close. Single-pass (one slice, one
`rfind`, one decode), cost bounded by the window, not the file.

**`.zip` container.** Resolve the archive to its single data member through **one helper**
(`_zip_member`) shared by both readers (`sniff_raw` and `read_table`), so the byte layer and the
dataframe layer can never describe different files. Specifics:

- **Detect by extension, not signature** — `read_table` (pandas) keys off the extension, so a
  signature rule would desynchronise the two layers.
- **The helper returns bytes, with the read inside its guard** — an encrypted member (`RuntimeError`)
  or a content-corrupt member (`zlib.error`) raises at read time, not at open; a helper returning a
  live handle leaves the crash in the caller.
- **`OSError` is excluded from the caught set** — `FileNotFoundError`/`PermissionError` are
  `OSError`; swallowing them would report "corrupt archive" (exit 2) for a missing file that must
  stay an IO error (exit 4), the discriminator the shipped skills read.
- **Member selection** ignores `__MACOSX/`, directory and duplicate entries; a `.csv` among extras is
  used with a `zip_extra_members` INFO; a 256 MiB pre-open size bound (`zip_member_too_large`) keeps
  `sniff_raw` from materialising an unbounded decompressed member.
- **The inner file name** is checked against the platform's file-name rule (`zip_inner_file_name`),
  **`[needs clarification]`** — the docs are silent on whether the platform reads a name inside an
  archive, so it ships at FIX_REQUIRED with a hedged message, not HARD_REJECT.

**`prep` guards.** `zip_inner_file_name` is suppressed for `prep` (it emits a correctly named output);
a **non-overridable pre-flight guard** (`output_overwrites_input`/`output_not_csv`, via
`os.path.samefile` over any input) stops `prep x.zip --out x.zip` — and symlink/hardlink aliases, and
`--out *.zip` — from destroying the user's file, including through `--write-anyway`.

## Alternatives rejected

- **Line-align at 64 KB** (the first attempt) — shrank the wide-file sample to ~12 rows, opening a
  silent PASS that pulled in a whole-file field-count check, `csv.reader` head parsing and a `prep`
  tightening on the *default* population. Turned a loosening into a tightening. Replaced by raising
  the bound. See [process P-22](../principles/process.md).
- **Signature-based zip detection** — certified a clean CSV for a file pandas never parsed (the two
  layers disagreeing); the reason detection is by extension.
- **A decompression size bound checked after the read** (revisions 1–2) — bounded nothing; the member
  was already decompressed. Moved before `zf.open`, checked against the declared size and re-checked
  on a capped read.

## Consequences

- Nine new intake finding codes (`zip_unreadable`, `zip_empty`, `zip_member_empty`,
  `zip_multiple_files`, `zip_member_too_large`, `zip_inner_file_name`, `zip_extra_members`,
  `output_overwrites_input`, `output_not_csv`). Codes are a skill-facing seam (ADR-0002); no skill
  switches on a code today.
- Verdict changes both directions (measured `7c48e79`→`65cd4e7`, 40/197 matrix cases): wide files and
  clean zips stop being falsely rejected (loosening); illegal inner names, multi-member and oversize
  archives, and `.zip`-output paths are now caught (tightening). Full table in the frozen spec; user
  copy in `CHANGELOG.md`.
- **Carried, not fixed here:** the same crash-→-silent-drop shape survives on `quality-report`
  (`cli.py:111`) and `validate --holdout` (`validate.py:325`), which discard intake findings — the
  B9 pattern on a third and fourth surface, both in `validate.py`/`cli.py` (outside B3's scope).
- `csv_io.py` grew enough that sprint task B4's line pins were re-expressed by function name.

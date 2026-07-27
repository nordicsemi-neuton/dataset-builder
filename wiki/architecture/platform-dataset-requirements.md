---
type: architecture
status: active
updated: 2026-07-25
implementation:
  - ../../src/data_builder/validate.py
  - ../../src/data_builder/csv_io.py
  - ../../src/data_builder/normalize.py
  - ../../raw/platform-docs/2026-06-25-pipeline-dataset-requirements.md
sources:
  - ../../raw/platform-docs/2026-06-25-pipeline-dataset-requirements.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-uploading-and-setup.md
  - ../../raw/platform-docs/2026-06-25-get-started-1-collection-labeling.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
tags: [platform, csv, dataset, requirements, contract, encoding, validation]
---

# platform — Dataset requirements (the input CSV contract)

**This is the hard output contract our data-builder must produce and validate against.** The platform refuses or mis-trains on data that violates these rules ("the platform's rules are law"). Every rule below is from Nordic Edge AI Lab documentation; numbers are verbatim. Where the docs are silent, it is marked `[not stated]` — do not invent a default.

Related: [signal-processing windowing contract](platform-signal-processing.md) · [preprocessing options](platform-preprocessing-options.md) · [feature extraction](platform-feature-extraction.md) · [pipeline & upload](platform-data-pipeline.md) · [deployment/inference CSV contract](platform-deployment-inference.md).

## File-level requirements

| Aspect | Rule |
|---|---|
| Format | **CSV** (single file). Upload accepts `.csv` **or `.zip`**. |
| Encoding | **UTF-8 or ISO-8859-1** only. Other encodings must be converted (e.g. Notepad++ → Encoding → Convert to UTF-8). |
| File name | Must **not** contain these special characters: `` !/[+!@#$%^&*,. ?":{}\/\|<>()[]] `` (verbatim from docs; the set includes space and dot; the `\|` is a literal pipe). |
| Separator | One of **comma `,` , semicolon `;` , pipe `\|` , caret `^` , or tab**. (Docs say "comma, semicolon, pipe, care, or tab" — "care" is a typo for **caret**.) |
| Line endings | **CRLF or LF**, used **consistently** across the file. |
| Header | **First row = column names** (required). |
| One model per dataset | **Only one dataset trains one model.** Data spread across multiple files must be **combined before upload** (see [combining files](#combining-multiple-recordings)). |

## Column / header rules

- All column names (header values) must be **unique**.
- Column names may contain **only** letters `a–z A–Z`, digits `0–9`, hyphen `-`, underscore `_`.
- **Field/column order must be identical** between training and inference/holdout data. "When transferring data for inference on the device, the values must always be in the same order as in the training dataset."
- Irrelevant columns can be excluded at upload time via the **Remove variables** section (the model ignores them in training and validation).

## Value rules

- **All feature values must be numeric.**
- **No empty values**, and no strings that *represent* empty (`NA`, `NAN`, etc.). The data-builder must reject/repair these, not pass them through.
- **EN-US numeric locale only:**
  - Decimal separator is a **dot** `.`; remove thousands separators. `20,000.00` → `20000.00`.
  - If a value combines a number with a unit, keep **only the number**. `$20,000.00` → `20000.00`.
  - End-of-line symbols must be **excluded from field values**.
- **Numeric storage types accepted: INT8, INT16, FLOAT32.** The chosen input data type must match the data (see [preprocessing options](platform-preprocessing-options.md) for INT8 ∈ [-128,127], INT16 ∈ [-32768,32767], FLOAT32 if any value is float). Datatype at inference must match the training datatype.
- **Timestamps / dates** must be **epoch time or relative format**, not calendar strings. `10/18/2017` → `1508284800`. The same timestamp format must be used consistently between training and test data.

> ⚠️ "The number of lines must be excluded from the training dataset." — i.e. **do not add a row-index/line-number column.** (Verbatim wording is ambiguous; treat as "no index column," and re-verify against the source if a row-count meaning is suspected: [raw](../../raw/platform-docs/2026-06-25-pipeline-dataset-requirements.md).)

## Classification target rules

- Target/label values for **classification must start at `0`** and be encoded **contiguously** (e.g. `swipe=0, rotate=1, tap=2`). Save the encoding dictionary.
- A classification training set needs a **minimum of 2 classes**, with **at least 20 samples per class**.
- The target column is designated at upload as the **Target Column** (it is one of the CSV columns, e.g. `class`).
- **Units are not dictated by the platform** — features only need to be numeric. (Domain note: the gesture demo records accelerometer `acc_z ≈ 9.7–9.8`, consistent with m/s²; record the actual unit + sampling rate per dataset.)

## Inertial-sensor (Signal-Processing) row layout

For sensor data (gyroscope, accelerometer, magnetometer, EMG, …) used with **Signal Processing**:

- **Each row = device readings for one unit of time, plus a label column as the target.** One row per sample, time-ordered.
- **Do not shuffle signal labels and do not encode/transform the signal** before upload — the platform windows the raw time series itself.
- The documented example column layout (gesture demo): `acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, class` (6 sensor axes + target). Column **names are author-chosen** but must obey the header rules above; this naming is a convention, not a platform-enforced schema.
- The window size (e.g. 8, or 99 at 100 Hz) governs how many consecutive rows the platform groups into one feature-extraction window — see [signal-processing contract](platform-signal-processing.md). Rows are *not* pre-grouped in the CSV; the platform groups them.

> ### `[needs clarification]` — does "≥20 samples per class" count rows or windows?
>
> **Unresolved, and the captured docs cannot settle it — they use "sample" in both senses.**
>
> | reading | evidence |
> |---|---|
> | **sample = row** | `pipeline-signal-processing-windowing.md` throughout: *"Window size … specifies how many samples"*, *"Window size minimum is 10 samples"*, *"each sub-window must contain at least 10 samples"*, *"consecutive windows share overlapping samples"* |
> | **sample = one window's output** | `get-started-2-cleaning-combining-preprocessing.md:90`: *"for each set of 99 **records** per axis …, Neuton will extract features and represent the data as a **single training sample (1 row)**"*; also `:92`, `:119` (*"96 features per sample"*), `:137` |
>
> The rule itself (`pipeline-dataset-requirements.md:38`) says only "20 samples" and does not disambiguate.
>
> **What the tool does today:** `MIN_SAMPLES_PER_CLASS` in [`validate.py`](../../src/data_builder/validate.py) counts **rows**. **Treat that as unverified, not as confirmed correct.** The risk is asymmetric: if the platform means windows, we pass files it will reject — the same class of failure as a gate that lies.
>
> **The strongest argument for rows — an inference, not a source.** This rule is enforced by the platform **at upload**, and Signal Processing is pipeline **step 5**: at upload time the platform does not yet know the window size, and if [SP is left off](platform-signal-processing-applicability.md) there will never be a window at all. A check that must fire at upload can only count rows. That is a good argument and still not a citation — record it as reasoning, don't promote it to a rule ([process P-18](../principles/process.md)).
>
> **The counter-argument is not weak either.** On the "sample = training example" reading, a class with 20 rows at a window of 100 yields *zero* training examples, so a row-count minimum under-enforces by roughly the window size — which is a real failure in the dangerous direction.
>
> **How to resolve it (cheap, empirical):** upload a dataset with ~25 rows per class and a window of 100. Accepted ⇒ rows. Rejected for insufficient samples ⇒ windows. Until then this stays `[needs clarification]` and **no code change is made in either direction**.
>
> *History: an internal reading first asserted "windows" from our own paraphrase; the correction then asserted "rows" and claimed the docs were consistent. Both were unsourced. Caught at the spec gate, 24.07.2026.*

## Test / holdout dataset

- Same rules as training: CSV, UTF-8/ISO-8859-1, header row first, same separator set, CRLF/LF.
- Must have the **same file structure, same feature-value rules, and the same field order** as the training dataset.
- End-of-line symbols excluded from field values.
- If holdout validation is **not** supplied, the platform **auto-splits training data 80% train / 20% validation** (see [pipeline](platform-data-pipeline.md)).

## Session ID (optional, for time-continuous data)

- A **Session ID column** marks a time-continuous process (e.g. one sensor recording / one subject). It separates sessions so windowing does not cross session boundaries.
- **Not mandatory.** If present (e.g. a `session_id` column), select it via the **Session ID** radio button at upload.
- Consequence on windowing: **sessions shorter than the window size are dropped automatically** ([signal-processing](platform-signal-processing.md)).

## Combining multiple recordings

One-dataset-per-model means per-class/per-session recordings must be concatenated first. Documented commands:

- **Windows (PowerShell):** `Get-Content idle.csv, swipe_right.csv, swipe_left.csv | Set-Content dataset.csv`
- **macOS/Linux:** `cat idle.csv swipe_right.csv swipe_left.csv > dataset.csv`

⚠️ Naive concatenation repeats the header row from each file. The docs show this command form but the resulting header-duplication handling is `[not stated]` — the data-builder should concatenate with a **single** header. Re-verify against [raw](../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md).

## Cleaning expectations (pre-upload)

- Exclude **idle/incorrect records** captured while setting up hardware — good practice is to **drop the first and last few seconds** of each recording.
- For non-continuous gestures, **segment** raw data so the gesture peak sits in the middle of the window (Nordic provides a [signal-centering script](https://github.com/nordicsemi-neuton/segment-center-signal)).

## Implementation

Implemented in `src/data_builder/`: format/value/structure validation in [`validate.py`](../../src/data_builder/validate.py) (raw-bytes intake in [`csv_io.py`](../../src/data_builder/csv_io.py), numeric repair in [`normalize.py`](../../src/data_builder/normalize.py)), assembly in `combine.py`/`relabel.py`, export in `pipeline.py`. This page is the spec those modules satisfy; the engine architecture is [ADR-0002](../decisions/adr-0002-data-builder-engine-architecture.md). Scope is gesture classification first (see the spec for deferred task types). Raw docs remain in `sources:` for re-verification.

Since [ADR-0005](../decisions/adr-0005-zip-intake-and-head-bound.md) (25.07.2026) the intake layer also resolves a **`.zip`** upload to its single CSV member before applying the checks above, and checks the member's name against the file-name rule (`zip_inner_file_name`, see the open item below).

## Open items / to re-verify against source

- Exact meaning of "The number of lines must be excluded from the training dataset" (no index column vs. row-count limit).
- Header handling when concatenating files (single vs repeated header).
- Whether a timestamp column is required or optional for Signal-Processing datasets (the demo CSV has **no** explicit time column — time is implicit via fixed sampling rate). `[not stated]` — likely optional given fixed-rate rows.
- Maximum dataset/file size: **not stated** anywhere in the captured docs. (Project assumption elsewhere: training sets usually ≤ ~100 MB — that is *our* assumption, not a platform-stated limit.)
- **Does the platform read the file name *inside* a `.zip`?** The file-name character rule above is stated for *the uploaded file's name*; the docs are silent on an archive member's name. Our intake emits `zip_inner_file_name` at FIX_REQUIRED (a hedged warning, not a HARD_REJECT) pending an answer (ADR-0005, `databuilder-013`). `[needs clarification]` — resolve by uploading a `.zip` whose member has a forbidden character and observing acceptance.
- **Exactly one CSV inside a `.zip`?** The docs say only "`.csv` or `.zip`". Our `zip_multiple_files` is justified by *our* inability to pick a member, not a stated platform rule. `[needs clarification]`.

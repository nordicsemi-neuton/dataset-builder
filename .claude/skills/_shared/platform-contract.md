# Platform input-CSV contract — shared reference for data-builder skills

**What this is.** A plain-language digest of the hard contract a prepared CSV must satisfy for the
**Nordic Edge AI Lab** platform, written so the skills don't each restate it. **It is a cited
pointer, not a source of truth.** Every rule links to its canonical wiki page; on any conflict or
edge case, **re-read the wiki page**, which is authoritative. Do not quote a number from here that
you have not confirmed against the linked page when it matters.

**Epistemic legend** — say which one you're invoking, never blur them:
- 🔒 **PLATFORM LAW** — stated in Nordic's documentation; violating it rejects the upload or
  mis-trains the model. Enforce it.
- 🧪 **EXPERIENTIAL** — learned from field experience ([principles](../../../wiki/principles/domain.md)),
  a strong default but not documented platform law. Recommend it, label it as experience.
- ❓ **UNVERIFIED** — a working assumption flagged in the wiki; present as "verify against the
  platform's Processed Data view", never as a guarantee.

Canonical pages: [dataset requirements](../../../wiki/architecture/platform-dataset-requirements.md) ·
[signal processing](../../../wiki/architecture/platform-signal-processing.md) ·
[preprocessing options](../../../wiki/architecture/platform-preprocessing-options.md) ·
[feature extraction](../../../wiki/architecture/platform-feature-extraction.md) ·
[deployment/inference](../../../wiki/architecture/platform-deployment-inference.md) ·
[data pipeline](../../../wiki/architecture/platform-data-pipeline.md).

---

## Group A — HARD-REJECT (the platform refuses or mis-reads the file) 🔒

Source: [dataset requirements](../../../wiki/architecture/platform-dataset-requirements.md) unless noted.

- **One CSV per model.** One dataset trains one model; combine multiple recordings into a single
  file **with a single header row** first. Upload accepts `.csv` or `.zip`.
- **Encoding** UTF-8 or ISO-8859-1 only. Convert anything else.
- **Separator** is one of comma `,`, semicolon `;`, pipe `|`, caret `^`, or tab — one consistently.
- **Line endings** CRLF or LF, used consistently.
- **Header row first**, with column names.
- **Column names** unique and drawn only from `A-Za-z0-9_-`.
- **File name** must not contain the platform's forbidden character set (space, dot, and the
  punctuation listed on the page).
- **All values numeric.** No empty cells, no `NA`/`NAN`/empty-string stand-ins.
- **EN-US numeric locale:** decimal point `.`; strip thousands separators (`20,000.00` → `20000.00`);
  keep only the number if a unit is attached (`$20,000.00` → `20000.00`).
- **Timestamps** as epoch/relative numbers, never calendar strings (`10/18/2017` → `1508284800`);
  same format across train and test.
- **No row-index/line-number column** ("the number of lines must be excluded"). ❓ exact wording
  flagged on the page — treat as "no index column".
- **Storage type** one of INT8 / INT16 / FLOAT32 for the whole dataset; inference type must match
  training type. (Axon/LiteRT ⇒ FLOAT32 only — [preprocessing options](../../../wiki/architecture/platform-preprocessing-options.md).)
- **Classification target** starts at `0`, contiguous encoding; **≥2 classes, ≥20 samples each**.
- **Holdout** (if supplied) must have the **same structure and field order** as training; otherwise
  the platform auto-splits 80/20.
- **Signal-Processing row layout:** one row = all sensor-axis readings at one time + the label
  column; rows **time-ordered, never shuffled**, signal **not pre-transformed** (the platform windows
  the raw series itself).

## Group B — SILENT-LOSS (accepted, but data quietly disappears) 🧪 / ❓

Source: [signal processing](../../../wiki/architecture/platform-signal-processing.md), [domain principles](../../../wiki/principles/domain.md).

- 🧪❓ **A class whose longest contiguous run < window size produces zero windows and silently
  vanishes** ("data removed" / "label has no data"). The strict "mixed-label windows are dropped"
  model is an ❓ upper bound — present per-label survival counts and tell the user to **verify
  against the platform's Processed Data view**. Diagnose with `window_survival_sim.py`. [domain P-01]
- 🔒 **Sessions shorter than the window are dropped automatically** when a Session ID column is used.
- 🔒 **Single sampling rate** is mandatory (window size is in samples); resample mixed rates first.
- 🔒 **Frequency-domain features** ⇒ window must be power-of-2 in **128–2048**; the minimum contiguous
  run per class therefore escalates to **128**.

## Group C — BAD-MODEL (accepted and kept, but the model suffers) 🧪

Sources: [preprocessing options](../../../wiki/architecture/platform-preprocessing-options.md),
[signal processing](../../../wiki/architecture/platform-signal-processing.md), [domain principles](../../../wiki/principles/domain.md).

- 🧪 **Set the training sliding shift = window size.** Small training shifts over-sample the
  dominant (idle) class → severe imbalance. Overlap is for inference. [domain P-02]
- 🔒/🧪 **Input data type:** pick the widest type present — one float value ⇒ whole dataset FLOAT32;
  else INT16 if any value exceeds ±127, else INT8. Recommend from observed ranges; wrong type costs
  footprint/accuracy.
- 🧪 **Class imbalance** ⇒ recommend Balanced Accuracy / weighted F1 over plain Accuracy **for reading
  results, not as a training fix** — the platform's optimizer always minimizes cross-entropy regardless
  of the selected metric, so a metric change makes an existing small-class result visible, it does not
  make the next training run try harder on that class. Report per-class counts so the user can choose.
  [domain P-13]
- 🧪 **Directional / multi-orientation classes** (left vs right, up vs down) need the signed-asymmetry
  features **LR_SLOPE / LR_INTERCEPT** enabled, or they conflate/die. [domain P-06] —
  [feature extraction](../../../wiki/architecture/platform-feature-extraction.md).
- 🧪 **Discrete gestures should be centered** (peak mid-window), per class, never across class
  boundaries; idle/unknown stay raw. [domain P-05] **Confirm each class's physical nature (continuous vs
  discrete) with the user before centering — never infer it from filenames/presets.** [domain P-15]

## Group D — DEPLOYMENT / runner CSV (so local validation matches) 🔒

Source: [deployment/inference](../../../wiki/architecture/platform-deployment-inference.md).

- The desktop inference runner defaults: delimiter **comma**, target column **`target`**, session
  column **`session`**. If the label column is named `class`, the user must pass `-t class`.
  → Default the exported target column to `target`, **or** print the exact `-t`/`-sn`/`-d` flags.
- 🧪 **Postprocessing has a hard ceiling:** if a class's max probability ≈ 0 it is dead at the model
  level — no threshold/smoothing recovers it; retrain or drop. Check before promising a fix. [domain P-07]
- 🧪 **Recommended on-device postprocessing default:** EMA (α≈0.3) + unknown-margin suppression
  (~0.2); no threshold / consecutive-N unless a specific failure mode needs it. [domain P-08]

---

## How skills should speak to the user (house style)

- Plain language, no internal jargon (don't say "ingest/ADR/lint/wiki type"). [CLAUDE.md §"In human terms"]
- Reply shape for any diagnosis/validation: **root cause in one sentence (their words) → the numbers
  from their own data → numbered fixes in priority order, each citing the exact rule → secondary
  notes → collaborative tone.** [process P-07](../../../wiki/principles/process.md)
- Reconcile, don't assume: treat the user's stated class map / rate / durations as hypotheses to
  check against the file. [process P-02/P-03](../../../wiki/principles/process.md)
- Propose before writing files; confirm a non-trivial change. [CLAUDE.md Discipline 4]
- Never present an experiential default or an unverified assumption as platform law.

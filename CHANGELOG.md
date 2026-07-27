# Changelog

Behaviour changes that affect what the tool accepts, rejects, or writes. The release script resets
`wiki/log.md` and `STATE.md` on every publish, so this file is the only record a downloaded copy
carries of how its verdicts differ from an earlier download.

## Unreleased

_Nothing yet._

## 0.2.0 — 2026-07-27

### Added — a `signal_processing` profile field, so a tabular dataset is no longer wrongly windowed

The dataset profile now accepts `"signal_processing": true | false` (omit if unknown). It records
whether the platform's Signal Processing (windowing) will be on for this solution:

- **true** (or omitted) — windowed, exactly as before. Nothing changes for any existing profile.
- **false** — tabular: one row is one independent observation and the platform does not window it.
  On `validate`, the window-based checks (window range, sliding shift, window survival, direction
  features, mixed sampling rate) no longer apply and are skipped, so a tabular file is no longer
  rejected by rules that do not fit it. You get an `sp_off_unverified` advisory — the tool has not
  itself confirmed the data is tabular, so it asks you to. If the profile also declares
  `gesture_classes`, that is a contradiction (a gesture is a windowed concept) and is reported as
  `sp_off_contradicts_profile` (FIX_REQUIRED).

Scope when first added: `validate` only. **`prep` and `quality-report` gained tabular support in the
same release — see "`prep` and `quality-report` now understand a tabular profile" below.**

A profile with an invalid `signal_processing` value (a number or string rather than a boolean) is now
a profile error (exit 4) rather than being silently coerced.

### Changed — `prep` and `quality-report` now understand a tabular (Signal-Processing-off) profile

`validate` already knew about `"signal_processing": false` (a tabular dataset the platform does not
window). `prep` and `quality-report` now do too:

- `prep` on a tabular profile no longer centers or resamples the data (both are windowing / continuous-
  signal operations that would silently corrupt independent rows — centering discarded rows, resampling
  invented them, both under a PASS). It writes the tabular file as-is, with the same `sp_off_unverified`
  advisory `validate` gives (the tool has not itself confirmed the data is tabular — you should). If the
  profile also declares gesture classes, or you pass `--resample`, that is a contradiction and `prep`
  refuses (`sp_off_contradicts_profile` / `sp_off_resample_refused`), telling you to fix the profile or
  turn Signal Processing on. Previously a tabular profile with no window made `prep` fail with "no window
  given" — the honest tabular user was simply blocked.
- `quality-report` on a tabular profile no longer crashes; it prints the per-source profile and says the
  source comparison was not run (it compares windowed features, which do not exist for tabular data).
- Passing a window (`--window` or the profile's `window.candidates`) with Signal Processing off now says
  the window was ignored (`sp_off_window_ignored`), instead of ignoring it silently.
- `prep --window 0` (or any window below 1) is now a usage error instead of silently substituting the
  profile's window candidate.

### Fixed — `quality-report` no longer crashes on a missing label column, and stops hiding why a file could not be read

`quality-report` compares each class across your recordings, so it needs the label column named in the
profile. If that column was absent it ended in an unhandled error (exit 1) instead of telling you. It now
reports the missing column the same way `validate` and `prep` do, and exits 2. (Anomaly-detection data is
unlabelled by design, so there it simply reports per-source row counts.)

It also used to discard the reason a file could not be read: an unreadable, misnamed or password-protected
`.zip`, or a multi-file archive, produced only "no readable input files" (exit 4). It now surfaces the
specific problem (`zip_unreadable`, `zip_multiple_files`, an unrepairable value, …) and exits 2, matching
`validate`/`prep`. A file it can read still reports as before (exit 0), and its `--json` output keeps every
key it had (with `verdict`/`findings` added). `validate --holdout` likewise now tells you when the *holdout*
file has a format problem (an illegal name inside a `.zip`, mixed line endings) instead of silently ignoring
it.

### Fixed — a wide file is no longer rejected for a problem it does not have

We checked field counts on only the first 64 KB of a file and cut that window mid-row, so a file with
many columns (roughly 500 or more) was rejected with a message about a stray delimiter or a
comma-decimal that was not there. We now read enough of the file to check the first 50 rows in full. A
valid 513-column recording passes. Your file has not changed — only what we said about it. (A file
whose header itself was longer than 64 KB could hide a ragged row entirely; that is now reported too.)

### Fixed — a `.zip` is read as an archive instead of as binary noise

The platform accepts a `.csv` or a `.zip`. We scanned the archive's compressed bytes, so every `.zip`
came back as "not UTF-8 or ISO-8859-1", usually with one or two further invented format complaints,
and `prep` refused to write. We now look inside and judge the CSV that is in there: encoding, line
endings and delimiter describe your data. `prep` accepts a `.zip` and writes byte-for-byte the same
output as the same CSV unzipped. Archives made by Finder (which add a `__MACOSX` folder) and by
`zip -r` (which store the folder itself) now work — they used to fail with a message about
comma-decimals.

### Fixed — a damaged, password-protected or misnamed `.zip` no longer crashes

`validate` and `prep` ended with an unhandled error on a corrupt archive, on an archive whose contents
are encrypted, and on a plain CSV simply renamed `.zip`. They now report `zip_unreadable` and exit 2.
A missing or unreadable file still exits 4 with an IO error, as before. (`quality-report` no longer
crashes on these either, but still reports only "no readable input files" — being fixed separately.)

### Changed — new checks on what is inside an archive

`zip_multiple_files` — we cannot tell which file you meant, so put a single CSV in the `.zip`.
`zip_empty` / `zip_member_empty` — nothing usable inside, or the file inside is empty.
`zip_member_too_large` — the file inside is over 256 MB; unzip it and validate the CSV directly.
`zip_extra_members` — a note, not a problem: more than one file was in there and we used the single
`.csv`; the note names what we ignored. `zip_inner_file_name` — the file *inside* the archive has
characters the platform forbids in a file name. **We cannot tell from the docs whether the platform
reads that inner name**; renaming is cheap and a wrong name is plausibly fatal at upload, so we report
it and say exactly that.

**This is a tightening** for the first four: an archive that reached a verdict before can now be
rejected.

### Changed — `prep` protects your input file

`prep archive.zip --out archive.zip` would have replaced your only copy of the archive with a CSV —
including through `--write-anyway`, and including when `--out` was a shortcut (symlink or hardlink) to
it. Refused now, and the same protection now covers `prep data.csv --out data.csv`. `--out
something.zip` produced a CSV under a `.zip` name that our own reader then rejects as a broken archive;
refused too. `prep` no longer refuses over the *name of the file inside* your archive — it reports it
and carries on, the way it already handles line-ending problems.
### Changed — `prep` now reports what centering discarded

When `prep` centers gesture data it keeps one window per detected gesture and drops everything in
between, so the row count can fall a long way — on sparse recordings, legitimately by most of the
file. `prep` used to say nothing about this: a dataset could shrink by 80% with a PASS verdict and no
note. It now reports, for every centered run, the rows in, the rows out, and how many gesture events
were found per class, so a large drop is visible and explained rather than silent.

Nothing is accepted, rejected, or written differently — this is a reporting change only. The report
gains one line (so later items renumber), and `--json` output gains one finding
(`centering_rows_discarded`) whose data carries the per-class breakdown.
### Fixed / Added — diagnostic scripts (`scripts/diagnostics/`)

These are the read-only diagnostics the skills drive; they do not change what `prep`/`validate`
accept, reject, or write, but their output is user-visible.

- **`check_signal_centered.py` now accepts `--sensor-cols`.** Before, it only recognised the six IMU
  column names and stopped on anything else, so EMG / magnetometer / vibration data (all in platform
  scope) could not be checked without renaming columns. Name the columns explicitly with
  `--sensor-cols`. Named columns must be numeric and finite; a text, boolean, or non-finite column is
  now refused with a clear message instead of a crash or a silently degenerate verdict. Default
  (no-flag) behaviour on IMU data is unchanged.
- **`window_survival_sim.py` no longer crashes on non-integer labels.** Before, it printed the
  totals and then raised on the per-label breakdown for any string label (and on blank or non-finite
  labels), losing the per-label numbers that are the tool's whole point. String labels now print as
  themselves; integer labels are unchanged; rows with a missing / non-finite label are reported on
  their own line rather than crashing or appearing as a phantom class.
- **`feature_separability.py` can now recommend every feature family.** Before, five features across
  three families (Crossing rate, Signal variation, Autocorrelation) could rank top of the measured
  evidence yet never appear in the recommended enable-set. They are now recommended when a class's
  strongest discriminator lives there. Recommendations for data that does not need these families are
  unchanged.

### Fixed — a continuous (regression) target is no longer turned into class labels

`prep` used to run class encoding on every dataset, so a regression target such as
`2.5, 10.1, 0.3` was rewritten as `0, 1, 2` and a class dictionary was written beside it. On data
whose target values sit in blocks this happened under a **PASS** verdict, so nothing warned you.
Continuous targets are now passed through untouched and no class dictionary is produced.

If you prepared a regression dataset with an earlier version, re-run `prep` — the uploaded file's
target column was very likely wrong.

### Fixed — a missing target column no longer passes validation

`validate` accepted a CSV whose target column (the one named in your profile) was not in the file,
reporting **PASS**. It now reports `label_column_missing` and exits 2. `prep` used to crash on the
same input with an unhandled error; it now reports the same finding.

Anomaly detection is exempt — its data is unlabeled by design.

**This is a tightening.** A file that passed before can now be rejected. That is the intended
correction: such a file cannot be trained on.

### Changed — a leftover class dictionary beside a dataset that has none

When a dataset has no classes (regression, or anomaly data with no target column), `prep` no longer
writes a dictionary file. If one is already sitting at that path from an earlier run, it is removed
and reported — but **only after checking it really is a class map**. A file that cannot be
identified is never deleted; it is reported as something that must be moved before uploading.

### Changed — command output

`prep` printed `Wrote data.csv and None.` when there was no dictionary. It now prints
`Wrote data.csv.`

### Fixed — a regression (or anomaly) target no longer triggers "a class disappears" warnings

The window-survival check (which warns that a class's rows are too short a run to survive windowing)
was running on any numeric target column, so a **regression** target whose values sit in blocks — e.g.
`60, 90, 120` — was reported as classes that would "silently disappear" (`class_run_below_window`,
WILL_LOSE_DATA), and `prep` refused to write. A regression value is not a class and has no runs; the
check now runs only for a classification target. The same applies to anomaly detection (no classes).

### Fixed — a single blank label no longer invents a false "class too short" warning

A classification column with one blank/`NaN` in the middle of a long run was split at the blank, so a
genuine 81-row run was reported as a 40-row run below the window — a false WILL_LOSE_DATA. The blank
itself is (and was) a hard reject you must fix first; the window-survival check now waits until the
labels are clean rather than measuring runs across a hole. A class written inconsistently as both `0`
and `0.0` is also no longer split into two phantom classes.

### Changed — `validate` now warns about window survival (it was silent before)

On the standalone `validate` command the window-survival checks (`class_run_below_window`,
`session_below_window`) never actually ran, because the label column is read as text there. They now
run for a classification file, so `validate` can report **WILL_LOSE_DATA (exit 3)** where before it
said PASS. **This is a tightening**: a file with a class run — or a session — shorter than the window
now surfaces at the pre-upload gate instead of only inside `prep`. Every such finding still carries
"confirm against the platform's Processed Data view" — it is an upper bound on the loss.

### Added — the report now shows per-class *window* counts, not just row counts

The platform trains on **windows**, not rows, and the two diverge: a class recorded in short or
fragmented runs has plenty of rows but yields few clean windows. Validation now reports, for every
windowed classification dataset, the pure (single-label) windows each class yields at the recommended
training shift — the actual per-class training-set size (`window_class_yield`, an informational note).
When the windowed counts are imbalanced by more than 3× — which can happen even when the *row* counts
are perfectly balanced — you also get a `window_class_imbalance` advisory. Neither changes the verdict;
they tell you what the platform will build so a weak class is visible before you train. (A class that
yields *zero* windows is still flagged separately as losing data.)

### Fixed — shuffled / out-of-order rows are no longer hidden

The platform windows your data in row order, so rows that are out of time order build
temporally-incoherent windows and train a wrong model — but the validator never checked, because the
one place it looked at the time column sorted it first (to estimate the rate). We now check each
**recording** for backwards timestamps: on `validate` (the whole file), and on `prep` (each input file
as it is combined). A file whose rows jump backwards mid-recording, or that is sorted in reverse time
order, is reported `timestamps_out_of_order` (FIX_REQUIRED). A legitimate combine of several recordings
is **not** flagged — each file is checked on its own, so the natural clock reset between recordings is
never mistaken for a shuffle. Sub-step timestamp jitter on an otherwise-forward clock is not flagged;
only a real backwards jump (larger than one normal step) is. This does not run when Signal Processing
is off (row order is irrelevant then). `prep` refuses to write an out-of-order file unless you pass
`--write-anyway`; the tool never silently reorders your rows.

### Changed — a missing sampling rate blocks only when Signal Processing is on

With no time column and no recorded sampling rate, `validate` reported `rate_unknown` as FIX_REQUIRED
(exit 2) in every mode. With Signal Processing **off** (a tabular profile) the window math that needs
the rate does not run, so this is now an advisory that does not change the verdict. With Signal
Processing on (or unstated), it remains FIX_REQUIRED — the window is counted in samples, so the rate
is load-bearing.
### Fixed — a target column that mixes class names and class numbers no longer crashes

If your target labelled some rows by a class *name* (`left`) and others by that class's *number* (`1`)
from your profile's encoding, `prep` used to stop with an unexpected error and write nothing. It now
reports `label_keyspace_mixed` and asks you to relabel the column using **one** notation — all names,
or all numbers — then exits without writing (exit 2). A column that is entirely names, or entirely
numbers, is completely unaffected.

This removes a crash; it is not a new rejection of any file that produced output before. The tool will
not guess which class a mixed row means, because the two readings can disagree.

### Changed — resampling no longer fabricates decimal precision on an integer sensor column

When you `--resample`, a sensor column whose values are all whole numbers (e.g. a raw INT16
accelerometer at counts per g) used to come out as long fractional floats — a `197` became something
like `197.5557631762425`, inventing ~13 digits the sensor never recorded — because interpolation and
the anti-alias filter produce fractional estimates. That one fractional value then forced the whole
dataset to **FLOAT32**, several times larger on disk and on the chip than the **INT16** it should be.

Now, on the resampling path only, a column whose every source value was a whole number has its
resampled values rounded back to whole numbers, so no decimal precision is fabricated and the data type
stays INT8/INT16 where it belongs. The tool reports this as `resample_integer_preserved` (an
informational note listing the columns; it does not change the verdict). A column that genuinely holds
fractional values is left exactly as before.

**This changes the written bytes** for a dataset that resamples integer sensor columns — that is the
intended fix. Nothing changes if you do not resample, and a resampled *fractional* column is
byte-for-byte identical to before. If you prepared an integer dataset with `--resample` on an earlier
version, re-run `prep` to get the smaller, honest output. (The `recommended_dtype` note also now names
the column that made a dataset FLOAT32, so you can see whether it is a genuine float or something to
look at.)

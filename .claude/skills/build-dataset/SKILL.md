---
name: build-dataset
description: >-
  Guide the user end-to-end from raw inertial-sensor recordings to an upload-ready, centered, validated
  dataset for the Nordic Edge AI Lab platform — one conducted flow that pauses at each step to show
  evidence, explain, suggest, and get confirmation. Use when the user wants the whole journey rather than
  one piece: "guide me through preparing my data", "take me from raw files to upload, step by step",
  "build my dataset from start to finish", "walk me through it", "I have recordings, what do I do?".
---

# Build a dataset — guided, step by step

You are the conductor. Lead the user through the journey **one stage at a time**, and at each gate:
**show the evidence (their numbers) → explain it plainly → suggest what to do → wait for their confirmation
→ proceed.** Never auto-decide a judgement call; never present an experiential default or a Cohen's-d
number as a platform rule. Reuse the focused skills and the engine — don't reimplement. The hard contract
is in [_shared/platform-contract.md](../_shared/platform-contract.md) (canonical:
[wiki/architecture/platform-*](../../../wiki/architecture/platform-dataset-requirements.md)); cite it.

Engine commands (run from the repo root): `PYTHONPATH=src python3 -m data_builder.cli <prep|validate|quality-report> … [--json]`.

## Stage 0 — Frame the data (reconcile, don't assume)

Identify the recordings and confirm the dataset profile **against the files**, not from the user's say-so
([process P-02/P-03](../../../wiki/principles/process.md)): label column, sensor-axis columns, separator,
sampling rate (Hz), the class encoding, and an intended window size.

**Always ask the sensor full-scale** — accelerometer (±2g / 4g / 8g / 16g) and gyroscope (125 / 250 / 500 /
1000 dps) — and record them (`accel_full_scale_g`, `gyro_full_scale_dps`). They fix counts-per-g and
counts-per-dps, so keep the data **raw INT16 — never convert to floats** (the platform consumes raw
integers; conversion only loses fidelity/footprint), and use them to sanity-check scale and to segment rest
vs motion (at rest `|acc|` ≈ 1 g in counts **and gyro ≈ 0**). **Reconcile each source's scale against the
data** — recordings can silently mix accelerometer ranges/units; probe the at-rest gravity magnitude per
source, bring everything onto the one scale the device emits, or exclude the mismatches
([domain P-11](../../../wiki/principles/domain.md)).

**Hard gate — settle the nature of every class before you go near centering** ([domain P-05](../../../wiki/principles/domain.md)):
**ask the user** which classes are **continuous** motions (idle, "unknown", rotation, walking — a sustained
stream with no single start/finish → *trimmed, never centered*) and which are **discrete** gestures (tap,
flick, double-tap — clear start and finish, one motion peak → *centered*). Record the split in
`continuous_classes` / `gesture_classes`. **Never infer class nature from filenames or the gesture-demo
example** — a name like "rotate" looks like a gesture but is continuous. Getting this wrong sends a
continuous class into centering, where it can never sit mid-window.

Start from [the schema](../../../data/skill-presets/dataset-profile.schema.json) /
[example](../../../data/skill-presets/nordic-gesture-demo.json); write the confirmed profile to
`output/<name>/profile.json`. Confirm it back to the user in plain words before continuing.

## Stage 1 — Quality analysis (the evidence gate)

Profile the data and **look for a source collected differently from the rest** — the common "several
people contributed and one did it wrong" case:

```
PYTHONPATH=src python3 -m data_builder.cli quality-report <file...> --profile output/<name>.profile.json --json
```

(Each input file is treated as a source; or a session column if it's one file.) Also run
[`analyze_csv_signal.py`](../../../scripts/diagnostics/analyze_csv_signal.py) for per-class counts,
run-lengths and rate. **If a source looks like an outlier** (high Cohen's-d for a class vs the others):
show the evidence (which source, which class, the d-value, the axes it differs on), explain the likely
cause ("source C's *swipe* sits ~3 std from everyone else's *swipe* — probably recorded with a different
orientation or device"), and **suggest options — exclude that portion / re-collect it / keep it — then let
the user decide.** Frame Cohen's-d as *indicative*, not pass/fail ([case patterns](../../../wiki/synthesis/support-case-patterns.md)).
If a class is short or thin, surface it now and offer [collection-advice](../collection-advice/SKILL.md).

## Stage 2 — Clean & assemble

With the user's confirmed decisions, combine the kept recordings and repair the format. This is the engine's
`prep` (it also does the next stages); preview what it will do, then run it.

## Stage 3 — Center, then auto-verify (suggest, you confirm)

`prep` **auto-centers** gesture classes (peak mid-window) and trims continuous ones — default-on
([domain P-05](../../../wiki/principles/domain.md)). Then **confirm it worked**: run
[`check_signal_centered.py`](../../../scripts/diagnostics/check_signal_centered.py) on the output (pass the
profile's label/sensor names). Expected: gesture classes read **CENTERED** (tap-like ones LOOSE),
continuous classes RAW. **If a class reads RAW, first re-check its nature, do not reach for the window
knob:** a continuous class (rotation/idle) is *supposed* to read RAW — leave it. Only if a class the user
**confirmed is a discrete gesture** reads RAW has centering actually struggled; then say so with the
numbers, **try a couple of window sizes and recommend the best**, but **let the user approve** — and flag
honestly that a discrete gesture with no clear peak may be a *data* problem (weak/inconsistent gestures →
recollect), not a parameter to tune around ([process P-05 / domain P-07](../../../wiki/principles/process.md)).
Never tune the window to force a continuous class to center. Hand off to
[feature-advice](../feature-advice/SKILL.md) if direction/separability is the concern.

## Stage 4 — Resample (only if needed)

If the quality analysis showed mixed sampling rates, resample to one common rate
([domain P-04](../../../wiki/principles/domain.md)) — `prep --resample <HZ>`. Otherwise skip.

## Stage 5 — Recommend the feature enable-set (measured)

The platform extracts features itself, but **which families are enabled is the user's lever** — so produce an
**evidence-backed full enable-set**, not one or two asserted features ([domain P-12](../../../wiki/principles/domain.md),
[feature-advice](../feature-advice/SKILL.md)). Run the deterministic diagnostic on the centered output:

```
python3 scripts/diagnostics/feature_separability.py output/<name>/<name>.csv --profile output/<name>/profile.json
```

It windows each class, computes the time-domain catalogue per axis, ranks by separation, flags **magnitude-blind
class pairs** (best magnitude-only Cohen's-d ≲ 1 ⇒ a **direction** problem, not energy), gates Skewness/Kurtosis
on the storage dtype, and prints a recommended enable-set in full platform names. Present it as:

- **Energy** (Standard Deviation, Root Mean Square, Range, Mean Absolute Deviation, Absolute Mean) — rest vs active, energy differences.
- **Signed level + direction** (Mean, Min, Max, **Linear Regression Slope**, **Linear Regression Intercept**,
  Percentage of Signal over Zero, Percentage of Signal over Mean) — the only direction carriers; required for
  mirror/opposite classes (left/right, up/down, CW/CCW). Magnitude is direction-blind.
- **Impulse/shape** (Crest Factor, Hjorth Mobility, Hjorth Complexity) — sharp classes (taps).

**Hold back:** **INT16 ⇒ do NOT recommend Skewness/Kurtosis**; **FFT** needs a power-of-2 128–2048 window (off
otherwise). **Do NOT enable feature-selection in the first experiment** — advise it only later as optimization
(Stage 7). Present the set with the numbers that justify it, and **always name features in full as they appear
on the platform — no abbreviations** (e.g. "Linear Regression Slope", not "LR_SLOPE"; "Standard Deviation",
not "STD").

## Stage 6 — Validate & export (the pre-upload gate)

Run the full `prep` (or `validate`) and present the verdict **PASS / FIX-REQUIRED / WILL-LOSE-DATA** in the
[process P-07](../../../wiki/principles/process.md) shape: verdict → their numbers → numbered fixes each
citing the rule → notes. The engine **refuses to write** a file that would be rejected or silently lose a
class unless the user explicitly overrides.

On PASS, deliver **one self-explanatory folder, not loose files** ([process P-09](../../../wiki/principles/process.md)):
write into `output/<name>/` the upload CSV, the dictionary the engine **auto-writes** next to it
(`<csv>_dictionary.json` — **do not hand-make a second one**), the `profile.json` recipe, and a
plain-language `README.md`. The README must name the **single file to upload**, the class map, the
desktop-runner flags (`-t <label-col>`), **the recommended platform settings** — training shift = window (no
overlap), **inference shift at 50–70% overlap** ([domain P-02](../../../wiki/principles/domain.md)), storage
type, and the **measured feature enable-set from Stage 5** — and one line on what each other file is for.
**Close by pointing the user to that `README.md`** as the place with all the details, and briefly note that
**if they later have separate validation data, you can compare it to the training data, run the
inference-runner, and report validation details**. Reuses [prep-dataset](../prep-dataset/SKILL.md) /
[validate-upload](../validate-upload/SKILL.md).

## Stage 7 — After they train (optimization & validation)

Once they've trained and **tested in real conditions**, help interpret results: dead classes / confusion
([diagnose-data](../diagnose-data/SKILL.md)), and — only now, if optimization is needed — advise re-running
the **same experiment with feature-selection on** to prune for size ([domain P-12](../../../wiki/principles/domain.md)).
If they have **separate validation data**, compare its feature distribution to the training classes and run
the inference-runner to report real-world accuracy. **Note:** the platform extracts/selects features itself —
this stage *advises*; it does not compute features into the file.

## How to run the flow
- One stage at a time; end each with a short "here's what I found / did — OK to continue, or adjust?".
- Plain language, no internal jargon; the user should always see the evidence behind a suggestion.
- If the user says "just run it", proceed end-to-end but still **stop on any real decision** (an outlier
  source, a class that won't center, a FIX-REQUIRED/WILL-LOSE-DATA verdict).

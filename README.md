# dataset-builder

**Prepare inertial-sensor recordings into upload-ready training datasets for the [Nordic Edge AI Lab](https://ai.lab.nordicsemi.com) platform.**

[![Platform: Nordic Edge AI Lab](https://img.shields.io/badge/platform-Nordic%20Edge%20AI%20Lab-00A9CE)](https://ai.lab.nordicsemi.com)
[![Docs](https://img.shields.io/badge/docs-edge--ai--lab-00A9CE)](https://docs.nordicsemi.com/bundle/edge-ai-lab/page/index.html)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-81%20passing-brightgreen)](src/tests/)

> Clone it, point it at your raw CSVs, and get back a single training file that the platform will actually accept — plus an honest report of anything that would be silently dropped before you upload.

---

## What this is

[Nordic Edge AI Lab](https://ai.lab.nordicsemi.com) is Nordic Semiconductor's no-code TinyML service: you upload a CSV of sensor readings, and it automatically builds a compact model (via the **Neuton** framework or the **Axon NPU**) that runs on Nordic's ultra-low-power wireless SoCs (Cortex-M0/M4/M33).

The platform is strict about its input. Get the format, encoding, labels, or windowing wrong and your data is rejected — or worse, *silently* trimmed during the platform's windowing step, so you train on less data than you think.

**dataset-builder** is the missing local step between *"I have a folder of accelerometer/gyroscope recordings"* and *"I have one clean CSV ready to upload."* It:

- **Combines** many recordings into a single training file (one dataset → one model).
- **Fixes** encoding, separators, decimal format, column names, data types, and label encoding to match the platform contract exactly.
- **Centers** discrete gestures and **resamples** mixed sampling rates when needed.
- **Validates** a CSV against the platform's hard rules *before* you upload — returning `PASS` / `FIX-REQUIRED` / `WILL-LOSE-DATA`, with every problem tied to the specific rule it breaks.
- **Diagnoses** why data is being dropped, a class is never predicted, or left/right gestures get confused.

It ships both as a **command-line engine** and as a set of **AI assistant skills** that walk you through the whole journey conversationally.

---

## Why it's structured this way

This repo is more than a script — it's a **compiled knowledge base** about the Nordic Edge AI Lab platform and the craft of preparing inertial-sensor data for it. Rather than re-deriving the platform's rules from documentation every time, the rules are extracted once into an interlinked wiki, and the code and skills cite that wiki by reference.

That makes the repo a **starting point you can grow**: download it, use it, and as you learn more about your sensors or the platform, the knowledge accretes in one place instead of scattering across notes.

```
dataset-builder/
├── src/data_builder/   The engine — CSV intake → analysis → preprocessing → validation → export
├── .claude/skills/     The AI assistant — conversational, confirm-first data-prep skills
├── scripts/            Standalone diagnostic & preprocessing scripts (numpy + pandas, or drop-in C)
├── wiki/               Compiled knowledge: the platform contract, decisions, principles, playbooks
├── data/               Dataset-profile schema + worked examples
├── raw/                Source material (platform docs, samples) — read-only
└── methodology/        How the knowledge base is maintained
```

The single source of truth for the platform's input rules lives in [`wiki/architecture/platform-dataset-requirements.md`](wiki/architecture/platform-dataset-requirements.md). When the platform and the wiki disagree, the platform wins and the wiki is corrected.

---

## Requirements

- **Python 3.9+**
- **numpy** and **pandas** (the only runtime dependencies)

```bash
python3 -m pip install numpy pandas
```

No build or install step — the engine runs straight from the source tree.

---

## Quick start

From the repo root:

```bash
# 1. Validate a CSV against the platform contract before uploading
PYTHONPATH=src python3 -m data_builder.cli validate my_data.csv \
    --profile data/skill-presets/nordic-gesture-demo.json

# 2. Combine raw recordings into one upload-ready training file
PYTHONPATH=src python3 -m data_builder.cli prep recording1.csv recording2.csv \
    --profile data/skill-presets/nordic-gesture-demo.json \
    --out output/training.csv
```

A **dataset profile** (a small JSON file) tells the engine your column names, sampling rate, units, label encoding, and window size. Start from the schema and the worked example:

- Schema: [`data/skill-presets/dataset-profile.schema.json`](data/skill-presets/dataset-profile.schema.json)
- Worked example: [`data/skill-presets/nordic-gesture-demo.json`](data/skill-presets/nordic-gesture-demo.json)

Copy the example, then edit every field to match your actual file — the demo numbers (e.g. `idle=0`, `unknown=1`, gestures `2..7`, a 99-sample window) are an *illustrative convention from the platform's gesture walkthrough, not a platform rule.*

---

## The command-line engine

`data_builder.cli` exposes three subcommands. All accept `--json` for machine-readable output.

| Command | What it does |
|---|---|
| `validate <csv>` | Checks a CSV against the platform contract. Reports `PASS` / `FIX_REQUIRED` / `WILL_LOSE_DATA`, each finding tied to its rule. Optional `--holdout <csv>` to check a test file's structure matches. |
| `prep <inputs...>` | Combines recordings into one upload-ready CSV (`--out`). Auto-centers gesture datasets (`--no-center` to skip), optionally resamples (`--resample HZ`). Won't write if it would break the contract unless you pass `--write-anyway`. |
| `quality-report <inputs...>` | Profiles each source file and flags any recording/user whose feature distribution looks like a different regime (indicative Cohen's *d* — not a platform pass/fail). |

**Exit codes** (a frozen contract the skills rely on): `0` = pass/ok · `2` = fix required · `3` = will lose data · `4` = I/O, profile, or usage error.

```bash
# Resample mixed-rate recordings to 100 Hz and assemble, skipping centering
PYTHONPATH=src python3 -m data_builder.cli prep session_*.csv \
    --profile my_profile.json --out output/training.csv \
    --resample 100 --no-center

# Compare sources to spot an outlier recording before you train
PYTHONPATH=src python3 -m data_builder.cli quality-report user_*.csv \
    --profile my_profile.json
```

### Run the tests

```bash
PYTHONPATH=src python3 -m unittest discover -s src/tests -v
```

---

## The AI assistant (skills)

If you use [Claude Code](https://claude.com/claude-code), this repo ships six conversational skills under [`.claude/skills/`](.claude/skills/) that drive the engine for you and explain each step. They **never auto-apply** changes — they show you the evidence and confirm before acting.

| Skill | Use it when you want to… |
|---|---|
| **build-dataset** | Be guided end-to-end from raw recordings to a validated, upload-ready file. |
| **prep-dataset** | Combine, fix, center, or resample recordings into one training CSV. |
| **validate-upload** | Gate-check a CSV: *"will the platform accept this, and will it lose data?"* |
| **diagnose-data** | Find out why data is removed, a class is never predicted, or gestures are confused. |
| **collection-advice** | Decide how much data to collect and how to record, label, and clean it. |
| **feature-advice** | Choose which platform features and window settings make classes separate. |

---

## The diagnostic & preprocessing scripts

[`scripts/`](scripts/) holds standalone, reference tooling generalized from common field scenarios — each script is self-contained (Python: numpy + pandas; C: drop-in, no deps). See [`scripts/README.md`](scripts/README.md). Highlights:

- `diagnostics/analyze_csv_signal.py` — first-pass profiler: schema, NaNs, label distribution, session lengths, per-session sampling rate. Run it first on any CSV.
- `diagnostics/window_survival_sim.py` — simulates the platform's per-window label extraction to show how many windows each label keeps. Run this when *"data is being removed"* or *"a label has no data."*
- `preprocessing/center_training_data.py` — centers discrete gestures and trims continuous classes to a window multiple, per class.
- `postprocessing/postprocessing_pipelines.py` — compares threshold / consecutive-N / majority-vote / EMA pipelines on model output.
- `firmware/` — ~15-line validated on-device C postprocessing (EMA + unknown-margin suppression) and a median-3 spike filter.

---

## The platform contract, in brief

The full, verified rules live in [`wiki/architecture/`](wiki/architecture/). The essentials your output CSV must satisfy:

- **One CSV**, UTF-8 / ISO-8859-1, header row first, separator ∈ `, ; | ^` or tab, **dot** decimal, unique column names matching `[A-Za-z0-9_-]`.
- **All values numeric** — no empty / `NA` / `NAN`. Storage types INT8 / INT16 / FLOAT32 (Axon ⇒ FLOAT32 only).
- **Inertial layout:** one row = sensor readings at one timestamp + a label column. Rows **time-ordered, never shuffled** (the platform does the windowing). **Single sampling rate** — resample if mixed; always record the Hz.
- **Classification target** starts at `0`, contiguous; **≥ 2 classes, ≥ 20 samples each**.
- **Windowing (platform-side):** window 10–1000 samples (128–2048, power-of-2 when frequency-domain features are on). A holdout file must match the training file's structure, else the platform auto-splits 80/20.

---

## Status & honesty note

This tool is under active development. Its preprocessing heuristics — the window-survival model and the gesture-centering / resampling transforms — are built from the platform's documented contract and validated reference scripts, but **not all are yet confirmed against the live platform's "Processed Data" view.** Where the tool reports potential data loss, treat it as *"verify in the platform's Processed Data view,"* not a guarantee. See [`STATE.md`](STATE.md) for current status.

---

## Contributing knowledge

This repo is designed to be enriched. New facts about the platform or about data preparation go into [`wiki/`](wiki/), not into scattered notes — see [`methodology/`](methodology/) for how the knowledge base is maintained and grows. Code changes go through a spec → review → implement → re-review cycle.

---

## Disclaimer

This is an **experimental utility maintained by Nordic Semiconductor**, provided **as-is** without warranty or a guaranteed support SLA. *Nordic Semiconductor*, *Nordic Edge AI Lab*, *Neuton*, and *Axon* are trademarks of their respective owners. Always confirm behavior against the [official platform documentation](https://docs.nordicsemi.com/bundle/edge-ai-lab/page/index.html).

---

## License

This project is MIT-licensed — see [`LICENSE`](LICENSE). Note that [`raw/platform-docs/`](raw/platform-docs/) reproduces Nordic Semiconductor official documentation and remains © Nordic Semiconductor ASA.

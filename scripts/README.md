# scripts/ — diagnostic & data-preparation toolkit

Reusable, self-contained scripts for diagnosing and preparing inertial-sensor data for the platform. Generalized from field experience (practitioner knowledge); **draft/reference tooling**, not (yet) the production data-builder in `src/`. Each is standalone (Python: `numpy` + `pandas` only; C: drop-in, no deps).

The *why* behind each script — the diagnostic moves, the rules, and the worked cases — lives in the wiki:
- [synthesis/support-diagnostic-playbook.md](../wiki/synthesis/support-diagnostic-playbook.md) — how to investigate a data-prep problem
- [synthesis/support-troubleshooting-checklist.md](../wiki/synthesis/support-troubleshooting-checklist.md) — fast symptom→cause triage
- [synthesis/support-case-patterns.md](../wiki/synthesis/support-case-patterns.md) — worked-case anatomies of common data-prep scenarios
- [principles/domain.md](../wiki/principles/domain.md) & [principles/process.md](../wiki/principles/process.md) — the always/never rules these tools encode

> Scope note: gesture class indices in defaults (idle=0, unknown=1, gestures=2..7) are an *illustrative convention*, not a platform rule. Override per dataset. The platform's hard rules are in `wiki/architecture/platform-*`.

## diagnostics/ — understand a dataset or model before theorizing

| Script | Purpose | Typical use |
|---|---|---|
| `analyze_csv_signal.py` | First-pass profiler: schema/dtypes, NaN check, label distribution (+ contiguity warning), session count/lengths, per-session class crosstab, **per-(session,label) run-length stats**, per-session sampling rate from a time column. | Run first on any uploaded CSV. |
| `window_survival_sim.py` | Simulates the per-window pure-label extraction for given `--window`/`--shift` pairs; reports total / kept / dropped and **per-label surviving window counts** (flags zero). | "Data is removed" / "a label has no data" complaints. |
| `feature_mask_decoder.py` | Decodes `FEATURES_EXTRACTION_MASK` from a model archive's `nrf_edgeai_user_model.c` into a per-axis feature table; flags whether `LR_SLOPE`/`LR_INTERCEPT` (the only signed-asymmetry features) are enabled. | Direction-confusion / dead-class tickets. |
| `check_signal_centered.py` | Per class, walks non-overlapping windows and reports the distribution of the motion-peak position → verdict CENTERED / LOOSE / RAW. | "Is this training data centered?" before any feature analysis. |
| `windowed_feature_distribution_comparison.py` | Computes per-window time-domain features for train (per class) vs test; per-axis STD envelopes + mean Cohen's-d distance test↔class. | "Predictions are uniformly wrong" → distribution-shift check. |
| `feature_separability.py` | Deterministic. Windows each class, ranks the time-domain catalogue by multiclass ANOVA-F + per-class one-vs-rest, flags **magnitude-blind class pairs** (direction problems), gates Skewness/Kurtosis on storage dtype, and prints a recommended platform enable-set in full feature names. | "Which features should I enable?" — the measured enable-set (build-dataset Stage 5 / feature-advice). |

## preprocessing/ — shape raw recordings into upload-ready training data

| Script | Purpose | Notes |
|---|---|---|
| `center_training_data.py` | **Standalone** centering tool: splits a multi-class IMU CSV by class, centers discrete-gesture classes (peak mid-window), trims continuous classes (idle/unknown) to a window multiple, concatenates in class order. Supports `--auto-work-axis`, `--work-axis-per-class`, `--trim-edges`. | Self-contained (no external centering script needed). Output is comma-separated, upload-ready. |
| `apply_centering_per_class.py` | Wrapper that drives an **external** `center_signal.py` correctly per-class (never across class boundaries) when a project already has its own centering script. | Needs `--src-dir` pointing at the external `center_signal.py`. Prefer `center_training_data.py` if you don't have one. |

## postprocessing/ — turn model output probabilities into clean predictions

| Script | Purpose | Notes |
|---|---|---|
| `postprocessing_pipelines.py` | On a runner predictions CSV (`target, Probability of 0..N`): **postprocessing-ceiling check** (dead class if max-prob ≈ 0) + side-by-side comparison of baseline / threshold / consecutive-N / majority-vote / exclude-unknown / EMA / hybrid pipelines, with per-class frame & episode counts. | Run before promising any postprocessing fix. |

## firmware/ — production on-device C

| File | Purpose | Read first |
|---|---|---|
| `firmware_postprocessing_ema_unknown_margin.c` | ~15-line recommended on-device postprocessing: EMA (α=0.3) + unknown-margin suppression (0.2). No threshold, no consecutive-N. Optional event-on-transition detector at the bottom. | This is the validated default. |
| `firmware_median3_filter.c` | 3-tap median filter for IMU sample-and-hold/FIFO-overrun spikes. | ⚠️ Has a prominent **training/inference parity** warning — do not apply only at inference. See [principles/domain.md](../wiki/principles/domain.md). |

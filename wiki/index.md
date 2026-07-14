# Wiki Index

> Catalog of wiki pages — one line per page, grouped by type. Format — [../methodology/index-log-format.md](../methodology/index-log-format.md).

## architecture

- [platform — Dataset requirements (the input CSV contract)](architecture/platform-dataset-requirements.md) — hard CSV contract: format, encoding, separators, columns, value/type rules, class minimums, sensor row layout, holdout. _Updated: 2026-06-25_
- [platform — Data pipeline (end-to-end workflow)](architecture/platform-data-pipeline.md) — the 9-step model-creating pipeline; where our tool plugs in (upload/setup); solution creation, target column, session ID, holdout 80/20. _Updated: 2026-06-25_
- [platform — Deployment, inference & model settings](architecture/platform-deployment-inference.md) — bit depth, output format, target HW (Cortex-M0/M4/M33, Axon NPU); desktop inference-runner CSV contract (target/session/delimiter defaults). _Updated: 2026-06-25_
- [platform — Feature extraction & selection](architecture/platform-feature-extraction.md) — feature catalogue (time/frequency domain), per-axis counting, FFT power-of-2 window rule, feature-selection pruning rules, the measured enable-set method (direction features, INT16 hold-backs). _Updated: 2026-06-30_
- [platform — Preprocessing options (data type, normalization, task, metrics)](architecture/platform-preprocessing-options.md) — INT8/INT16/FLOAT32 ranges, normalization, task types & evaluation metrics; metric is evaluation-only, not a training input. _Updated: 2026-07-10_
- [platform — Signal Processing (windowing & sampling contract)](architecture/platform-signal-processing.md) — window size 10–1000 (FFT 128–2048 pow2), sliding shift, sub-windowing, single-sampling-rate rule (+ our anti-alias resampling method), SRAM. _Updated: 2026-07-13_
- [data — Dataset-profile (skill preset) contract](architecture/data-skill-preset-contract.md) — the per-dataset profile schema the skills + src/ engine consume; confirm-first, never auto-applied; runtime files in data/skill-presets/. _Updated: 2026-06-25_

## decisions

- [ADR-0001 — User-facing capabilities ship as Skills](decisions/adr-0001-user-facing-skills-mechanism.md) — skills (not instructions/presets) are the surface; presets = confirm-first data; instructions = one shared cited reference; the 5-skill catalog. _Updated: 2026-06-25_
- [ADR-0002 — data-builder engine architecture](decisions/adr-0002-data-builder-engine-architecture.md) — two-layer validation (raw-bytes + dataframe), Finding/Report/verdict taxonomy, refuse-on-loss, flag-never-truncate, numpy/pandas-only (scipy on resample path since ADR-0003). _Updated: 2026-07-13_
- [ADR-0003 — scipy.signal on the resampling path (amends ADR-0002)](decisions/adr-0003-scipy-on-resample-path.md) — permit scipy.signal.decimate/resample_poly in resample.py for anti-aliasing; the bare np.interp downsample silently aliases; scipy kept to that one path. _Updated: 2026-07-13_

## discovery

- [platform — Data collection, labeling & cleaning practices](discovery/platform-data-collection-practices.md) — PoC data amounts, recording setup, labeling/encoding, segmentation (centering script), cleaning; worked gesture example; production/multi-user + class-specific tips. _Updated: 2026-06-25_
- [platform — The downloaded solution archive](discovery/platform-model-archive.md) — what the platform returns: `nrf_edgeai_generated/` + `artifacts/inference_runner/`; feature mask & input-scaling clamps; on-device 4-call API; predictions CSV format. _Updated: 2026-06-25_
- [platform — Nordic Edge AI Lab (what it is)](discovery/platform-overview.md) — no-code TinyML platform for Nordic SoCs; Neuton vs Axon NPU; domains; exclusivity; ready-to-use models; access. _Updated: 2026-06-25_
- [platform — Neuton neural-network framework](discovery/platform-neuton-framework.md) — neuron-by-neuron growth, patented global optimization, vs traditional/NAS; minimal inputs (data+target+metric); metric is evaluation-only, training always optimizes cross-entropy. _Updated: 2026-07-10_
- [platform — Task types (and what each needs from the data)](discovery/platform-task-types.md) — classification/regression/anomaly/wake-word; anomaly = unlabeled, single model, no holdout; analytics tools. _Updated: 2026-06-25_

## synthesis

- [Case patterns — anatomies of common data-prep scenarios](synthesis/support-case-patterns.md) — 3 reusable patterns: data-removal from short runs+overlap; dead classes / postprocessing ceiling; iteration recovery + pipeline choice. _Updated: 2026-06-25_
- [Diagnostic playbook — investigating a data-prep problem](synthesis/support-diagnostic-playbook.md) — ordered investigation moves (profile → run-lengths → window survival → centering → feature mask → ceiling → distribution shift → reply). _Updated: 2026-06-25_
- [Troubleshooting checklist — fast symptom→cause triage](synthesis/support-troubleshooting-checklist.md) — symptom→cause table + staged checklist by pipeline stage (upload, classes, windowing, footprint, accuracy, inference, holdout, wake word, anomaly). _Updated: 2026-06-25_

## principles

- [Domain principles — inertial data prep & modeling](principles/domain.md) — P-01..P-15: window survival, training/inference shift, contiguous labels, single sampling rate, centering, direction features, postprocessing ceiling, EMA default, preprocessing parity, idle/unknown class, sensor-scale reconciliation, measured feature enable-set, metric is evaluation-only, resampling decision procedure (anti-alias/measure-first), physical-meaning gate before centering. _Updated: 2026-07-13_
- [Process principles — how to diagnose a user's problem](principles/process.md) — P-01..P-08: read both halves, profile first, reconcile claims vs data, simulate, ceiling/parity checks, confirm protocol, reply structure, skills-reference-wiki-by-path. _Updated: 2026-06-25_

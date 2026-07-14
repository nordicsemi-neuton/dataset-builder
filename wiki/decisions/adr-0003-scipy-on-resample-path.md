---
type: decision
status: active
updated: 2026-07-13
sources:
  - ./adr-0002-data-builder-engine-architecture.md
  - ../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md
  - ../principles/domain.md
tags: [decision, data-builder, resampling, dependencies, scipy, anti-aliasing]
---

# ADR-0003 — Permit scipy.signal on the resampling path (amends ADR-0002)

Status: active
Date: 13.07.2026

## Context

[ADR-0002](adr-0002-data-builder-engine-architecture.md) chose **numpy + pandas only (no scipy)** so the
tool stays trivially installable for third parties. The resampler [`resample.py`](../../src/data_builder/resample.py)
accordingly uses `numpy.interp` (linear interpolation) straight onto the target grid.

An embedded engineer's review ([notes](../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md))
showed this **silently aliases when downsampling**: linear interpolation onto a *coarser* grid does not
remove signal energy above the new Nyquist frequency — those frequencies fold back into the band and
corrupt exactly the statistical features the platform extracts (STD, RMS, crest factor…). On classification
this shows up as mysteriously degraded features, with nothing wrong visible in the CSV. Correct downsampling
requires an **anti-alias filter before decimation** (`scipy.signal.decimate` for integer factors,
`resample_poly` for fractional — both filter internally). Silent data corruption shipped to a third party is
the precise outcome ADR-0002 exists to prevent, so the no-scipy constraint now conflicts with the higher
principle (correctness over dependency-minimalism). Hand-rolling an FIR/polyphase anti-alias filter in numpy
is possible, but it is correctness-critical DSP we would have to design, review, and maintain ourselves.

## Decision

**Permit `scipy.signal` (specifically `decimate` / `resample_poly`) on the resampling path** in
`src/data_builder/resample.py`. ADR-0002's "numpy + pandas only, no scipy" is **narrowed** to
"numpy + pandas + `scipy` — `scipy` limited to the resampling path (anti-aliasing)". The rest of the engine
stays numpy/pandas + stdlib `unittest`; **pytest and jsonschema remain rejected** (ADR-0002 unchanged there).
The reference `scripts/` stay scipy-free (a dead scipy import was deliberately removed in
[databuilder-002](../../specs/databuilder-002-reference-script-fixes.md)) — scipy is added only where
anti-aliasing needs it, not reintroduced project-wide. Graceful-degradation vs hard-requirement behaviour of
the scipy import is settled in spec [databuilder-008](../../specs/databuilder-008-resampling-antialias.md).

## Consequences

**Easier:** correct, filtered down/up-sampling with battle-tested code; we don't own and verify hand-rolled
DSP. **Harder / watch:** one more third-party dependency to pin and ship (update release deps / any
packaging manifest, and the "trivially installable" claim in ADR-0002's rationale); the scipy import must be
handled cleanly (hard dependency, or degrade with a clear finding when absent — decided in databuilder-008);
keep scipy contained to `resample.py` so the dependency surface doesn't creep back across the engine.

## Alternatives considered

- **Hand-rolled numpy FIR / polyphase anti-alias filter** — rejected: correctness-critical DSP we would
  have to design, review, and test ourselves, when scipy already does it correctly and is near-universal.
- **Warn-only / refuse downsampling** — rejected: blocks a legitimate, common operation (mixed-rate
  datasets routinely need downsampling to the lowest common rate); defers the problem rather than fixing it.
- **Keep numpy/pandas-only, accept linear-interp downsampling** — rejected: it silently aliases, the exact
  silent-corruption class ADR-0002 refuses to ship.

## Sources

Embedded-engineer notes ([raw](../../raw/harvested-practice/2026-07-13-resampling-decision-procedure.md));
[ADR-0002](adr-0002-data-builder-engine-architecture.md); domain [P-04](../principles/domain.md) / **P-14**;
spec [databuilder-008](../../specs/databuilder-008-resampling-antialias.md); this session (13.07.2026).

---
type: decision
status: active
updated: 2026-07-27
sources:
  - ../../specs/databuilder-021-resample-integer-preservation.md
  - ./adr-0002-data-builder-engine-architecture.md
  - ./adr-0003-scipy-on-resample-path.md
  - ../architecture/platform-preprocessing-options.md
tags: [decision, data-builder, resample, data-type, integer-preservation, byte-identity, engine]
---

# ADR-0004 — resample re-quantizes an integral sensor column, preserving the represented value

Status: active
Date: 27.07.2026

Narrows [ADR-0002](adr-0002-data-builder-engine-architecture.md) `:71` ("sensor values are never cast to
int (floats preserved bit-for-bit)"). Extracted from spec `databuilder-021` (sprint task **B4**). This
is the fourth amendment note on ADR-0002 (after ADR-0005 / 0006 / 0007, dated 25.07); it carries the
**lowest number but the latest date** because 0004 was reserved for B4 while 0005–0007 landed first.

## Context

`--resample` interpolates a continuous signal onto a new time grid (`np.interp` on the up/no-op path;
`scipy.signal.resample_poly` on the anti-aliased downsample path, ADR-0003). Those estimates are
generically fractional, so a sensor column that was **integer-valued in the source** (a raw INT16
accelerometer at counts per g — `normalize_numeric` already types it `int64`) left resample as `float64`
with fabricated precision. Measured defect (tester review, 23.07.2026): a ±8 g INT16 wrist set shipped
`197.5557631762425` — ~13 digits the sensor never produced — and that one fractional value forced
`datatype.recommend_dtype` to **FLOAT32** for the whole dataset (a 13.3 MB file where ~2 MB / INT16 would
do, and a larger on-device model). It contradicts domain [P-11](../principles/domain.md) ("raw INT16 …
never convert to floats").

Read literally, ADR-0002 `:71` ("never cast to int … floats preserved bit-for-bit") forbids the fix. But
that clause was written to stop the *writer* silently truncating floats; a resampled integer column is a
different case — the values were integral, and representing them at the sensor's own integer resolution
*preserves* the represented value, whereas the fabricated float *changed* it.

## Decision

Narrow ADR-0002 `:71` to:

> The writer still **never casts a column to an integer storage dtype**, and a value is **never changed
> except by an explicit, disclosed transform** (resampling here; centering is the other such transform).
> On the **resampling path only**, a sensor column **whose every source value is a whole number** has its
> resampled *estimates* **re-quantized** (`np.round`) to the sensor's own integer resolution — **the
> column remaining `float64`** — so the tool does not fabricate decimal precision the sensor never
> recorded. Recorded as a **verdict-neutral provenance finding**. It licenses **no** integer cast and
> changes **nothing** on the non-resampled path.

Realised entirely in `resample.py` `resample_to_rate` + a one-line evidence enrichment in
`datatype.py`; the writer (`csv_io._format_value`/`write_table`) is **read, not modified**:

1. **Detect by value content, dataset-wide.** A sensor column is "integral" iff every non-NaN source
   value is a whole number (`np.mod(arr,1)==0`), the same test `recommend_dtype` uses — robust to
   `int64` / `float64` / string input. `{time, label, session}` columns are excluded defensively (never
   interpolated; the time grid is a continuous regenerated grid that must not be rounded).
2. **Re-quantize once, only when a resample ran.** After `pd.concat(out_parts)`, round the integral
   columns via `np.round(pd.to_numeric(..., errors="coerce"))` — object-safe on a string-typed
   direct-caller column mixed with a run left at its original rate. Gated on `resampled_any` (any run
   actually interpolated), so a fully-refused / no-resample frame is untouched. `csv_io._format_value`
   already renders an integral `float64` (`198.0`) as `"198"`, so no writer change is needed and the
   column keeps NaN-tolerance.
3. **Disclose, never silently.** A verdict-neutral INFO `resample_integer_preserved` names the rounded
   columns. Its message is a **group** statement ("integral sensor columns had their resampled estimates
   re-quantized …"), not a per-column fabrication claim, so it does not over-claim on a constant column
   or a refused run.
4. **`recommend_dtype` evidence (monotone).** Its FLOAT32 `reason` now names the first fractional column
   — provenance so a user seeing FLOAT32 can tell a genuine float column from (post-fix: never) a
   resample artifact. The returned **dtype value is unchanged for every input**; report-only.

## What the narrowing deliberately does NOT claim

- **Not** "the values the sensor produced." Resampling produces estimates at new time points; the
  anti-aliased downsample FIR can even ring past the source range (an INT8-max 127 source can produce a
  rounded 138 — inherent to anti-aliased downsampling, pre-existing, not introduced here). The honest
  claim is only: **no fabricated sub-LSB precision beyond the sensor's integer resolution.**
- "Integer resolution" is exact only for |value| < 2^53; every real INT8/INT16 sensor satisfies this by
  orders of magnitude, and above-range integers are FLOAT32 regardless, so defect #10 is unaffected.
- **Not** a licence to cast: the column stays `float64`; only its *values* are whole. The non-resampled
  path, and a resampled *fractional* column, are byte-for-byte unchanged.

## Rejected alternatives

- **Fix it in `csv_io._format_value`** (round-integral-columns at the writer). Rejected: the writer
  formats **every column of every dataset for every task type** — the broadest blast radius in the
  engine — and touching it endangers the byte-identity this change is built around. The fabrication is
  upstream, so the fix is upstream ([P-22](../principles/process.md): don't realign the max-blast-radius
  component; fix at the source).
- **Only round when it yields a dtype benefit** (skip when a sibling column already forces FLOAT32).
  Rejected: couples `resample.py` to the dtype decision and makes a column's behaviour depend on its
  siblings (context-dependent, unpredictable). The per-column rule ("every source value integral →
  re-quantise") is simpler and matches the represented-value contract; the always-true rationale is "no
  fabricated precision", not "avoid FLOAT32" (which is false on a mixed set).
- **Cast the column to an integer storage dtype** (`int64`). Rejected: that is exactly the cast ADR-0002
  guards; `int64` cannot carry the NaN the pipeline tolerates elsewhere, and `_format_value` already
  renders an integral `float64` as an integer, so a cast buys nothing.
- **Round on the whole concatenated frame** rather than the integral sensor set. Rejected: would collapse
  the continuous time grid and break monotonicity.

## Consequences

- **One intended byte change.** For an existing user who `--resample`s integer sensor data the written
  CSV changes (integer-rendered instead of fabricated floats) and `recommend_dtype` recovers INT8/INT16.
  Proven by a resample/no-resample × int/float **SHA-256 matrix** (`dev/databuilder-021_resample_int_matrix.py`,
  never ships): the non-resampled and resampled-**float** paths are byte-identical to the prior release,
  the class dictionary is identical on every path, and only the resampled-**integral** CSV differs.
  Disclosed in `CHANGELOG.md`; trivially reversible (re-run `prep`).
- **INT recovery is undone by centering.** `center_per_class` runs after resample and subtracts a
  per-class mean → fractional → FLOAT32 again, so the dtype win lands on *not-centered* sets (activity /
  continuous / `--no-center`) — which is the defect-#10 case. Centering also reads the re-quantised
  work-axis, so it can shift which rows survive by ≤1 sample: a legitimate downstream consequence of
  feeding centering the honest signal, disclosed, and outside the exact-SHA claim.
- **Finding/Report/exit-code contract stands.** `resample_integer_preserved` is verdict-neutral INFO;
  `recommend_dtype`'s change is a report-only `reason` string (the `recommended_dtype` finding's code,
  severity, `data`, and verdict are unchanged). The five skills reference findings by rendered message +
  `rule_ref`, so no skill file changes.
- **ADR-0002 `:71`** gains an amendment note pointing here (placed chronologically last, dated 27.07,
  despite this ADR's lower number).

## Sources

Spec `databuilder-021` (sprint task B4), the reinforced spec gate (5 + 3 reviewers) and the impl gate
(2 reviewers, by execution; fix `fc781fa`, parent `2500b25`, suite 239 → 248). Builds on
[ADR-0002](adr-0002-data-builder-engine-architecture.md), [ADR-0003](adr-0003-scipy-on-resample-path.md).

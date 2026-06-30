---
name: feature-advice
description: >-
  Advise which platform features to enable/disable and which window settings to choose so classes
  separate accurately on Nordic Edge AI Lab — the tool never computes features, the platform does. Use
  when the user asks "which features should I enable?", "why don't my classes separate?", "left and right
  are confused — which feature fixes that?", "should I turn on FFT / spectral features?", or "my model is
  too big from too many features".
---

# Advise on features & windowing for class separability

The platform extracts a fixed catalogue of features automatically (per axis, per window) — the user only
chooses **which** features are enabled and the window/sub-window settings that gate them. So this skill
advises; it does not compute features. Canonical knowledge:
[feature extraction & selection](../../../wiki/architecture/platform-feature-extraction.md),
[signal-processing / windowing](../../../wiki/architecture/platform-signal-processing.md),
[domain principles](../../../wiki/principles/domain.md).

## 1. Gate: is the data centered? (discrete gestures)

Raw and centered datasets are not comparable in feature space. Before any separability analysis, confirm
centering with [`check_signal_centered.py`](../../../scripts/diagnostics/check_signal_centered.py); if raw,
center first (the **prep-dataset** skill's `--center`, or
[`center_training_data.py`](../../../scripts/preprocessing/center_training_data.py)) — per class, never
across class boundaries ([domain P-05](../../../wiki/principles/domain.md)).

## 2. Decode the enabled features (if a model archive is available)

[`feature_mask_decoder.py`](../../../scripts/diagnostics/feature_mask_decoder.py) on the archive's
`nrf_edgeai_user_model.c` shows which features are on per axis, and flags whether LR_SLOPE/LR_INTERCEPT are
enabled.

## 3. Produce the enable-set from a measured separability pass

Don't assert one or two features — **measure and recommend a full set** ([domain P-12](../../../wiki/principles/domain.md)).
Run the deterministic diagnostic on the centered data:

```
python3 scripts/diagnostics/feature_separability.py <centered.csv> --profile <profile.json>
```

It windows each class, computes the platform's time-domain catalogue per axis, ranks by multiclass
separability (ANOVA F) and per-class one-vs-rest, flags **magnitude-blind class pairs** (best *magnitude-only*
Cohen's-d ≲ 1 ⇒ a **direction** problem, not energy), gates Skewness/Kurtosis on the storage dtype, and
prints the recommended enable-set. ([`windowed_feature_distribution_comparison.py`](../../../scripts/diagnostics/windowed_feature_distribution_comparison.py)
remains for train-vs-test distribution shift.) **Name every feature in full, exactly as the platform UI
shows it — no abbreviations** (e.g. "Linear Regression Slope", never "LR_SLOPE"; "Standard Deviation", never
"STD"). Map the evidence to platform families and recommend:

- **Energy** — **Standard Deviation, Root Mean Square, Range, Mean Absolute Deviation, Absolute Mean**. Rest
  vs active, high- vs low-energy gestures.
- **Direction / signed level** — **Mean, Min, Max, Linear Regression Slope, Linear Regression Intercept,
  Percentage of Signal over Zero, Percentage of Signal over Mean**. The only features encoding signed
  asymmetry (direction); **required for mirror/opposite classes** (left/right, up/down, clockwise/counter-clockwise)
  — magnitude features are direction-blind. **Linear Regression Slope/Intercept** are also orientation-invariant
  (survive per-class axis-sign flips across sessions) ([domain P-06](../../../wiki/principles/domain.md)). For a
  *dead* directional class, present this as part of a bundle (capacity + sharper data) and run the dead-class
  ceiling check first (**diagnose-data**) so the fix isn't over-promised.
- **Impulse/shape** — **Crest Factor, Hjorth Mobility, Hjorth Complexity**. Sharp/impulsive classes (taps)
  that energy features miss.

**Hold-backs (current defaults):**

- **INT16 input ⇒ do not recommend Skewness or Kurtosis** (higher moments are unstable on integers; revisit for FLOAT32).
- **Frequency-domain (FFT) features** need a power-of-2 window in 128–2048 and are incompatible with
  sub-windowing / the raw-data option ([signal-processing](../../../wiki/architecture/platform-signal-processing.md));
  don't switch windows for them unless time-domain separability is insufficient.
- **Don't enable feature-selection in the first experiment** — train the advised set, **test in real
  conditions**, then re-run with feature-selection on only if you must shrink the model. The platform's
  auto-pruning drops constant / perfectly-correlated / low-importance features
  ([feature page](../../../wiki/architecture/platform-feature-extraction.md)); fewer enabled features ⇒
  smaller model, but prune by *measured* importance, not by guessing up front.

**Windowing shifts:** training shift = window (no overlap); **inference shift = 50–70% overlap** (shift ≈
30–50% of the window), tuned to gesture duration/variability ([domain P-02](../../../wiki/principles/domain.md)).

## Reply
Plain language, concrete ("left and right collapse because the direction features are off — enable Linear
Regression Slope and Linear Regression Intercept on these axes; your taps also need sharper motion, not just a
feature change"). **Always use full platform feature names, never abbreviations.** Cite the feature/signal
pages. Frame Cohen's-d numbers as indicative. Hand off to **collection-advice** when the real fix is better
data, or **diagnose-data** for the full triage.

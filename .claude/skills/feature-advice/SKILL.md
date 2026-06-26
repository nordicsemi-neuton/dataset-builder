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

## 3. The high-value recommendations

- **Direction confusion / a dead directional class** → enable **LR_SLOPE / LR_INTERCEPT**: they are the only
  features encoding signed asymmetry (direction) and they are orientation-invariant; without them opposite
  gestures sit on top of each other ([domain P-06](../../../wiki/principles/domain.md),
  [feature page](../../../wiki/architecture/platform-feature-extraction.md)). Present this as part of a
  bundle (capacity + sharper data) and run the dead-class ceiling check first (**diagnose-data**) so the fix
  isn't over-promised.
- **Frequency-domain (FFT) features** are only worth enabling with a power-of-2 window in 128–2048, and they
  are incompatible with sub-windowing and the raw-data option ([signal-processing](../../../wiki/architecture/platform-signal-processing.md)).
- **Separability as an indicator, not a verdict:** [`windowed_feature_distribution_comparison.py`](../../../scripts/diagnostics/windowed_feature_distribution_comparison.py)
  gives Cohen's-d between classes/test — use it as indicative (there is no documented pass/fail cutoff).
- **Model too big from too many features:** the platform's auto-pruning removes constant features, perfectly
  correlated ones, and those below an importance floor; you can disable feature selection to keep a feature
  you know is useful ([feature page](../../../wiki/architecture/platform-feature-extraction.md)). Fewer
  enabled features ⇒ smaller model.

## Reply
Plain language, concrete ("left and right collapse because the direction features are off — enable LR Slope
and LR Intercept on these axes; your taps also need sharper motion, not just a feature change"). Cite the
feature/signal pages. Frame Cohen's-d numbers as indicative. Hand off to **collection-advice** when the real
fix is better data, or **diagnose-data** for the full triage.

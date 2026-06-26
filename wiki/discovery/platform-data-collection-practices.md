---
type: discovery
status: active
updated: 2026-06-25
sources:
  - ../../raw/platform-docs/2026-06-25-get-started-1-collection-labeling.md
  - ../../raw/platform-docs/2026-06-25-get-started-2-cleaning-combining-preprocessing.md
tags: [platform, data-collection, labeling, segmentation, cleaning, gesture, best-practices]
---

# platform — Data collection, labeling & cleaning practices

Domain guidance from the platform's gesture-recognition walkthrough (Nordic Thingy:53 / nRF5340). These are **best practices and a worked example**, not always hard rules — but they shape what good inertial input looks like and inform the data-builder's analysis/advice. Hard rules live in [dataset requirements](../architecture/platform-dataset-requirements.md) and [signal processing](../architecture/platform-signal-processing.md).

## How much data (PoC guidance)

- "The most important part of any machine-learning model is correctly labeled data."
- **PoC:** ~**3–5 minutes per gesture/class**, from **1–5 unique individuals**. Production needs much more variability — **more unique users ⇒ better generalization**.
- Demo dataset: **8 minutes total** (~2 min per motion) at **100 Hz**.

## Recording (reference setup)

- Capture via **nRF Connect for Desktop → Serial Terminal**; **Baud 115200**; clear console before connecting; **Write to File** → CSV after each gesture.
- Buffer caveat: at 100 Hz a 100,000-line buffer ≈ **1000 s** before overwrite — adjust buffering to your rate/session length.
- Per-recording technique: hold still 3–5 s at start; perform gesture 1–2 s; ~1 s pause between repetitions; **vary speed, orientation, intensity**.

## Labeling

- After collecting one class per file, add a **`class` column** with a **constant integer** for that class; name sensor columns clearly. Demo names: `acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z` (+ `class`).
- **Classes must start at `0`** and be **contiguous** (e.g. swipe=0, rotate=1, tap=2). **Save the encoding dictionary.** Demo encoding: IDLE=0, UNKNOWN=1, swipe-right=2, swipe-left=3, double-knock=4, double-thumb-tap=5, rotation-CW=6, rotation-CCW=7.
- Include an **idle/no-gesture class and random movements** to reduce false detections.

## Segmentation (non-continuous gestures)

- Gestures split into **continuous** (running, swimming) and **non-continuous** (swipe, jump — have a start/finish).
- Non-continuous gestures need **segmentation**: cut raw data into samples with the **gesture peak in the middle** of the feature-extraction window. Pick the longest-gesture timeframe (e.g. 1 s) → at the sampling rate (e.g. 100 Hz) that defines the window.
- Nordic provides a **signal-centering script**: https://github.com/nordicsemi-neuton/segment-center-signal (automates segmentation given the longest-gesture timeframe).

## Cleaning

- Remove **idle/incorrect records** from the start/end of a session (hardware setup). Good practice: **delete the first and last few seconds**. Plot a single axis to spot and remove bad samples. The centering script also does this.

## Combining files

One-dataset-per-model ⇒ concatenate per-class CSVs before upload (PowerShell `Get-Content … | Set-Content`, or `cat … > dataset.csv`). See the header-duplication caveat in [dataset requirements](../architecture/platform-dataset-requirements.md).

## Worked example (numbers, for reference)

100 Hz → 100 rows/s; ~1 s gesture → window **99 records**; features per axis = **16** → **96 features/sample** over 6 axes; sliding-shift = window ⇒ non-overlapping 1-s samples; inference sliding-shift 33 ⇒ ~3 inferences/s. Full detail: [signal processing](../architecture/platform-signal-processing.md), [feature extraction](../architecture/platform-feature-extraction.md).

## Observed in practice: production & class-specific collection

From field experience:

- **Production needs many users, not one.** A PoC may be one or a few people; for production, target **5–10+ users** with varied hand sizes / motion styles, **≥10 minutes per user** across all classes. Single-user training generalizes poorly to new users.
- **Always include an idle class and an "unknown" / "none-of-the-above" class** (populate "unknown" with the user's real non-target activities). Without them, every input is forced into a gesture → constant false detections. Canonical loop: deploy → observe false triggers → add their patterns to "unknown" → retrain. See [domain P-10](../principles/domain.md).
- **Class-specific tips when a class is weak:** for directional gestures, exaggerate the contrast (e.g. clearer left-vs-right motion) and enable the [direction features](../architecture/platform-feature-extraction.md); for impulse gestures (tap), collect *sharper* motions — a soft tap whose magnitude barely exceeds idle is hard to separate; for knock-style gestures, keep them consistent; for idle, capture **multiple device orientations** so the model doesn't tie "idle" to one pose.
- **Watch for firmware artifacts during collection vs deployment.** If the IMU full-scale-range register or firmware changes between training-data collection and deployment, gyro/accel saturation rates can shift and silently move the data out of the trained feature regime — keep them consistent, and see the [preprocessing-parity rule](../principles/domain.md). The diagnostic + worked example: [case patterns](../synthesis/support-case-patterns.md).

> Capture gap: the `Preparing raw dataset`, `Requirements`, and `Gesture execution` subsections of the getting-started page did not fully load (firmware-setup oriented). Re-capture from a rendered browser if firmware/prerequisite detail is needed: [raw](../../raw/platform-docs/2026-06-25-get-started-1-collection-labeling.md).

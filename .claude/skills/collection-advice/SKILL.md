---
name: collection-advice
description: >-
  Advise how much inertial-sensor data to collect and how to record, label, and clean it for a Nordic
  Edge AI Lab model — including tricks to fix a weak class at the source. Use when the user asks "how much
  data do I need?", "how should I record gestures?", "how do I label my classes?", "my class is weak, how
  do I collect better data?", "how do I clean my recordings?", or "how do I stop false detections?".
---

# Advise on data collection, labeling & cleaning

Advice only (no file is changed). Pair the platform's documented guidance with hard-won experience, and
**always tag which is which** — a platform recommendation is not a law, and an experiential target is not a
platform rule. Sources: [data-collection practices](../../../wiki/discovery/platform-data-collection-practices.md),
[domain principles](../../../wiki/principles/domain.md), [case patterns](../../../wiki/synthesis/support-case-patterns.md),
and the hard contract in [_shared/platform-contract.md](../_shared/platform-contract.md).

## What to cover

**How much (PLATFORM guidance vs EXPERIENTIAL targets):** state the platform's PoC guidance and the
experiential production targets from [the collection-practices page](../../../wiki/discovery/platform-data-collection-practices.md)
and [domain principles](../../../wiki/principles/domain.md) — read them and quote the actual figures rather
than reciting from memory; label each figure as platform-guidance or experience.

**Recording technique:** include an **idle** class and an **"unknown" / none-of-the-above** class populated
with the user's real non-target activities — without a catch-all, every input is forced into a gesture and
you get constant false detections ([domain P-10](../../../wiki/principles/domain.md)). Vary speed,
orientation, and intensity. One class per file, then combine (the **prep-dataset** skill does the combine).

**Labeling & encoding:** target contiguous from 0, ≥2 classes, ≥20 samples each
([contract](../_shared/platform-contract.md)); keep recordings time-ordered, one row per sample.

**Cleaning:** drop the first/last few seconds of each recording (hardware-setup noise).

**Weak-class tricks (tie to the symptom):**
- direction class confused (left/right) → exaggerate the motion AND enable LR_SLOPE/LR_INTERCEPT
  ([domain P-06](../../../wiki/principles/domain.md)); see **feature-advice**.
- a class disappears at windowing → record longer continuous runs per gesture, at least as long as the
  window ([domain P-01](../../../wiki/principles/domain.md)).
- false triggers in normal use → grow the "unknown" class with the activities that misfire, then retrain
  ([domain P-10](../../../wiki/principles/domain.md)).

## Reply
Plain language, organised by the user's actual question. Each number tagged platform-guidance vs
experience. If the real fix is in the data already collected, hand off to **diagnose-data**; if it's about
feature settings, hand off to **feature-advice**.

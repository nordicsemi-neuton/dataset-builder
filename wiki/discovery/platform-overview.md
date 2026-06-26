---
type: discovery
status: active
updated: 2026-06-25
sources:
  - ../../raw/platform-docs/2026-06-25-welcome-overview-domains.md
  - ../../raw/platform-docs/2026-06-25-overview-neuton-axon-workflow.md
  - ../../raw/platform-docs/2026-06-25-ready-to-use-models.md
  - ../../raw/platform-docs/2026-06-25-registration-and-login.md
  - ../../raw/platform-docs/2026-06-25-pipeline-inference-on-desktop.md
  - ../../raw/platform-docs/2026-06-25-pipeline-data-preprocessing.md
  - ../../raw/platform-docs/2026-06-25-pipeline-model-settings.md
  - ../../raw/platform-docs/2026-06-25-get-started-1-collection-labeling.md
  - ../../raw/platform-docs/2026-06-25-get-started-3-training-deployment.md
tags: [platform, overview, neuton, axon, nordic, product]
---

# platform — Nordic Edge AI Lab (what it is)

**Nordic Edge AI Lab** is an automated, **no-code** platform for building **extremely compact TinyML models** and embedding them across **Nordic Semiconductor wireless connectivity SoCs**. No data-science or embedded-engineering expertise is required. URL: <https://ai.lab.nordicsemi.com> (free account required).

This is the ML platform our `data-builder` prepares data for. The hard input rules live in [`architecture/platform-dataset-requirements`](../architecture/platform-dataset-requirements.md); this page is the product context.

## Two technologies

| | **Neuton** | **Axon NPU** |
|---|---|---|
| What | Patented NN framework, fully automatic, ultra-compact models | LiteRT models with standard deep-learning architectures, more flexibility |
| Task types | Regression, Binary/Multiclass Classification, **Anomaly Detection** | Regression, Binary/Multiclass Classification (+ a separate data-free **Wake Word** pipeline — see below) |
| Architecture | Auto, neuron-by-neuron (no manual design) → [neuton framework](platform-neuton-framework.md) | User-customizable layers / presets; compare runs |
| Input data type | INT8 / INT16 / FLOAT32 | **FLOAT32 only** |
| Bit depth / target HW | 8/16/32-bit; Cortex-M0/M4/M33 | locked 32-bit float; target = Axon NPU |

A **data-free wake word pipeline** exists **only for Axon NPU** — it generates a wake-word model **without any uploaded dataset**. For every other task type, **a CSV dataset upload is required**. See [task types](platform-task-types.md).

## Key claims & constraints

- Models are **up to 10× smaller** than other frameworks, built **without compression techniques**, deployable on the smallest MCUs with fast inference.
- **Exclusivity:** models built with Edge AI Lab are **available only for Nordic wireless SoCs** (a premium offering for Nordic's customer base).
- Input is always a **CSV dataset of independent features + a target variable** (except data-free wake word).
- **Ready-to-use Models:** a growing library of **pre-trained** models to download and deploy directly — prototype without collecting data or training. Useful to evaluate on-device inference before investing in a dataset.

## Supported tasks & application domains

TinyML tasks: gesture recognition, wake-word detection, vital-sign determination, human-machine interfaces, human-activity recognition, machine-fault classification, asset tracking/monitoring, and **any sensor-based time-series task** (regression / classification / anomaly detection).

Domains: wearables, healthcare (HR/SpO₂/ECG/PPG), environmental monitoring, energy management, logistics/transport, agriculture, smart home, predictive maintenance, smart cities, retail, automotive.

→ This confirms our target domain: **inertial time series from wearables** (accelerometer/gyroscope) for activity/gesture/state recognition.

## Access & support

- **Registration:** manual (first/last name, company, work email, password) or **Continue with Google**; email verification required. Password recovery via **Forgot password?** (also lets Google users set a password).
- **Support:** in-platform **AI chatbot** + Nordic **DevZone**.
- **Reference hardware** in the docs' walkthrough: **Nordic Thingy:53 (nRF5340)**, captured over Bluetooth via **nRF Connect for Desktop** (Serial Terminal). See [data-collection knowledge](platform-task-types.md) and the raw getting-started capture.

## Related

[Neuton framework](platform-neuton-framework.md) · [task types & anomaly/wake-word](platform-task-types.md) · architecture: [pipeline](../architecture/platform-data-pipeline.md), [dataset requirements](../architecture/platform-dataset-requirements.md).

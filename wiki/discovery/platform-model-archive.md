---
type: discovery
status: active
updated: 2026-06-25
sources:
  - Field experience (practitioner knowledge; no external source document).
  - ../../scripts/diagnostics/feature_mask_decoder.py
tags: [platform, model-archive, inference, feature-mask, firmware, discovery]
---

# platform — The downloaded solution archive (what the platform returns)

After training, the platform produces a **ZIP archive** of the solution. Knowing its layout matters for support: the feature mask, input-scaling clamps, and runner predictions are where most "why is my model behaving like this" answers live. Observed from common solution archives (field experience); the runner CLI itself is documented in [deployment/inference](../architecture/platform-deployment-inference.md).

## Archive layout

```
<solution>/
├── nrf_edgeai_generated/        ← model-specific generated C (copy into your firmware src/)
│   ├── nrf_edgeai_user_model.c  ← model definition: FEATURES_EXTRACTION_MASK, input scaling MIN/MAX, neuron/weight counts, window/shift, feature count
│   ├── nrf_edgeai_user_model.h  ← model interface
│   ├── nrf_edgeai_user_types.h  ← input/output data types
│   ├── nrf_edgeai_user_model_axon.h  ← only if Axon/NPU mode
│   └── prj_example.conf         ← example Zephyr prj.conf (enables Edge AI / Axon)
├── nrf_edgeai/                  ← include/ lib/ source/ for the inference runtime
└── artifacts/
    └── inference_runner/        ← desktop runner executables (linux/win/mac) + README
```

The **generated code is model-specific only** — the actual inference engine comes from the separate **Edge AI Add-on** (`nrf_edgeai` / `nrf_axon` libraries, installed via nRF Connect SDK). Firmware integration, drivers, BLE/HID, sample apps, and on-device thresholding all live in the Add-on docs, not the Edge AI Lab docs.

## `nrf_edgeai_user_model.c` — the support-relevant fields

- **`FEATURES_EXTRACTION_MASK[]`** — one `uint64_t` per input axis. ⚠️ The exact bit layout (and that the time-domain mask occupies the upper 32 bits, ordered per the `nrf_edgeai_dsp_pipeline_types.h` feature enum) is **reverse-engineered from sample archives + the decoder script, not stated in platform docs** — verify the enum ordering against that header if you have it. Decode it with [`feature_mask_decoder.py`](../../scripts/diagnostics/feature_mask_decoder.py) to see which features the model uses. **First thing to check** for direction-confusion / dead-class tickets — see [domain P-06](../principles/domain.md) (`LR_SLOPE`/`LR_INTERCEPT` are the only signed-asymmetry features).
- **Input scaling MIN/MAX per axis** — the model's input clamp. For gyro this doubles as the **saturation bound**; test data that hits it (sample-and-hold spikes) inflates STD-type features — see [case patterns](../synthesis/support-case-patterns.md).
- **Neuron / weight counts, window, sliding shift, extracted-feature count, input type, bit depth** — model capacity and preprocessing config at a glance (a tiny model on many confusable classes is a common dead-class cause).

## On-device inference API (4 calls)

`nrf_edgeai_user_model()` → get model ptr · `nrf_edgeai_init()` (once, first) · `nrf_edgeai_feed_inputs()` (buffers internally until a full window is ready) · `nrf_edgeai_run_inference()`. Feed raw features **in the same order and type as the training data** ([dataset requirements](../architecture/platform-dataset-requirements.md)). Apply [recommended postprocessing](../principles/domain.md) to the output probabilities.

## Desktop runner predictions format

`metrics`/`inference` with `-s` writes a CSV: a `target` column (when present) plus one **`Probability of 0` … `Probability of N`** column per class. This is the input to [`postprocessing_pipelines.py`](../../scripts/postprocessing/postprocessing_pipelines.py) (ceiling check + pipeline comparison). Runner CLI flags and defaults: [deployment/inference](../architecture/platform-deployment-inference.md).

## Note

Neuton runs on the CPU; Axon runs on the NPU (same `nrf_edgeai` API, different build/link). The Axon NPU is reported to accelerate inference substantially over CPU. Detail beyond data prep is Add-on territory.

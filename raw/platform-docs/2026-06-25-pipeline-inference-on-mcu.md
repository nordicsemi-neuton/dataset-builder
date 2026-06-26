# RAW SOURCE — Pipeline: Run Inference on MCU

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_mcu.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-inference-on-mcu fetch_ok=True
> - pass=p2 slug=inference-on-mcu fetch_ok=False anchors=1/2

---

<!-- source segment: pass=p1 slug=pipeline-inference-on-mcu fetch_ok=True -->

# Run Inference on MCU

> CAPTURE NOTE (not part of the source page): The target page is rendered client-side by the docs.nordicsemi.com documentation portal application. Across three WebFetch attempts, the fetcher could reliably retrieve only the page title, a single introductory statement, and the page's subsection/navigation headings. It did NOT return the full rendered body text of the subsections. The verbatim content that WAS reliably retrieved is reproduced below. The subsection bodies could not be retrieved and are deliberately NOT reconstructed or paraphrased here, to avoid fabricating platform requirements. A re-capture from a fully rendered DOM (or the documentation export) is recommended to obtain the complete "Inference engine" and "Key features" subsection text.

## Introductory statement (verbatim, as retrieved)

"This page describes the inference engine and its key features for running trained models on target hardware. For guidance on integrating the model into the MCU, as well as code samples, refer to the Edge AI Add-on."

## Subsections present on the page (headings only — body text not retrieved)

- Inference engine
- Key features

> The body text under "Inference engine" and "Key features" was not returned by the fetch (the fetcher returned only the headings as part of the page's navigation/structure). No verbatim content for these subsections is available from this capture, and none has been invented.

## Cross-references mentioned on the page

- Edge AI Add-on — referenced for guidance on integrating the model into the MCU and for code samples.

---

<!-- source segment: pass=p2 slug=inference-on-mcu fetch_ok=False anchors=1/2 -->

# Run Inference on MCU: inference engine, key features

## Inference engine

> [not retrieved]

## Key features

The inference engine provides the following capabilities:

* **TinyML optimization** — Supports deployment of ultra-small models on edge devices with limited computing power, such as microcontrollers and IoT devices.
* **Efficiency** — Enables fast execution with low power consumption, suitable for real-time and resource-constrained applications.
* **Cross-platform support** — Works with different hardware platforms (for example, Cortex-M0, Cortex-M4, Cortex-M33, and Axon NPU) depending on the target device.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- The inference engine supports cross-platform deployment across different hardware platforms, for example Cortex-M0, Cortex-M4, Cortex-M33, and Axon NPU, depending on the target device.
- TinyML optimization supports deployment of ultra-small models on edge devices with limited computing power, such as microcontrollers and IoT devices.
- The inference engine enables fast execution with low power consumption, suitable for real-time and resource-constrained applications.

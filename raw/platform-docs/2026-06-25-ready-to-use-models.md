# RAW SOURCE — Ready-to-use Models

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/ready_to_use_models.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=ready-to-use-models fetch_ok=True anchors=3/3

---

<!-- source segment: pass=p2 slug=ready-to-use-models fetch_ok=True anchors=3/3 -->

# Ready-to-use Models: prerequisites, exploring library, working with model

## Prerequisites

To successfully run any of these models on your device, you will need two main components:

* **Model Archive** — The compiled model file (the specific compiled model file you choose and download).
* **Inference Runtime Libraries** — You must have the "Edge AI Add-on" installed to execute the models on your hardware.

## Exploring the Model Library

The Nordic Edge AI Lab catalog encompasses several key application domains:

The platform provides **"Wake Words — Instantly activate your device using the standard 'Okay Nordic' wake word."** Additionally, models support keyword spotting for devices like smart TVs and smartwatches, drawing from Google Speech Commands datasets.

Environmental sound recognition capabilities include **"Acoustic Event Detection — Context-aware audio models capable of recognizing specific environmental sounds, such as dog barking, cat's meowing, baby crying, snoring, and coughing."**

Motion-based applications feature **"Gesture Recognition — Motion-based control models, featuring remote control."**

The documentation provides organized pathways through prerequisites, model exploration workflows, and practical implementation guidance for working with the available models in the library.

## Working with the Model

To start working with a ready-to-use model:

1. Install the Edge AI Add-on and set up the application.
2. Browse the model catalog and download the archive matching your use case and target hardware.
3. Extract the archive and review the included `README.md` for configuration details.
4. Copy the model into the application folder, replacing the default one.
5. Update your application's source code with the parameters from the `README.md`, then build and flash to your device.
6. Run inference and evaluate the model's performance to determine whether it meets your requirements.

If none of the available models fit your use case, you can train a custom model using your own dataset. See Model creating pipeline for guidance.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- To run any of these models on your device, two main components are required: a Model Archive (the compiled model file you choose and download) and Inference Runtime Libraries.
- You must have the 'Edge AI Add-on' installed to execute the models on your hardware.
- Wake Words models instantly activate your device using the standard 'Okay Nordic' wake word.
- Keyword spotting models for devices like smart TVs and smartwatches draw from Google Speech Commands datasets.
- Acoustic Event Detection models are context-aware audio models capable of recognizing specific environmental sounds, such as dog barking, cat's meowing, baby crying, snoring, and coughing.
- Gesture Recognition models are motion-based control models, featuring remote control.
- To work with a ready-to-use model: install the Edge AI Add-on and set up the application, browse the model catalog and download the archive matching your use case and target hardware, extract the archive and review the included README.md for configuration details, copy the model into the application folder replacing the default one, update your application's source code with the parameters from the README.md then build and flash to your device, and run inference and evaluate the model's performance.
- If none of the available models fit your use case, you can train a custom model using your own dataset (see Model creating pipeline).

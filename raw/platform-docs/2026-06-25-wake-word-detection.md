# RAW SOURCE — Wake Word Detection

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/wake_word.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=wake-word-detection fetch_ok=True anchors=6/7

---

<!-- source segment: pass=p2 slug=wake-word-detection fetch_ok=True anchors=6/7 -->

# Wake Word Detection: overview, requirements & best practices, training, pre-built model, results, settings, on-device

## Overview

Wake word detection is a specialized speech recognition task that identifies specific keywords or phrases, known as wake words, within audio streams. These wake words serve as triggers for voice-activated systems, allowing users to interact with devices hands-free. Common examples include "Hey Siri," "OK Google," and "Alexa."

Wake word detection is available exclusively for **Axon NPU** at the solution creation stage. It is designed to be efficient and accurate, enabling real-time detection of wake words while minimizing false positives. This makes it suitable for applications such as wearables, smart speakers, voice assistants, and other IoT devices that rely on voice commands.

The workflow for creating a wake word detection model is straightforward. Enter the word you want the system to recognize, and the platform handles the rest automatically. The full process typically takes around one hour.

**Note**

If you stop the solution while it is in progress, all current progress is lost and the process must be restarted.

## Requirements and best practices

When defining a wake word for your device, adhere to these specifications:

**Character Requirements:**
- Use only English characters
- Minimum length is 4 characters
- Maximum length is 30 characters

**Composition Guidelines:**
- Use 1 to 3 words

**Selection Best Practices:**
- Avoid common or frequently used phrases
- Choose words that are clear and easy to pronounce
- In case the wake word does not sound as expected, adjust capitalization and spacing

These guidelines ensure your wake word functions reliably and performs as intended within the Nordic Edge AI Lab system.

## Training custom wake word

Enter or submit your wake word, play the sample and confirm that it sounds correct. If not, adjust it according to the recommendations. Once confirmed, click **Start** to begin training.

## Using the pre-built model (Okay Nordic)

Evaluate the ready-to-use model to understand how it works. You can explore fine-tuning options, and download it for inference on your device. Once ready, click **Open results**.

(Followed by an image labeled "Wake Word Configuration (Okay Nordic)".)

## Results

After entering the wake word and starting the process, the platform automatically redirects you to the results page. From here, you can:

* Monitor training progress.
* Review the estimated memory footprint.
* Download the model.
* Test the model in your browser.

## Detection settings

The following parameters allow you to fine-tune detection behavior during live testing:

- **Above threshold** — Minimum confidence score required to treat a prediction as positive. Higher values reduce false activations but make detection more strict.
- **During the period** (seconds) — Defines the time window during which predictions must remain above the threshold to confirm detection.

The interface also displays the equivalent number of consecutive predictions.

**Note:** Changes made here are not automatically applied to the downloaded model. You must configure the same parameters manually in your firmware using the Edge AI add-on.

## Inference on device

> [not retrieved]

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Wake word detection is available exclusively for Axon NPU at the solution creation stage.
- The full wake word model creation process typically takes around one hour.
- If you stop the solution while it is in progress, all current progress is lost and the process must be restarted.
- Wake word definition: use only English characters.
- Wake word minimum length is 4 characters.
- Wake word maximum length is 30 characters.
- Wake word composition: use 1 to 3 words.
- Detection setting 'Above threshold' is the minimum confidence score required to treat a prediction as positive; higher values reduce false activations but make detection more strict.
- Detection setting 'During the period' (seconds) defines the time window during which predictions must remain above the threshold to confirm detection.
- Changes made in detection settings are not automatically applied to the downloaded model; you must configure the same parameters manually in your firmware using the Edge AI add-on.

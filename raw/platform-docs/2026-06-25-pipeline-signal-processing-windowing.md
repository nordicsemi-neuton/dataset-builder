# RAW SOURCE — Pipeline: Signal Processing — windowing, sliding shift, SRAM, sub-windowing

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/signal_processing.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=signal-processing-windowing fetch_ok=True anchors=6/6

---

<!-- source segment: pass=p2 slug=signal-processing-windowing fetch_ok=True anchors=6/6 -->

# Signal Processing: guided setup, windowing, sliding shift, SRAM, raw data, sub-windowing

## Guided Setup

The Nordic Edge AI Lab provides an automated configuration wizard for signal processing that guides users through a series of questions to automatically configure windowing parameters and feature extraction settings.

### Key Features

The wizard is designed as "the fastest way to get started if you are new to signal processing." It walks through a questionary format to streamline the setup process.

### Default Settings

When signal processing is enabled, the system applies specific defaults: "the Normalization type is set to AutoSelect by default. Features created during Feature Extraction are normalized within their own scale. Raw sensor data is normalized separately for each variable and axis."

This approach ensures that both extracted features and raw sensor measurements are appropriately scaled according to their individual ranges and characteristics.

## Windowing

Windowing transforms sequential signal data into vectors suitable for feature extraction. The **Window size** parameter specifies how many samples process the training dataset using a static window approach.

### Key Requirements

The window size must remain consistent across all events in your training dataset, regardless of event duration. Training and validation datasets must use identical window sizes before platform upload. Apply upsampling or downsampling as needed to align data.

The platform groups training data by the specified sample count and calculates variables from these groups.

**Size constraints:**
- Minimum: 10 samples (required for accurate feature calculation)
- Maximum: 1,000 samples (designed for TinyML applications)

**Note:** When using a Session ID column, sessions smaller than the window size get removed automatically.

### Specification Methods

Three approaches define window size:

1. **Time interval** — Enter milliseconds (ms) and frequency in Hertz (Hz). Sensors with different frequencies require prior downsampling or upsampling to a single frequency.

2. **Number of Rows (Samples)** — Set rows based on domain knowledge. Example: 100 Hz sampling with one-second maximum activity duration suggests 100 rows.

3. **Auto Determination** — Platform automatically selects optimal window size via built-in algorithm. Optionally specify minimum/maximum boundaries and sliding shift percentage (for classification and regression).

### Frequency Domain Features

For frequency domain features, window size must be a power of 2, ranging between 128 and 2048 samples. The platform alerts you if settings don't match these requirements.

## Sliding Shift

The **Sliding shift** setting controls window overlap by defining how many samples the window moves forward to form the next segment.

### Key Characteristics

- If the shift equals the window size, there is no overlap between consecutive windows.
- If the shift is smaller than the window size, consecutive windows share overlapping samples.
- The shift value cannot exceed the window size.
- Sliding shift is available for both training and inference.

## Estimated SRAM Usage

The documentation states: "The platform estimates SRAM usage based on your selected window size and features. Actual usage will be determined after model training and compilation."

Key points about SRAM estimation:

- Calculation is based on window size and feature selections
- Final values emerge only after model training and compilation completes
- For automatic window determination, the SRAM estimate becomes visible only following the training process

The page includes a visual diagram illustrating how the SRAM usage estimation appears in the platform interface, though the specific technical thresholds and memory calculations are not detailed in this section.

## Raw Data Option

You can include raw sensor data in your model by enabling the **Raw data** option, which is disabled by default. When enabled, raw data from all variables and axes in feature extraction is used for training. This option is not available for Axon technology (LiteRT framework).

Raw data cannot be used when:

*   Sliding shift does not equal window size.
*   Any frequency domain feature is enabled.
*   Window auto-determination is enabled.

The platform displays hints and disables the raw data option as needed.

## Sub-windowing

Sub-windowing (or sub-sequence analysis) splits a signal into smaller segments to better capture local peaks, dips, and patterns. Instead of analyzing the entire signal as one long sequence, the platform processes it in smaller chunks and extracts more detailed features from each one. This is especially useful for gesture and activity recognition.

To enable it, select the **Sub-windowing** option.

You can choose between 2 and 10 sub-windows, and each sub-window must contain at least 10 samples. Make sure that the window size in samples divided by the number of sub-windows is 10 or more. If it is not, adjust the window size or the number of sub-windows.

When sub-windowing is enabled:

* You can still add full-window features, which are calculated over the entire window.
* Frequency domain features are disabled.
* Feature selection is automatically enabled, but you can turn it off if needed.
* Lag features (raw data option) are not compatible with sub-windowing. You must disable sub-windowing to use lag features.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- When signal processing is enabled, the Normalization type is set to AutoSelect by default.
- Features created during Feature Extraction are normalized within their own scale.
- Raw sensor data is normalized separately for each variable and axis.
- The window size must remain consistent across all events in the training dataset, regardless of event duration.
- Training and validation datasets must use identical window sizes before platform upload.
- Window size minimum is 10 samples (required for accurate feature calculation).
- Window size maximum is 1,000 samples (designed for TinyML applications).
- When using a Session ID column, sessions smaller than the window size are removed automatically.
- Window size can be specified by time interval by entering milliseconds (ms) and frequency in Hertz (Hz).
- Sensors with different frequencies require prior downsampling or upsampling to a single frequency.
- Example: 100 Hz sampling with one-second maximum activity duration suggests 100 rows.
- Auto Determination optionally allows specifying minimum/maximum boundaries and sliding shift percentage (for classification and regression).
- For frequency domain features, window size must be a power of 2, ranging between 128 and 2048 samples.
- Sliding shift defines how many samples the window moves forward to form the next segment.
- If the sliding shift equals the window size, there is no overlap between consecutive windows.
- If the sliding shift is smaller than the window size, consecutive windows share overlapping samples.
- The sliding shift value cannot exceed the window size.
- Sliding shift is available for both training and inference.
- The platform estimates SRAM usage based on selected window size and features; actual usage is determined after model training and compilation.
- For automatic window determination, the SRAM estimate becomes visible only after the training process.
- The Raw data option is disabled by default.
- When the Raw data option is enabled, raw data from all variables and axes in feature extraction is used for training.
- The Raw data option is not available for Axon technology (LiteRT framework).
- Raw data cannot be used when the sliding shift does not equal the window size.
- Raw data cannot be used when any frequency domain feature is enabled.
- Raw data cannot be used when window auto-determination is enabled.
- Sub-windowing allows choosing between 2 and 10 sub-windows.
- Each sub-window must contain at least 10 samples.
- The window size in samples divided by the number of sub-windows must be 10 or more.
- When sub-windowing is enabled, frequency domain features are disabled.
- When sub-windowing is enabled, feature selection is automatically enabled but can be turned off.
- Lag features (raw data option) are not compatible with sub-windowing; sub-windowing must be disabled to use lag features.
- When sub-windowing is enabled, full-window features can still be added and are calculated over the entire window.

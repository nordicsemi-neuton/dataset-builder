# RAW SOURCE — Pipeline: Signal Processing — feature extraction & selection

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/signal_processing.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=signal-processing-features fetch_ok=True anchors=12/13

---

<!-- source segment: pass=p2 slug=signal-processing-features fetch_ok=True anchors=12/13 -->

# Signal Processing: feature extraction (time/statistical/frequency domain), feature selection

## Feature Extraction

When the window size is configured, the platform automatically **extracts selected features** for each column (variable or axis). These same features are then extracted during inference.

You have several options for managing features:
- Enable or disable individual features
- Use the **Edit** button for modifications
- Select all features at once with **Select All**
- Return to default settings with **restore defaults**
- Utilize the search bar to locate specific features quickly

The interface displays a feature extraction panel where you can view and configure all available features for your dataset processing.

## Time-domain features

> [not retrieved]
>
> (This anchor is a parent/intro that only states "The following time-domain features are available for extraction" and lists the sub-categories below — Statistical features, Regression features, Crossing-rate features, Signal shape and variation, Hjorth parameters, Peak-to-peak features. No standalone body text was returned after two attempts.)

## Statistical Features

| Feature | Description |
|---------|-------------|
| **Max** | Calculates the maximum value in the window. |
| **Min** | Calculates the minimum value in the window. |
| **Mean** | Calculates the arithmetic mean of the window. |
| **Range** | Measures amplitude variation by finding the difference between peak and trough values within a signal window. |
| **Absolute Mean** | Computes average signal magnitude independent of polarity, offering a computationally efficient energy estimate. |
| **Standard Deviation** | Quantifies the amount of variation or dispersion in a set of data points from their mean value, with applications in activity recognition, anomaly detection, and audio processing. |
| **Mean Absolute Deviation** | The average of the absolute differences between each data point and the mean of the dataset. |
| **Root Mean Square** | Calculates the root of the arithmetic mean of the squares of a set of numbers. |
| **Kurtosis** | Measures the combined weight of a distribution's tails relative to the center of the distribution. |
| **Skewness** | Measures the asymmetry of the distribution of a variable. |

These metrics support machine learning applications across domains including wearable sensor analysis, fault detection, and signal characterization.

## Regression Features

| Feature | Description |
|---------|-------------|
| Linear Regression Intercept | The value of the dependent variable (y) when all independent variables (x) are set to zero. |
| Linear Regression Slope | The change in the dependent variable (y) for every one-unit increase in the independent variable (x). |

## Crossing-rate features

| Feature | Description |
|---------|-------------|
| Zero-crossing Rate | Measures the number of times a signal changes its sign from positive to negative or vice versa, divided by the length of the frame. Represents signal frequency crossing the zero axis. |
| Mean-crossing Rate | Calculates the number of times the signal crosses the mean value within the window. |
| Threshold-crossing Rate | Measures the frequency at which a signal crosses a predefined threshold value within a given time window. |
| Positive Sigma Crossing Rate | Measures how frequently a signal exceeds a threshold defined as a multiple of the standard deviation (σ) above the mean. Helps identify significant amplitude deviations and repetitive patterns or anomalies in time-series data. |
| Negative Sigma Crossing Rate | Measures how frequently a signal falls below a threshold defined as a multiple of the standard deviation (σ) below the mean. Helps identify significant downward deviations and anomalies in time-series data. |

## Signal Shape and Variation

| Feature | Description |
|---------|-------------|
| Crest Factor | Calculates the ratio of a signal's peak amplitude to its root mean square (RMS) value. It is particularly useful for analyzing waveforms in: Electrical engineering; Vibration analysis; Audio processing. |
| Root Difference Square | Measures the square root of the mean squared difference between neighboring discrete points. It measures mean signal variation between neighboring points and can be used as a characteristic of the rate of change of a signal. |
| Average Magnitude Difference | A signal processing technique used for periodicity analysis in sensor signals. It is particularly useful in: Sensor-based systems where detecting periodic patterns is crucial; Speech analysis; Music signal processing. However, it may suffer from incorrect pitch detection in highly noisy conditions, which has led to the development of extended versions for improved performance. |
| Percentage of Signal over Mean | Calculates the ratio between the number of sensor signal values greater than the mean value in a window over the total window size. It is particularly useful in applications where relative changes in the signal are more important than absolute values, such as: Vibration analysis; Environmental monitoring; Process control systems. |
| Percentage of Signal over Zero | Calculates the ratio between the number of positive sensor signal values in a window over the total window size. In other words, it measures the fraction of time the signal was positive. |
| Percentage of Signal over Sigma | Calculates the ratio between the number of sensor signal values greater than the sigma value (mean + n standard deviations) in a window over the total window size. |
| Autocorrelation | Measures the correlation between a signal and a time-shifted version of itself, providing valuable insights into the signal's inherent patterns, periodicities, and statistical properties. |

## Hjorth Parameters

| Feature | Description |
|---------|-------------|
| **Hjorth Mobility** | Measures the mean frequency or the rate of change of a signal, indicating how fast the signal changes. It is defined as the square root of variance of the first derivative of the signal y(t) divided by variance of the signal y(t). |
| **Hjorth Complexity** | Measures the change in frequency, for example, how the shape of the signal evolves. The parameter compares the signal's similarity to a pure sine wave, where the value converges to 1 if the signal is more similar. |

### Applications

Both parameters see common use in tactile signal processing contexts. They enable detection of physical object properties like surface texture and material composition, as well as classification of touch modality through artificial robotic skin systems.

## Peak-to-Peak Features

### Global Peak to Peak of High Frequencies

Measures the maximum variation in amplitude of the high-frequency components across the entire signal. This feature extraction technique isolates and analyzes high-frequency signal components, commonly applied in image processing, audio analysis, and vibration monitoring. The metric quantifies the largest difference between maximum and minimum values within the high-frequency range.

### Global Peak to Peak of Low Frequencies

Measures the maximum variation in amplitude of the low-frequency components across an entire signal. This metric reveals the overall intensity and range of low-frequency content, proving particularly valuable in applications requiring understanding of low-frequency behavior, including vibration analysis, audio engineering, and industrial monitoring systems.

## Frequency-domain features

Frequency-domain features use Fast Fourier Transform (FFT) to calculate the frequency of peaks and their power. When enabled, the window size must be a power of 2 and between 128 and 2048 samples.

## Spectral Analysis

### Features and Applications

**Amplitude Spectrum**

Represents the magnitude of different frequency components present in a signal, offering insights into its spectral characteristics. Key applications include vibration analysis, signal classification, speech recognition, mechanical fault detection, gesture recognition with IMU data, structural health monitoring, and motor condition monitoring.

**Spectral Centroid**

Represents the center of mass of a spectrum and is closely associated with the perceived brightness of a signal. Used for detecting mechanical wear via vibration sensors, IMU-based motion pattern recognition, and structural health monitoring with accelerometers.

**Spectral Spread**

Measures the dispersion of the spectrum around its centroid, calculated as the average deviation of the spectrum from its spectral centroid. Applied in vibration pattern characterization, detecting structural looseness, and classifying gestures based on frequency content using IMU sensors.

**Spectral Crest**

Measures the peakiness or tonality of a signal's spectrum, calculated as the ratio of the maximum magnitude in the spectrum to the arithmetic mean. Useful for vibration-based fault detection, motor imbalance detection with IMU data, and impact detection for accelerometers or gyroscopes.

**Spectral RMS**

Measures the average energy of a signal in the frequency domain, providing valuable information about the spectral content and overall power of a signal. Applications include detecting abnormal vibration energy increases, monitoring load variations with IMU sensors, and activity classification in wearables.

## Dominant Frequency Features

| Feature | Description |
|---------|-------------|
| **Dominant Frequencies** | Identifies the most prominent frequency components within a signal's spectrum through frequency-domain analysis. Critical for biomedical signals (atrial fibrillation at 4–9 Hz), geophysical sensing via ground-penetrating radar, and fluid dynamics vortex analysis. |
| **Dominant Frequency Amplitudes** | Represents the amplitudes of the most prominent frequency components in a signal's spectrum, enabling efficient representation and analysis of complex waveforms. |
| **Dominant Frequency Mean Distance** | Quantifies the average separation between dominant frequency components in a signal or across signal segments. Applied to rotating machinery wear detection, EEG/ECG arrhythmia tracking, and wireless signal frequency drift monitoring. |
| **Dominant Frequency SNR** | Calculates the ratio of the power of the dominant frequency component to the power of the noise in a signal. Supports vibration analysis and anomaly detection. |
| **Dominant Frequency THD** | Calculates the total harmonic distortion by comparing the energy in harmonic frequencies to the fundamental (dominant) frequency. Used for RF sensor characterization, bearing fault detection, and ECG filter design. |

## Energy ratio features

| Feature | Description |
|---------|-------------|
| Low/High Frequency Energy Ratio | Compares the energy content of low-frequency components to high-frequency components within a signal. Applied in vibration monitoring, acoustic analysis, and fault detection. |
| Low/Mid Frequency Energy Ratio | Analyzes the distribution of energy between lower and mid-frequency bands of a signal, providing valuable insights into the spectral characteristics of audio, vibration, and electrical signals. Uses include vibration analysis for mechanical faults, power quality monitoring for voltage sags, and audio processing to distinguish speech from music. |
| Mid/High Frequency Energy Ratio | Analyzes the distribution of energy between mid-range and high-frequency components of a signal, similar to the low/high frequency energy ratio but focused on a different part of the spectrum. Applications encompass vibration anomaly detection in motors/fans/pumps, machine health monitoring via accelerometer data, and gesture recognition on IMU sensors for detecting sharp or high-frequency movements. |

## Feature Selection

Feature Selection allows you to automatically select the most important features for model building, reducing dataset size and improving performance.

![Feature Selection](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/J1wDh2G6hRPTahNn5N7~Ow-aNQtRTyvjlJdHnUOv1c8sw/content?v=3bbb0bb9916c14c5)

Features will be removed if:

* They are constants.
* Their correlation with other features is 1.00.
* It causes a metric loss of 0.875% or more (feature importance).

---

## Extracted hard requirements (key_facts, verbatim from capture)

- When the window size is configured, the platform automatically extracts selected features for each column (variable or axis); the same features are extracted during inference.
- Frequency-domain features use Fast Fourier Transform (FFT) to calculate the frequency of peaks and their power.
- When frequency-domain features are enabled, the window size must be a power of 2 and between 128 and 2048 samples.
- Feature Selection: a feature is removed if it is constant.
- Feature Selection: a feature is removed if its correlation with other features is 1.00.
- Feature Selection: a feature is removed if it causes a metric loss of 0.875% or more (feature importance).
- Percentage of Signal over Sigma is the ratio of sensor signal values greater than the sigma value (mean + n standard deviations) in a window over the total window size.
- Hjorth Complexity converges to a value of 1 when the signal is more similar to a pure sine wave.
- Dominant Frequencies analysis is applied to biomedical signals such as atrial fibrillation at 4–9 Hz.

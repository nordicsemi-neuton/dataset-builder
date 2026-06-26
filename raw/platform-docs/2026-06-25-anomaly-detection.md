# RAW SOURCE — Anomaly Detection

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=anomaly-detection fetch_ok=True

---

<!-- source segment: pass=p1 slug=anomaly-detection fetch_ok=True -->

# Anomaly detection

This page describes how to train and evaluate anomaly detection models in Nordic Edge AI Lab, including data requirements, the cosine distance distribution plot, and reconstruction accuracy.

## Overview

Nordic Edge AI Lab enables you to train anomaly detection models in an unsupervised manner.

You do not need to label your data as normal or abnormal.

Simply upload a dataset representing normal operational sensor data, and the system learns to recognize it as the normal mode of operation.

During inference, if new sensor data falls outside these learned patterns, it is classified as abnormal.

Unlike classification or regression, the anomaly detection task in Neuton always trains a single model and does not support adding a holdout validation dataset.

Model validation is performed by running inference on datasets with and without anomalies and analyzing the predicted anomaly scores.

## Cosine distance distribution plot

After data preprocessing, Edge AI Lab generates a **cosine distance distribution plot** for anomaly detection solutions.

Each point on the plot represents a training data sample.

Points closer to the center have a smaller cosine distance and are more similar to one another.

Points farther from the center indicate samples that differ more from the rest of the dataset.

This visualization helps you understand the internal structure and variability of your normal data.

The plot is available for newly created anomaly detection solutions.

## Reconstruction accuracy

**Reconstruction accuracy** measures how well the model can recreate the input data.

High reconstruction accuracy means the model has learned the normal patterns of the data well.

Low reconstruction accuracy means the model may not have learned the data properly, or the data may contain too much noise or anomalies.

The closer the reconstruction accuracy is to 1 (the maximum score), the higher the anomaly detection accuracy.

## Inference and anomaly score threshold

For details on running inference and configuring the anomaly score threshold, refer to the Edge AI Add-on samples.

---

_Capture note: This page (Nordic Edge AI Lab documentation, Zoomin platform) is a client-rendered single-page application protected by Cloudflare. The bare page URL returns only the navigation menu plus the page meta-description to a non-JavaScript fetcher. The article body above was recovered by fetching each documented sub-section anchor (Overview, Cosine distance distribution plot, Reconstruction accuracy, Inference and anomaly score threshold) individually, each via its own `contentId`. The four sub-sections listed in the page navigation were all captured. No separate "data requirements" block, table, or numeric data-format specification (file-size limit, sampling rate in Hz, CSV encoding, column ordering, minimum sample count, units) appears on this page; the only data-related guidance is the Overview instruction to upload a dataset representing normal operational sensor data. The opening line under the "Anomaly detection" heading is the page meta-description, reproduced above._

Sub-section source URLs (with contentId):
- https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html?contentId=LN5D4mb9~OWzrnLDHrMMeg (Anomaly detection — page)
- https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html/overview?contentId=rCvgGkm0et33r~zS6yPmbw (Overview)
- https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html/cosine-distance-distribution-plot?contentId=TjJnqDFB70JjP7h~Ja3m7g (Cosine distance distribution plot)
- https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html/reconstruction-accuracy?contentId=faV2QzrDIAqKi~Hs0tyYqA (Reconstruction accuracy)
- https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/anomaly_detection.html/inference-and-anomaly-score-threshold?contentId=LNRj1M5NIyUgpsVOAKKNlw (Inference and anomaly score threshold)

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Nordic Edge AI Lab enables you to train anomaly detection models in an unsupervised manner.
- You do not need to label your data as normal or abnormal.
- Simply upload a dataset representing normal operational sensor data, and the system learns to recognize it as the normal mode of operation.
- During inference, if new sensor data falls outside these learned patterns, it is classified as abnormal.
- Unlike classification or regression, the anomaly detection task in Neuton always trains a single model and does not support adding a holdout validation dataset.
- Model validation is performed by running inference on datasets with and without anomalies and analyzing the predicted anomaly scores.
- After data preprocessing, Edge AI Lab generates a cosine distance distribution plot for anomaly detection solutions.
- The cosine distance distribution plot is available for newly created anomaly detection solutions.
- The closer the reconstruction accuracy is to 1 (the maximum score), the higher the anomaly detection accuracy.

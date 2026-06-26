# RAW SOURCE — Overview of Nordic Edge AI Lab (Neuton, Axon NPU, Workflow)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/overview_of_nordic_edge_ai_lab.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=overview-neuton-axon-workflow fetch_ok=True anchors=3/3

---

<!-- source segment: pass=p2 slug=overview-neuton-axon-workflow fetch_ok=True anchors=3/3 -->

# Overview: Neuton, Axon NPU, Workflow

## Neuton overview

Neuton focuses on fully automated model generation and ultra-compact architectures optimized for resource-constrained devices. It supports:

* Regression
* Binary classification
* Multiclass classification
* Anomaly detection

Models are generated automatically without requiring users to design or tune neural network architectures.

## Axon overview

Axon targets deployments on the Axon NPU and provides greater architectural flexibility. It supports:

* Regression
* Binary classification
* Multiclass classification

You can customize and experiment with different neural network architectures, allowing comparison between multiple training runs to identify the most suitable model for their use case.

Additionally, a data-free wake word pipeline is available exclusively for the Axon NPU. This pipeline enables automatic wake word model generation without requiring users to upload a dataset. For all other task types, dataset upload is required for model training.

## Workflow

To train a machine learning model using Nordic Edge AI Lab, you need a CSV-formatted dataset containing independent features and dependent variables. The platform supports comprehensive signal processing capabilities including windowing, feature extraction, and feature selection.

The model training process involves three core steps:

1. Selecting data for training — Prepare your CSV dataset with features and target labels
2. Training your model — Configure model settings and let the platform identify patterns
3. Running inference on a device — Deploy the trained model

Model accuracy is calculated automatically on the split portion of the training dataset. You can also upload independent validation datasets to verify performance metrics.

Upon completion, you receive an archive with a ready-to-use Model and a calculation of the total footprint of the entire ML solution. The downloadable package includes the NRF EdgeAI Desktop Inference Runner for evaluating model quality on test data.

The Edge AI Lab platform includes an AI chatbot for quick support, and additional assistance is available through DevZone for any technical issues encountered during development.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Neuton supports the following task types: Regression, Binary classification, Multiclass classification, and Anomaly detection.
- Neuton generates models automatically without requiring users to design or tune neural network architectures.
- Axon targets deployments on the Axon NPU.
- Axon supports the following task types: Regression, Binary classification, and Multiclass classification.
- A data-free wake word pipeline is available exclusively for the Axon NPU, enabling automatic wake word model generation without requiring users to upload a dataset.
- For all task types other than the data-free wake word pipeline, dataset upload is required for model training.
- To train a machine learning model using Nordic Edge AI Lab, you need a CSV-formatted dataset containing independent features and dependent variables.
- The platform supports signal processing capabilities including windowing, feature extraction, and feature selection.
- The model training process involves three core steps: selecting data for training, training your model, and running inference on a device.
- Model accuracy is calculated automatically on the split portion of the training dataset.
- Independent validation datasets can be uploaded to verify performance metrics.
- Upon completion, you receive an archive with a ready-to-use Model and a calculation of the total footprint of the entire ML solution.
- The downloadable package includes the NRF EdgeAI Desktop Inference Runner for evaluating model quality on test data.

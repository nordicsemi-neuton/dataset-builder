# RAW SOURCE — Getting Started (3): firmware setup, model training, target hardware, results, embedding, tuning

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/get_started.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=getstarted-training-deploy fetch_ok=True anchors=6/7

---

<!-- source segment: pass=p2 slug=getstarted-training-deploy fetch_ok=True anchors=6/7 -->

# Getting Started: setup firmware, model training, target hardware, training, results, embedding, tuning

## Setting up firmware project

> [not retrieved]

## Model Training

After clicking **Next**, the platform redirects you to the Model Training Tab, where you can set the model settings and monitor training progress.

1. Click **New Session** to proceed. This example uses the Neuton framework, where only a single session is available. When using the LiteRT framework for Axon NPU, multiple sessions can be created, allowing you to experiment with different configurations and compare the results.

2. Enter the session name. The training framework is Neuton, the created model is for Cortex-M CPU.

3. Set up the following model settings:

   - **Weights & Coefficients** — Select Quantization-Aware 16-bit Integer. This option reduces memory footprint and speeds up inference while keeping accuracy high.
   - **Output Format** — Select floating-point 32-bit probabilities with values from 0 to 1. This provides easy-to-read confidence scores for each gesture class.
   - **Early stopping** — This setting is optional. Edge AI Lab will stop training when achieving the best possible accuracy. For demonstration purposes, set a target accuracy value to stop training early. During training, Edge AI Lab performs validation. When the accuracy score reaches 0.99, training stops.

## Defining Target Hardware

Select the target hardware for your model. Edge AI Lab compiles an archive containing the model along with all necessary data preprocessing and inference code for the specified hardware.

For this project, the target device is the Nordic Thingy:53 (nRF5340), so select `Cortex-M33` as the target hardware. You can select multiple hardware options, and the corresponding binaries are included in the downloadable archive.

![Target hardware](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/rxomL6yiGXFY6MR18zmN0Q-aNQtRTyvjlJdHnUOv1c8sw/content?v=d9b2cbc99b6e6c8c)

## Starting Training

After clicking **Start New Training**, the process runs in fully automatic mode. For convenience, the platform sends a notification as soon as the model is ready.

![Training progress](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/u_WbGarMfNPWJ4DxHqb3DA-aNQtRTyvjlJdHnUOv1c8sw/content?v=9486a3061c3b0934)

## Checking the Results

After model training is completed, the platform provides several key insights and artifacts for the model, including:

*   Final model accuracy
*   Accuracies and footprints of models at each iteration

    Note: To download a smaller model and tolerate slightly lower accuracy, select any iteration from the chart. All metrics, footprints, and analytics will be recalculated automatically, and a corresponding archive will be prepared for download.

*   Model footprint for the selected target hardware. If multiple devices were selected, use the **Target hardware** dropdown to choose another device. The displayed footprint will update accordingly.

*   Data Analytics, that shows the distribution of variables in the dataset.

*   Model Quality Diagram, that represents multiple metrics relevant to the task type.

*   Feature Importance Matrix (FIM), that shows the contribution of each input feature to the model's predictions.

*   Confusion Matrix, that visualizes the model's performance by showing correct and incorrect predictions for each class.

You can download the archive to your PC.

## Embedding a Neuton model into firmware project

1. For model integration and runtime behavior, use the `edge-ai/applications/gesture_recognition` application and follow the Gesture Recognition application documentation.

2. If you have built your own model on the Nordic Edge AI Lab, replace the `nrf_edgeai_generated` folder in `edge-ai/applications/gesture_recognition/src/` with the one from the downloaded archive, then rebuild and flash.

3. Make sure to update the `main.c`, `inference_postprocessing.c`, and `inference_postprocessing.h` files to match the classes your model was trained to recognize and to adjust the postprocessing logic accordingly.

## Model tuning and improvement

Typically, the first iteration produces a model that does not work flawlessly. The most common issue is false detections, where the model predicts one of the target classes when the subject is performing a different action. To address this:

*   Test the model on device.
*   Remember which unintended movements result in false detections.
*   Collect raw sensor data for those movements and add them to the _unknown class_.
*   Retrain the model.
*   Test again.

A few iterations of this process are usually necessary to achieve high accuracy and a low rate of false detections.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Model Training: only a single training session is available when using the Neuton framework; when using the LiteRT framework for Axon NPU, multiple sessions can be created.
- Model Training: in this example the training framework is Neuton and the created model is for Cortex-M CPU.
- Model Training - Weights & Coefficients: select Quantization-Aware 16-bit Integer, which reduces memory footprint and speeds up inference while keeping accuracy high.
- Model Training - Output Format: select floating-point 32-bit probabilities with values from 0 to 1.
- Model Training - Early stopping: this setting is optional; when set for demonstration, training stops when the accuracy score reaches 0.99.
- Defining Target Hardware: Edge AI Lab compiles an archive containing the model along with all necessary data preprocessing and inference code for the specified hardware.
- Defining Target Hardware: for this project the target device is the Nordic Thingy:53 (nRF5340), so Cortex-M33 is selected as the target hardware.
- Defining Target Hardware: you can select multiple hardware options, and the corresponding binaries are included in the downloadable archive.
- Starting Training: after clicking Start New Training, the process runs in fully automatic mode and the platform sends a notification as soon as the model is ready.
- Checking the Results: to download a smaller model and tolerate slightly lower accuracy, select any iteration from the chart; all metrics, footprints, and analytics are recalculated automatically and a corresponding archive is prepared for download.
- Checking the Results: if multiple devices were selected, use the Target hardware dropdown to choose another device and the displayed footprint updates accordingly.
- Checking the Results artifacts include: Final model accuracy, Data Analytics, Model Quality Diagram, Feature Importance Matrix (FIM), and Confusion Matrix.
- Embedding: for model integration and runtime behavior, use the edge-ai/applications/gesture_recognition application and follow the Gesture Recognition application documentation.
- Embedding: if you built your own model on the Nordic Edge AI Lab, replace the nrf_edgeai_generated folder in edge-ai/applications/gesture_recognition/src/ with the one from the downloaded archive, then rebuild and flash.
- Embedding: update the main.c, inference_postprocessing.c, and inference_postprocessing.h files to match the classes your model was trained to recognize and to adjust the postprocessing logic accordingly.
- Model tuning: collect raw sensor data for movements that cause false detections and add them to the unknown class, then retrain and test again; a few iterations are usually necessary to achieve high accuracy and a low rate of false detections.

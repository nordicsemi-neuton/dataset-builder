# RAW SOURCE — Pipeline: Model Training (sessions, results, progress, footprint, archive)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/model_training.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-model-training fetch_ok=True
> - pass=p2 slug=model-training-results fetch_ok=True anchors=8/8

---

<!-- source segment: pass=p1 slug=pipeline-model-training fetch_ok=True -->

# Model training

After configuring data preprocessing, the next step is to train your model. During this stage, you configure the model training and optimization settings, monitor training progress, and view or download the results.

To begin, click **New Session** to open the model settings. The available settings differ between the Neuton framework and the LiteRT framework, but the training process and results are similar for both.

For comprehensive details on each available configuration option, refer to the **Model Settings** section in the documentation.

---

**Navigation:** Back to home page (https://docs.nordicsemi.com/)

---

> Capture note: This page is a short introductory section of the model-creating pipeline. The body contains only the introductory text above plus a reference/link to the **Model Settings** section. Two independent WebFetch passes agree that the page body contains NO numeric values, default parameters, training metrics, epochs, batch sizes, learning rates, file formats, units, or limits — those details are stated to live in the referenced "Model Settings" section, not on this page. The "New Session" button and the Neuton / LiteRT framework names are the only named UI/framework elements present. The page references a Model Settings link (https://docs.nordicsemi.com/r/aNQtRTyvjlJdHnUOv1c8sw/shX6bMVVgi4fh1eMFApFag).

---

<!-- source segment: pass=p2 slug=model-training-results fetch_ok=True anchors=8/8 -->

# Model Training: sessions, model results, training progress, processed data, growth chart, footprint, archive

## Sessions

When using the Neuton framework, only a single training session can be created.

If you selected Axon NPU as the technology, the LiteRT framework is automatically applied. In this case, you can create multiple training sessions with different model architectures, allowing you to compare results and choose the most suitable model for your use case.

All sessions are displayed in the **Sessions** tab, where you can monitor training progress and evaluate model performance. Each session shows the following information:

*   **Sessions** — A unique identifier assigned to the training session.
*   **Name** — The name of the training session.
*   **Axon version** — The Axon compiler version the model is now compiled with (only available for the LiteRT framework).
*   **Created** — The date and time when the session was created.
*   **Framework** — The framework used for training (Neuton or LiteRT).
*   **Status** — The current status of the training session (In Progress, Completed, or Stopped).
*   **Evaluation metric** — The best value of the evaluation metric achieved during training (for example, accuracy for classification tasks or RMSE for regression tasks).

## Model results

After configuring model settings, click **Start New Training** to begin the training process. Once training has started, the **Results** section appears in the right panel, providing a comprehensive overview of the model's performance.

## Training progress

The training progress bar displays the current state of model creation. You can stop training at any time by clicking the **Stop** button if you are satisfied with the current results. Once training is finished or stopped, you can view the training log by clicking the **Log** button next to the progress bar.

## Processed Data

This section displays the data used for model training, incorporating any additional settings selected during configuration, such as features generated through feature extraction. Access the **Data Analytics** button to view analytics charts based on the processed data.

## Solution options

This section presents the results of the training process, allowing you to evaluate model performance, analyze memory requirements, and download the compiled solution.

## Model Growth Chart

The model growth chart displays iterations of the model's construction on a single graph. By interacting with the chart, you can compare and select models with granular differences in size (down to kilobytes) and accuracy (down to hundredths of a percent). This allows you to choose the most optimal model for resource-constrained devices.

**Note**

The model growth chart and detailed footprint estimations are not available for the Axon technology (LiteRT framework).

## Performance metrics and footprint

When reviewing a solution, the interface provides detailed specifications for the selected model:

- **Target metric** — Displays the current metric value (for example, Validation Accuracy). You can use the Metric type dropdown to switch between Training Metrics and Validation Metrics. If a separate holdout dataset was not provided before training, the validation metrics are automatically calculated based on a 20% split of your training data.
- **Total footprint** — Shows the estimated SRAM and NVM memory usage. This includes a detailed breakdown for the model, the inference engine, and signal processing, calculated specifically for your selected target hardware.

## Downloadable Model Archive

Click the **Download model** button to download the compiled model archive. The downloaded archive contains the following folders and files:

* `artifacts` — Contains an executable binary for model predictions on the desktop, as well as other useful artifacts.
* `nrf_edgeai_generated` — Contains the Nordic Edge AI Lab generated user solution for the runtime library.
* `LICENSE` — Contains the possibilities and restrictions on the use of Nordic Semiconductor intellectual property.
* `README` — Contains instructions and guidelines for using the libraries.

To execute the model on your hardware, you need the inference runtime libraries, which are provided with the nRF Edge AI Add-on. Refer to the [Edge AI Add-on](https://docs.nordicsemi.com/bundle/addon-edge-ai_latest/page/index.html) documentation for further deployment instructions.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- When using the Neuton framework, only a single training session can be created.
- If Axon NPU is selected as the technology, the LiteRT framework is automatically applied, and multiple training sessions with different model architectures can be created.
- A session Status can be one of: In Progress, Completed, or Stopped.
- The session Framework can be Neuton or LiteRT.
- The Axon version field (Axon compiler version) is only available for the LiteRT framework.
- Training can be stopped at any time by clicking the Stop button.
- The model growth chart and detailed footprint estimations are not available for the Axon technology (LiteRT framework).
- The model growth chart supports comparing/selecting models with size differences down to kilobytes and accuracy differences down to hundredths of a percent.
- If a separate holdout dataset was not provided before training, the validation metrics are automatically calculated based on a 20% split of the training data.
- The Metric type dropdown switches between Training Metrics and Validation Metrics.
- Total footprint shows estimated SRAM and NVM memory usage, with a breakdown for the model, the inference engine, and signal processing, calculated for the selected target hardware.
- The downloaded model archive contains the folders/files: artifacts, nrf_edgeai_generated, LICENSE, and README.
- To execute the model on hardware, the inference runtime libraries provided with the nRF Edge AI Add-on are required.

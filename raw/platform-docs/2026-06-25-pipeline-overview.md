# RAW SOURCE — Model Creating Pipeline (overview)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/index.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-overview fetch_ok=True

---

<!-- source segment: pass=p1 slug=pipeline-overview fetch_ok=True -->

# Model creating pipeline

> Section: Edge AI Lab
> tags: edge-ai-lab

The model training process in Edge AI Lab consists of several fully automated steps.

_[A pipeline diagram illustrates the entire workflow.]_

Refer to the following sections for a detailed description of each step:

1. Solution creation
2. Dataset requirements
3. Data uploading and setup
4. Data preprocessing
5. Signal processing
6. Model training
7. Model settings
8. Run inference on the MCU
9. Run inference on the desktop

---

## Capture notes

This URL is the overview/index page for the "Model creating pipeline" section of the Nordic Edge AI Lab documentation. The main content body is brief: a title, one introductory sentence ("The model training process in Edge AI Lab consists of several fully automated steps."), a pipeline diagram (rendered as an image, no transcribable text caption was returned by the fetcher), a lead-in sentence ("Refer to the following sections for a detailed description of each step:"), and an ordered list of nine links to the detailed sub-section pages listed above.

The page itself contains NO hard data requirements, numbers, units, column names, or file-format limits — those live in the linked sub-pages (notably "Dataset requirements" → "Requirements for training datasets" / "How to identify and change file encoding", and "Data uploading and setup"). Those detail pages must be captured separately to obtain the actual platform data-preparation rules.

For reference, the section's full sub-page table of contents (as exposed in the documentation navigation under "Model creating pipeline") is:

- Model creating pipeline
  - Solution creation
  - Dataset requirements
    - Requirements for training datasets
    - How to identify and change file encoding
  - Data uploading and setup
    - Uploading dataset
    - Selecting an uploaded or preloaded dataset
    - Using preloaded use cases
    - Dataset options
      - Session ID
      - Holdout validation
  - Data preprocessing
    - Signal processing
    - Input data type
    - Normalization type
    - Task type and evaluation metric
      - Classification metrics
      - Regression metrics
      - Anomaly detection metrics
  - Signal processing
    - Guided setup
    - Windowing
    - Sliding shift
    - Estimated SRAM usage
    - Raw data option
    - Sub-windowing
    - Feature extraction
      - Time-domain features
        - Statistical features
        - Regression features
        - Crossing-rate features
        - Signal shape and variation
        - Hjorth parameters
        - Peak-to-peak features
      - Frequency-domain features
        - Spectral analysis
        - Dominant frequency features
        - Energy ratio features
    - Feature selection
  - Model training
    - Sessions
    - Model results
      - Training progress
      - Processed data
      - Solution options
      - Model growth chart
      - Performance metrics and footprint
      - Downloadable model archive
      - Analytics tools
    - Model settings
      - Starting a new session
      - Weights and coefficients (bit depth)
      - Output format
      - Training stop options
      - Target hardware
      - LiteRT model settings
      - Training parameters
      - Model architecture
        - Architecture presets
        - Input and output layers
        - Adding and configuring layers
          - Core layers
          - Convolutional layers
          - Pooling layers
  - Run Inference on MCU
    - Inference engine
    - Key features
  - Run inference on desktop
    - Available commands
      - Getting solution information
      - Running inference
      - Getting metrics
      - Customizing CSV file reading settings

(This TOC is included for navigation context only; it reflects the documentation tree, not the body text of this specific overview page.)

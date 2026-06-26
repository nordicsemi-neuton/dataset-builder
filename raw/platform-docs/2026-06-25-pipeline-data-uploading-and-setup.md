# RAW SOURCE — Pipeline: Data Uploading and Setup (upload, dataset options, session ID, holdout)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/data_uploading_and_setup.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-data-uploading-and-setup fetch_ok=True
> - pass=p2 slug=data-uploading-and-setup fetch_ok=True anchors=6/6

---

<!-- source segment: pass=p1 slug=pipeline-data-uploading-and-setup fetch_ok=True -->

# Data uploading and setup

> Archive note (capture fidelity): This page was retrieved via WebFetch on 25.06.2026. The page renders as a documentation section of the Edge AI Lab "Model creating pipeline." The fetched content below is reproduced as faithfully as the converted markdown allowed. Across three separate fetches (full-content, hard-data-requirements, and session/holdout-focused), the page consistently returned the same core prose. The page's detailed numeric/format dataset requirements are NOT stated inline on this page — they are deferred to a separate linked page, "Dataset requirements" (see Links below). Sub-sections "Session ID" and "Holdout validation" are present on the page as headings, but the WebFetch markdown converter did not expand their full body prose beyond what is shown; this is flagged so a re-verification can target those anchors directly from the live page.

To begin model training, you first need to select or upload your dataset.

## Dataset selection options

The interface provides two primary pathways:

- **Uploaded Datasets**: Upload your own CSV or ZIP files, or select from previously uploaded datasets.
- **Preloaded Use Cases**: Demo datasets are available for testing and exploring platform capabilities.

## Key constraints

- Only one dataset is used to train one model.
- If your data is distributed across multiple files, combine them in advance before uploading.
- Ensure your data meets the dataset requirements. (Linked to a separate "Dataset requirements" page — see Links below.)

## Data security

Upon uploading, your data is encrypted and securely stored in the cloud.

## Dataset options (setup after upload)

After uploading your dataset, you configure dataset options, which include:

### Session ID

(Section heading present on the page. The detailed body text for configuring the Session ID was not expanded in the fetched markdown and should be re-verified against the live page anchor.)

### Holdout validation

(Section heading present on the page. The detailed body text describing holdout validation configuration, including any split percentages or field names, was not expanded in the fetched markdown and should be re-verified against the live page anchor.)

## Image

The page includes an image depicting the uploading options; the specific visual details are not textually described in the source material.

## Links referenced from this page

- Dataset requirements — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/dataset_requirements.html
- Requirements for training datasets — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/dataset_requirements.html/requirements-for-training-datasets

> The hard data requirements (file encoding, delimiters, decimal separators, file sizes, row counts, column naming/order, target/label column, timestamp column, sensor axis columns, sampling rate, window size/shift, sub-windowing, value ranges, NaN handling, number of classes, minimum samples per class, class balance, session/group IDs, holdout split percentages, etc.) are NOT enumerated on this page. They live on the linked "Dataset requirements" page and must be captured from there.

---

<!-- source segment: pass=p2 slug=data-uploading-and-setup fetch_ok=True anchors=6/6 -->

# Data Uploading and Setup

## Uploading Dataset

Click **Upload .csv or .zip file** and select your file, or simply drag and drop it to the designated area.

The platform automatically checks your dataset during upload. If an error message appears, verify and correct your file, then upload again. Successful upload is marked with a green check mark.

**Note:** Ensure your dataset structure and variable types are correct to avoid upload or processing errors. For details, see the dataset requirements.

After uploading, you can preview the dataset using the lens icon. Press **OK** to proceed.

If a file with the same name already exists, you will be prompted to rename your new file. For efficient storage, upload each dataset only once and select it from storage for future use.

## Selecting an Uploaded or Preloaded Dataset

To use an existing dataset, simply navigate and select it from the list of previously uploaded files.

![Selection of Uploaded Datasets](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/_TAbPjdMxnNuilB9Nit62Q-aNQtRTyvjlJdHnUOv1c8sw/content?v=e104027ff838845f)

## Using Preloaded Use Cases

The Nordic Edge AI Lab provides preloaded datasets across various domains, allowing users to explore platform capabilities without preparing custom data.

### Key Features

**Access Method:** Click the "Preloaded Use Cases" tab to view available datasets. Each dataset includes an information icon for additional details.

**Purpose:** These datasets are "ideal for experimenting with model training, validation, and pipeline steps, providing a safe environment to learn and test the platform."

**Limitations:** All settings for preloaded datasets come preconfigured and cannot be modified by users.

### Usage Context

Preloaded use cases serve as a learning resource, enabling users to understand the platform's workflow and capabilities before working with custom datasets.

## Dataset Options

After selecting your training dataset, specify the target column and, if applicable, a Session ID column for time-series or session-based data. You may also exclude any features (columns) you consider irrelevant.

[Image: Dataset options interface]

To exclude features from training, select the corresponding checkboxes in the **Remove variables** section. The model will automatically ignore these columns during training and validation.

## Session ID

The Session ID column in a dataset is used to describe a time-continuous process, such as readings from sensors over time. It helps in separating different sessions or instances within the dataset, allowing for more precise and concise model creation. Including a Session ID column can enhance the model's accuracy by providing context about the sequence of data points.

While it is not mandatory to specify a Session ID column, doing so can be beneficial if your dataset involves time-series data or processes that need to be distinguished by session. It ultimately depends on the nature of your data and the specific requirements of your analysis. If you have a `session_id` attribute in your data, use a **Session ID** radio button to identify this column in the **Dataset** tab.

## Holdout Validation

To enable holdout validation, turn on the switch and upload your validation dataset. The holdout validation dataset must match the format of your training data. If you do not enable this option, the platform will automatically split your training data: 80% will be used for training, and 20% for validation. Holdout validation allows you to evaluate your model on a completely separate, user-provided dataset for more robust testing.

When finished, click **Next** to proceed to the data preprocessing stage.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Only one dataset is used to train one model.
- If your data is distributed across multiple files, combine them in advance before uploading.
- Datasets are uploaded as CSV or ZIP files.
- Upon uploading, your data is encrypted and securely stored in the cloud.
- Data must meet the dataset requirements (defined on a separate linked 'Dataset requirements' page).
- Datasets are uploaded via the 'Upload .csv or .zip file' control, accepting .csv or .zip files, or by drag and drop to the designated area.
- The platform automatically checks the dataset during upload; if an error message appears, the file must be corrected and uploaded again, and successful upload is marked with a green check mark.
- Dataset structure and variable types must be correct to avoid upload or processing errors.
- If a file with the same name already exists, the user is prompted to rename the new file; each dataset should be uploaded only once and selected from storage for future use.
- All settings for preloaded datasets come preconfigured and cannot be modified by users.
- After selecting a training dataset, the user must specify the target column and, if applicable, a Session ID column for time-series or session-based data.
- Features (columns) can be excluded from training by selecting checkboxes in the 'Remove variables' section; excluded columns are ignored during training and validation.
- Specifying a Session ID column is not mandatory.
- If the data contains a `session_id` attribute, use the 'Session ID' radio button to identify this column in the 'Dataset' tab.
- If holdout validation is enabled, the user must upload a validation dataset that matches the format of the training data.
- If holdout validation is NOT enabled, the platform automatically splits the training data: 80% for training and 20% for validation.

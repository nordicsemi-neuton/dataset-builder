# RAW SOURCE — Pipeline: Dataset Requirements (training & holdout datasets, file encoding)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/dataset_requirements.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-dataset-requirements fetch_ok=True

---

<!-- source segment: pass=p1 slug=pipeline-dataset-requirements fetch_ok=True -->

# Dataset requirements

The following requirements are provided for training and test (holdout) datasets. You must meet them for successful model training and prediction on the new data. To check the datasets, use a text editor, such as Notepad++.

This page contains two subsections:
- Requirements for training datasets
- How to identify and change file encoding

---

## Requirements for training datasets

Your training dataset must meet the following criteria to be compatible with Edge AI Lab and suitable for building accurate machine learning models. For the exact requirements, see the relevant option depending on your use case:

* It must be a CSV file using UTF-8 or ISO-8859-1 encoding.
* The file name must not contain the following special characters: `!/[+!@#$%^&*,. ?":{}\\/|<>()[]]`.
* All feature values in the dataset must be numeric. For the classification task type, values of the target variable should start with `0`.
* A dataset must not have any empty values or values which represent empty values, such as `NA`, `NAN`, and others.
* A comma, semicolon, pipe, care, or tab must be used as a separator.
* You should use CRLF or LF as the end-of-line character and ensure it is consistent.
* All column names (values in the CSV file header) must be unique and must contain only letters (a-z, A-Z), numbers (0-9), hyphens (-), or underscores (_).
* For the classification task type, a training dataset must have a minimum of 2 classes of target variable with at least 20 samples provided for each class.
* Currently, the Edge AI Lab supports only the EN-US locale for numbers. This means the following:
    * You must use a dot as a decimal separator, and delete spaces and commas typically used to separate every third digit in your numeric fields. For example, `20,000.00` should be replaced with `20000.00`.
    * If any numeric column is represented as a combination of a number and its corresponding unit, then only the number should be placed in the column. For example, `$20,000.00` should be replaced with `20000.00`.
    * Date and time columns must be in epoch time representation or relative date format. For example, `10/18/2017` should be represented as `1508284800`.
    * In test datasets, the same timestamp format should be used in a manner consistent with the training dataset.
    * End-of-line symbols must be excluded from the field values.
    * In the case of sensor data from gyroscopes, accelerometers, magnetometers, electromyography (EMG), and other similar devices for creating models using Signal Preprocessing, every row of a dataset should be device readings per unit of time with a label as a target. You should not shuffle signal labels or encode your signal for model creation. For example, if the window is 8, then the dataset can be organized as follows: [Training dataset image referenced]
* The number of lines must be excluded from the training dataset.
* Data can be represented in the following types: INT8, INT16, FLOAT 32.
* When transferring data for inference on the device, the values must always be in the same order as in the training dataset.
* Datatype should match the train data type.

### Test (holdout) dataset

* A dataset must be a CSV file using UTF-8 or ISO-8859-1 encoding.
* The first row in the dataset must contain the column names, and a comma, semicolon, pipe, caret, or tab must be used as a separator. CRLF or LF should be used as the end of a line character.
* The test (holdout) dataset must have the same file structure with the same requirements for the feature values as the training dataset. The order of fields must be the same as in the training dataset.
* End-of-line symbols must be excluded from the field values. [Test (holdout) dataset image referenced]

---

## How to identify and change file encoding

The Nordic Edge AI Lab supports UTF-8 and ISO-8859-1 encoding for CSV files. You must verify your file's encoding and convert it to one of these supported formats if necessary.

### Checking file encoding

Open your file in a text editor such as Notepad++. The current encoding appears in the bottom right corner of the window.

### Converting to supported encoding

If your file uses an encoding other than UTF-8 or ISO-8859-1, convert it to UTF-8:

1. Select the **Encoding** menu
2. Click **Convert to UTF-8**
3. Verify that UTF-8 now displays in the bottom right corner
4. Save the file

Your file is now ready to upload to the Nordic Edge AI Lab.

---

> Capture note: docs.nordicsemi.com is a JavaScript-rendered documentation site behind a Cloudflare bot challenge (raw `curl` returns HTTP 403 "Just a moment..."). The substantive content is not present in the initial page HTML; it loads per-section keyed by `contentId`. The two subsections were retrieved via their in-page anchor URLs:
> - Requirements for training datasets -> `.../dataset_requirements.html/requirements-for-training-datasets?contentId=9ruBAm9tuIiqgJZkSmpLZA`
> - How to identify and change file encoding -> `.../dataset_requirements.html/how-to-identify-and-change-file-encoding?contentId=P0KP9up0IebwQ4cJi9KtDA`
> Two image figures ("Training dataset" and "Test (holdout) dataset") are referenced on the page illustrating the sensor/window layout (e.g. window = 8); the image pixel content itself could not be transcribed. The intro sentence and both subsections were each confirmed across multiple fetches with verbatim-matching detail.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- The training dataset must be a CSV file using UTF-8 or ISO-8859-1 encoding.
- The test (holdout) dataset must be a CSV file using UTF-8 or ISO-8859-1 encoding.
- The file name must not contain the following special characters: !/[+!@#$%^&*,. ?":{}\\/|<>()[]].
- All feature values in the dataset must be numeric.
- For the classification task type, values of the target variable should start with 0.
- A dataset must not have any empty values or values which represent empty values, such as NA, NAN, and others.
- A comma, semicolon, pipe, care, or tab must be used as a separator.
- You should use CRLF or LF as the end-of-line character and ensure it is consistent.
- All column names (values in the CSV file header) must be unique and must contain only letters (a-z, A-Z), numbers (0-9), hyphens (-), or underscores (_).
- For the classification task type, a training dataset must have a minimum of 2 classes of target variable with at least 20 samples provided for each class.
- Edge AI Lab supports only the EN-US locale for numbers.
- You must use a dot as a decimal separator, and delete spaces and commas typically used to separate every third digit in numeric fields. For example, 20,000.00 should be replaced with 20000.00.
- If a numeric column is a combination of a number and its unit, only the number should be placed in the column. For example, $20,000.00 should be replaced with 20000.00.
- Date and time columns must be in epoch time representation or relative date format. For example, 10/18/2017 should be represented as 1508284800.
- In test datasets, the same timestamp format should be used in a manner consistent with the training dataset.
- End-of-line symbols must be excluded from the field values.
- For sensor data from gyroscopes, accelerometers, magnetometers, electromyography (EMG), and other similar devices for creating models using Signal Preprocessing, every row of a dataset should be device readings per unit of time with a label as a target.
- You should not shuffle signal labels or encode your signal for model creation.
- Example: if the window is 8, then the dataset can be organized as shown in the training dataset figure.
- The number of lines must be excluded from the training dataset.
- Data can be represented in the following types: INT8, INT16, FLOAT 32.
- When transferring data for inference on the device, the values must always be in the same order as in the training dataset.
- Datatype should match the train data type.
- The first row in the dataset must contain the column names, and a comma, semicolon, pipe, caret, or tab must be used as a separator; CRLF or LF should be used as the end of a line character.
- The test (holdout) dataset must have the same file structure with the same requirements for the feature values as the training dataset.
- The order of fields in the test (holdout) dataset must be the same as in the training dataset.
- Nordic Edge AI Lab supports UTF-8 and ISO-8859-1 encoding for CSV files; verify the file's encoding and convert it to one of these supported formats if necessary.
- To convert encoding in Notepad++: select the Encoding menu, click Convert to UTF-8, verify that UTF-8 displays in the bottom right corner, and save the file.

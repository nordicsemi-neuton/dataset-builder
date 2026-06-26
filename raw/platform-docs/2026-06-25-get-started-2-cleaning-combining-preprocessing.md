# RAW SOURCE — Getting Started (2): segmentation, cleaning, combining CSVs, data overview, preprocessing, signal processing, features

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/get_started.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=getstarted-data-processing fetch_ok=True anchors=9/9

---

<!-- source segment: pass=p2 slug=getstarted-data-processing fetch_ok=True anchors=9/9 -->

# Getting Started: segmentation, cleaning, combining CSVs, data overview, preprocessing, signal processing, features

## Data segmentation

Gestures can be categorized as continuous (for example, running, swimming) and non-continuous, which have a start and finish (for example, swipe left, swipe right, jump). Non-continuous gestures require additional data preparation step: segmentation of raw data into perfect samples with gesture signal peak being in the middle of the feature extraction window. You must (subjectively) decide what is the timeframe of the longest gesture (for example, 1 second), then given the sampling rate (for example, 100Hz). This will be the window for all gestures segmentation in the raw data in order to create perfect training samples.

To simplify this process, you can use a [signal centering script](https://github.com/nordicsemi-neuton/segment-center-signal) that automates the segmentation step.

> The provided script performs this data-preparation step automatically when you supply the timeframe value representing the duration of the longest gesture.

## Data Cleaning

Make sure that your sensor data excludes idle and incorrect records, which may take place at the beginning or end of your data collection session when you are setting up hardware.

**Note**

Good practice is to delete the first and last few seconds from the collected data. If you are unsure about the quality of data, plot a single axis, find incorrectly collected samples and remove them from data. The script performs this step automatically.

## Combining CSV Files

To combine multiple labeled CSV files into a single dataset for Nordic Edge AI Lab, open a terminal in the directory containing your CSV files and execute the appropriate command for your operating system:

**Windows (PowerShell):**
```
Get-Content idle.csv, swipe_right.csv, swipe_left.csv | Set-Content dataset.csv
```

**macOS/Linux:**
```
cat idle.csv swipe_right.csv swipe_left.csv > dataset.csv
```

The resulting output will be a single CSV file containing all 8 gesture classes combined.

## Data Overview

For this use case, 8 minutes of accelerometer and gyroscope data were collected (2 minutes per motion) with the sensor frequency configured to 100 Hz. This generates 100 rows of sensor readings per second, with a snapshot of the data containing 10 rows, representing 0.1 seconds of motion.

The dataset includes a `class` column to indicate the corresponding activity for each motion. Additionally, the documentation notes that random movements and an idle class (no gestures) are also included to prevent false detections by the model.

A visual representation of the data structure is provided in the accompanying diagram showing the organized sensor data format.

## Signing in and Creating a Solution

1. For account setup and login details, consult the "Registration and login" page.

2. After logging in, select the **Add New Solution** button at the top.
   - The model classifies accelerometer and gyroscope data into 8 gesture classes
   - Target device: Nordic Thingy:53 (nRF5340)

3. Choose the **Neuton** option and select **Classification** as the task type.

4. Name your solution and click **Next**.

5. Upload your training data via drag-and-drop or file upload into the popup window, then click **OK**.

6. Set **class** as your **Target Column** and proceed by clicking **Next**.

## Data Preprocessing

Set up the following settings for input data and task configuration.

- **Data Type** — Choose Integer 16-bit as the data type (corresponds to the data we have uploaded).
- **Normalization Type** — Select Unique scale. A unique scale for each feature is used when features have different ranges.
- **Task Type** — Multi Classification, selected during Solution Creation, enables the model to recognize multiple gesture classes.
- **Evaluation Metric** — Choose Balanced Accuracy (ensures fair performance measurement when gesture classes are imbalanced).

![Input data and task configuration](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/VIf1VHLBdSoNihMpDq~oFQ-aNQtRTyvjlJdHnUOv1c8sw/content?v=a1659417ed575cc4)

## Enabling Signal Processing

Select **Manual Setup** and specify the window size. Since one gesture is executed in approximately one second, data should be processed in 99 records (1 second of sensor readings).

This means that for each set of 99 records per axis (ax, ay, az, gx, gy, gz), Neuton will extract features and represent the data as a single training sample (1 row).

The **Sliding Shift** controls how many records to skip before starting a new sample. To segment data by exactly one second without overlap, set the Sliding Shift for training to match the window size. To generate new samples with overlap, reduce the Sliding Shift value to be less than the window size.

The Sliding Shift for inference only affects sample generation from streaming data when performing inference on the edge device. For example, a Sliding Shift of 33 for inference queries the model 3 times per second. At the top of the page, you will see the estimated RAM footprint of the model.

## Feature Extraction

Key settings for training a robust model involve the Feature Extraction options. The Neuton framework generates features for each selected axis from the defined window. For example, the _Max_ feature for `accelerometer_X` returns the maximum reading within each window.

By default, Edge AI Lab is configured for optimal accuracy and footprint balance. For this use case, select the following features:

- Absolute Mean
- Average Magnitude Difference
- Max
- Mean
- Mean Absolute Deviation
- Min
- Percentage of signal over mean
- Percentage of signal over zero
- Root mean square
- Zero-crossing Rate
- Mean-crossing Rate
- Negative sigma crossing rate (setting 1)
- Percentage of signal over sigma (setting 1)
- Positive sigma crossing rate (setting 1)
- Root Difference Square
- Standard Deviation

For each of the six axes, 16 features will be extracted, resulting in a total of 96 features per sample.

Some features have additional settings (for example, **Positive sigma crossing rate**). To change feature settings, click the **Edit** icon and select the settings from the drop-down menu.

## Selecting a Feature

You can apply Feature Selection options to eliminate the least significant factors. This option is not used for this specific use case.

Features are removed if they meet any of the following criteria:

* They are constants.
* Their correlation with other features is 1.00.
* They cause a metric loss of ≥ 0.875% based on feature importance.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Non-continuous gestures require segmentation of raw data into samples with the gesture signal peak in the middle of the feature extraction window.
- Example longest-gesture timeframe is 1 second at a sampling rate of 100Hz, which defines the window for all gesture segmentation.
- A signal centering script (https://github.com/nordicsemi-neuton/segment-center-signal) automates the segmentation step when supplied the timeframe value of the longest gesture.
- Good practice is to delete the first and last few seconds from the collected data to exclude idle and incorrect records.
- Combine CSVs on Windows (PowerShell): Get-Content idle.csv, swipe_right.csv, swipe_left.csv | Set-Content dataset.csv
- Combine CSVs on macOS/Linux: cat idle.csv swipe_right.csv swipe_left.csv > dataset.csv
- The combined output is a single CSV file containing all 8 gesture classes combined.
- 8 minutes of accelerometer and gyroscope data were collected (2 minutes per motion).
- Sensor frequency is configured to 100 Hz, generating 100 rows of sensor readings per second.
- A snapshot of 10 rows represents 0.1 seconds of motion.
- A `class` column indicates the corresponding activity for each motion.
- Random movements and an idle class (no gestures) are included to prevent false detections by the model.
- The model classifies accelerometer and gyroscope data into 8 gesture classes.
- Target device is Nordic Thingy:53 (nRF5340).
- Set `class` as the Target Column.
- Data Type: choose Integer 16-bit.
- Normalization Type: select Unique scale (a unique scale per feature is used when features have different ranges).
- Task Type: Multi Classification (selected during Solution Creation).
- Evaluation Metric: choose Balanced Accuracy (for imbalanced gesture classes).
- Window size is 99 records (1 second of sensor readings, since one gesture is executed in approximately one second).
- For each set of 99 records per axis (ax, ay, az, gx, gy, gz), Neuton extracts features and represents the data as a single training sample (1 row).
- Sliding Shift controls how many records to skip before starting a new sample.
- To segment data by exactly one second without overlap, set the Sliding Shift for training to match the window size.
- To generate samples with overlap, reduce the Sliding Shift value to be less than the window size.
- A Sliding Shift of 33 for inference queries the model 3 times per second.
- The six axes are ax, ay, az, gx, gy, gz (accelerometer X/Y/Z and gyroscope X/Y/Z).
- For each of the six axes, 16 features are extracted, resulting in a total of 96 features per sample.
- Feature Selection removes a feature if it is a constant.
- Feature Selection removes a feature if its correlation with other features is 1.00.
- Feature Selection removes a feature if it causes a metric loss of >= 0.875% based on feature importance.
- The selected 16 features per axis are: Absolute Mean, Average Magnitude Difference, Max, Mean, Mean Absolute Deviation, Min, Percentage of signal over mean, Percentage of signal over zero, Root mean square, Zero-crossing Rate, Mean-crossing Rate, Negative sigma crossing rate (setting 1), Percentage of signal over sigma (setting 1), Positive sigma crossing rate (setting 1), Root Difference Square, Standard Deviation.

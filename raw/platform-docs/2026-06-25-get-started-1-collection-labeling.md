# RAW SOURCE — Getting Started (1): use case, raw dataset, requirements, data collection, recording, gesture, labeling

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/get_started.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=getstarted-data-collection fetch_ok=False anchors=4/8

---

<!-- source segment: pass=p2 slug=getstarted-data-collection fetch_ok=False anchors=4/8 -->

# Getting Started: use case, raw dataset, requirements, data collection, recording, gesture, labeling

## Use-case Description

### Overview

This project implements a gesture-based remote control using the Nordic Thingy:53 device, which connects to a PC via Bluetooth as a HID device. Users can "control media streams or slides of presentations" through gesture recognition.

### Recognized Gesture Classes

The Neuton machine learning model identifies eight gesture categories:

- Swipe right
- Swipe left
- Double shake
- Double thumb tap
- Rotation clockwise
- Rotation counter-clockwise
- No gestures (IDLE)
- Unknown gestures

### Data Sources

The documentation presents two paths forward:

1. **Raw Dataset Approach**: Enables creation of custom models or dataset augmentation for more robust training
2. **Provided Dataset**: A pre-compiled CSV file available for immediate use

The provided dataset link and detailed setup instructions direct users to the "Data overview section" for implementation guidance.

## Preparing raw dataset

> [not retrieved]
>
> (Anchor body did not load beyond navigation/intro. Partial signal from the page: this is a landing/index section for "Preparing raw dataset" with only a brief introductory statement; no substantive CSV/column/format prose was returned.)

## Requirements

> [not retrieved]
>
> (Anchor body did not load beyond navigation/intro. Partial signal from the page: the section directs the reader to install **VS Code**, **nRF Connect for VS Code**, and **nRF Connect for Desktop**, with a reference to complete instructions elsewhere. Full hardware/version/prerequisite prose was not returned.)

## Preparing data for gesture recognition

> [not retrieved]
>
> (Anchor body did not load beyond navigation/intro. Partial signal from the page: this section's workflow is stated to cover data collection procedures, recording sessions, gesture execution guidelines, labeling instructions, segmentation methods, cleaning processes, and CSV file combination instructions. The full prose was not returned.)

## Data Collection

The most important part of any machine learning model is the correctly labeled data. The amount of data required for an effective model depends on the use-case maturity requirements. For a Proof of Concept (PoC), you can collect 3-5 minutes of data per each gesture with 1-5 unique individuals. A production grade model will require significantly more data in terms of variability. The more unique users contribute to the training dataset, the better the model generalizes to new, unseen users.

For capturing data and monitoring the operations, use the Serial Monitor tool (**Serial Terminal app**) of the [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-Desktop/Download?lang=en#infotabs) app suite.

The serial terminal applies its own default buffering settings, which may need adjustment depending on your sampling rate and the duration of your recording session. You can modify these settings in the **Settings** tab.

For reference, the demo project uses a sampling frequency of 100 Hz. With a buffer limit of 100,000 lines, the terminal can store approximately 1000 seconds of data before it starts overwriting older samples.

## Recording sessions

1.  Set **Baud rate** to `115200` in a **Serial settings** tab on the left side of the window.

2.  With the port disconnected, **Clear the console** to ensure no residual data remains.

3.  **Connect to the port** and begin performing the gestures.

    Perform the gesture repeatedly for 5 minutes, and follow these guidelines to ensure high-quality data collection:

    *   Hold still for 3–5 seconds after starting.
    *   Perform the gesture for 1–2 seconds.
    *   Pause for approximately 1 second between gestures.
    *   Vary speed, orientation, and intensity.

4.  Once finished, click **Disconnect from the port**, and **Write to File** to store the captured data. Save the recorded data to a CSV file.

5.  Repeat these steps for each gesture.

## Gesture execution

> [not retrieved]
>
> (Anchor body did not load beyond navigation. Partial signal from the page: it references a "Making gestures" documentation page located elsewhere. No verbatim gesture-execution prose was returned.)

## Labeling data after recording

After collecting data for a specific class in a separate file, add a `class` column to the dataset with a constant integer representing that class. Additionally, ensure that the sensor reading columns are properly named.

1.  Open the CSV in VS Code, Excel, LibreOffice, or Python.
2.  Add a `class` column.
3.  Name sensor reading columns as follows:

    *   `acc_x`
    *   `acc_y`
    *   `acc_z`
    *   `gyro_x`
    *   `gyro_y`
    *   `gyro_z`
4.  Label each row according to your gestures.

    For example:

    ```
    acc_x,acc_y,acc_z,gyro_x,gyro_y,gyro_z,class
    0.1,0.0,9.8,0.02,0.01,0.00,0
    -0.2,0.5,9.7,0.04,0.05,0.02,0
    -0.3,0.6,9.7,0.05,0.06,0.03,0
    ```

    Where `0` is the `IDLE` gesture.

    ```
    acc_x,acc_y,acc_z,gyro_x,gyro_y,gyro_z,class
    0.2,0.0,9.8,0.02,0.01,0.08,1
    -0.14,0.5,9.7,0.04,0.05,0.01,1
    -0.3,0.6,9.7,3.05,0.09,0.03,1
    ```

    Where `1` is the `UNKNOWN` gesture.

5.  Proceed with labeling all 8 gesture classes:

    *   Swipe right: `2`
    *   Swipe left: `3`
    *   Double knock: `4`
    *   Double thumb tap: `5`
    *   Rotation clockwise: `6`
    *   Rotation counter-clockwise: `7`

    **Note:** Classes must start from `0`. For example, if you are training a model to predict `swipe`, `rotate`, `tap`, encode them as `0`, `1`, `2`. Save the encoding dictionary for future reference.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- The Neuton machine learning model identifies eight (8) gesture categories: Swipe right, Swipe left, Double shake, Double thumb tap, Rotation clockwise, Rotation counter-clockwise, No gestures (IDLE), Unknown gestures.
- The Thingy:53 device connects to a PC via Bluetooth as a HID device.
- For a Proof of Concept (PoC), collect 3-5 minutes of data per each gesture with 1-5 unique individuals.
- The demo project uses a sampling frequency of 100 Hz.
- With a buffer limit of 100,000 lines, the terminal can store approximately 1000 seconds of data before it starts overwriting older samples.
- Set Baud rate to 115200 in the Serial settings tab.
- Perform the gesture repeatedly for 5 minutes per recording session.
- Hold still for 3-5 seconds after starting.
- Perform the gesture for 1-2 seconds.
- Pause for approximately 1 second between gestures.
- Vary speed, orientation, and intensity during data collection.
- Save the recorded data to a CSV file (use Write to File after Disconnect from the port).
- Add a `class` column to the dataset with a constant integer representing that class.
- Name sensor reading columns exactly: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z.
- The CSV column order in the examples is: acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, class (7 columns).
- Class label 0 is the IDLE gesture.
- Class label 1 is the UNKNOWN gesture.
- Class encodings: Swipe right = 2, Swipe left = 3, Double knock = 4, Double thumb tap = 5, Rotation clockwise = 6, Rotation counter-clockwise = 7.
- There are 8 gesture classes to label.
- Classes must start from 0; encode contiguously (e.g., swipe=0, rotate=1, tap=2). Save the encoding dictionary for future reference.
- Example accelerometer values are around 9.7-9.8 on the acc_z axis (consistent with gravity in m/s^2 units).
- Required software (from intro): VS Code, nRF Connect for VS Code, and nRF Connect for Desktop (Serial Terminal app used for capture).

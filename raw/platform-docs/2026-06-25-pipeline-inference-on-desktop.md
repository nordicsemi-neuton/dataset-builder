# RAW SOURCE — Pipeline: Run Inference on Desktop (commands, CSV reading settings)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p1 slug=pipeline-inference-on-desktop fetch_ok=True
> - pass=p2 slug=inference-on-desktop fetch_ok=True anchors=5/5

---

<!-- source segment: pass=p1 slug=pipeline-inference-on-desktop fetch_ok=True -->

# Run inference on desktop

> Source: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html
> Part of: Edge AI Lab > Model creating pipeline
> Tags: edge-ai-lab

This page describes how to use the nRF Edge AI Desktop Inference Runner to validate model inference results on your desktop without deploying to an edge device.

The nRF Edge AI Desktop Inference Runner enables validation of model inference without deploying to edge devices. This executable is found in the artifacts folder of your downloaded trained solution.

The inference runner is an executable that contains your user-specific Nordic Edge AI Lab solution. You can find it in the downloadable archive of your trained solution, inside the `artifacts` folder. The following platform-specific builds are available:

- `nrf_edgeai_inference_runner_linux` — Linux-based systems (for example, Ubuntu 20.04).
- `nrf_edgeai_inference_runner_win` — 64-bit Windows-based systems.
- `nrf_edgeai_inference_runner_mac` — x86 macOS-based systems.

**Note**

For Axon-built models, only `nrf_edgeai_inference_runner_linux` is currently supported.

---

## Sub-sections of this page (separate child pages / anchors)

The following sub-sections are listed in the navigation under "Run inference on desktop". Their detailed content (command syntax, flags, arguments, and the CSV reading options) is NOT rendered inline on this page — each loads as its own child page/anchor. They are recorded here so the actual CSV-reading and command details can be fetched from these child URLs:

- **Available commands** — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html/available-commands?contentId=mD1~Y1Cxc~71k0OcoZPqZA
- **Getting solution information** — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html/getting-solution-information?contentId=wmaQCDdxTV0GXg6wopjrSg
- **Running inference** — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html/running-inference?contentId=jU3JkJHp~6kg09rPXBskzQ
- **Getting metrics** — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html/getting-metrics?contentId=eVs1~ySanXsN6prNf4TqxQ
- **Customizing CSV file reading settings** — https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/run_inference_on_the_desktop.html/customizing-csv-file-reading-settings?contentId=z7DqGf6ZCJSdi51eCyYsKw

---

## Capture note

Three separate WebFetch calls against this exact URL were made (full-content prompt, hard-data-requirements prompt, and raw-text/per-heading prompt). All three returned the same inline body: the introductory paragraph plus the three platform-specific executable names and the Axon note. No command syntax, no command-line flags/arguments, no CSV reading options table, and no CSV/data-format requirements (encoding, delimiter, decimal separator, file size, row/sample counts, column names/order, target column, timestamp column, sensor axes, sampling rate, window size, sliding shift, sub-windowing, value ranges, NaN handling, number of classes, samples per class, class balance, session/group IDs, holdout split) appear inline on this page. Those details live on the child pages listed above (and related pages such as "Dataset requirements", "Session ID", and "Holdout validation" under the same pipeline section).

---

<!-- source segment: pass=p2 slug=inference-on-desktop fetch_ok=True anchors=5/5 -->

# Run Inference on Desktop

## Available Commands

The inference runner provides a CLI interface for executing various commands. To see the help text, run the executable without any arguments:

```
.\artifacts\inference_runner>nrf_edgeai_inference_runner_linux

DESCRIPTION
    NRF EdgeAI Inference Runner Executable

SYNOPSIS
    nrf_edgeai_inference_runner_win.exe info
    nrf_edgeai_inference_runner_win.exe inference <dataset> [-t <target>] [-n <session>] [-d <delimiter>] [-s <filename>]
    nrf_edgeai_inference_runner_win.exe metrics <dataset> [-t <target>] [-n <session>] [-d <delimiter>] [-s <filename>]

OPTIONS
    info                      print EdgeAI Lab solution info
    
    inference
        <dataset>             filename of the user dataset
        -t, --target          set the dataset target column name ('target' by default)
        -sn, --session        set the dataset session column name ('session' by default)
        -d, --delimiter       set the dataset delimiter [comma|semicolon|tab|caret|vbar] ('comma' by default)
        -s, --save            save the inference results to the <filename>
    
    metrics
        <dataset>             filename of the user dataset with target
        -t, --target          set the dataset target column name ('target' by default)
        -sn, --session        set the dataset session column name ('session' by default)
        -d, --delimiter       set the dataset delimiter [comma|semicolon|tab|caret|vbar] ('comma' by default)

LICENSE
    Copyright (c) 2021 Nordic Semiconductor ASA.
```

## Getting Solution Information

Use the `info` command to view the Edge AI Lab solution information compiled into the inference runner:

```
.\artifacts\inference_runner>nrf_edgeai_inference_runner_linux info
       Solution name: My_Solution
     Model bit depth: 16 bits
       Float support: 1
           Task type: Binary classification
          Input type: float
Unique inputs count: 10
         Window size: 1
  Input scaling type: unified
       Outputs count: 2
       Neurons count: 11
     Model NVM usage: 241 bytes
```

## Running Inference

Use the `inference` command to run inference on a provided CSV dataset. Two dataset formats are supported: CSV text files (`.csv`) and Edge AI Lab dataset binary files (`.bin`). The CSV dataset must have a header and contain only number fields separated by commas.

The inference result is printed to the screen. To save the results to a CSV file, use the `-s <filename>` (or `--save <filename>`) parameter.

```
.\artifacts\inference_runner>nrf_edgeai_inference_runner_linux inference test.csv
.\artifacts\inference_runner>nrf_edgeai_inference_runner_linux inference test.csv -s result.csv
```

## Getting metrics

Use the `metrics` command to calculate validation metrics. This capability only works when the provided dataset contains target values. The dataset must include a header with a target column named `target`.

```
.\artifacts\inference_runner>nrf_edgeai_inference_runner_linux metrics test.csv
```

## Customizing CSV File Reading Settings

When using a CSV file as a dataset, you can customize the delimiter character, target column name, and session column name if they differ from the default values (`,`, `target`, and `session` respectively). Specify these as additional parameters when calling the `inference` or `metrics` command.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-d`, `--delimiter` | Specifies the delimiter character. Supported keywords: `comma` (`,`), `semicolon` (`;`), `tab` (`\t`), `caret` (`^`), `vbar` (`\|`). | `nrf_edgeai_inference_runner_linux inference test.csv -d tab` |
| `-t`, `--target` | Specifies the target column name of the provided dataset. | `nrf_edgeai_inference_runner_linux inference test.csv -t label` |
| `-sn`, `--session` | Specifies the session column name of the provided dataset. | `nrf_edgeai_inference_runner_linux inference test.csv -sn testee` |

---

## Extracted hard requirements (key_facts, verbatim from capture)

- The nRF Edge AI Desktop Inference Runner enables validation of model inference without deploying to edge devices.
- The inference runner executable is found in the `artifacts` folder of your downloaded trained solution.
- `nrf_edgeai_inference_runner_linux` is for Linux-based systems (for example, Ubuntu 20.04).
- `nrf_edgeai_inference_runner_win` is for 64-bit Windows-based systems.
- `nrf_edgeai_inference_runner_mac` is for x86 macOS-based systems.
- For Axon-built models, only `nrf_edgeai_inference_runner_linux` is currently supported.
- The `inference` command default target column name is `target`.
- The `inference` command default session column name is `session`.
- The `inference` command default delimiter is `comma`.
- The `-d`/`--delimiter` option supports the keywords: comma|semicolon|tab|caret|vbar.
- The delimiter keyword `comma` maps to the character `,`.
- The delimiter keyword `semicolon` maps to the character `;`.
- The delimiter keyword `tab` maps to the character `\t`.
- The delimiter keyword `caret` maps to the character `^`.
- The delimiter keyword `vbar` maps to the character `|`.
- The `-t`/`--target` option sets the dataset target column name (`target` by default).
- The `-sn`/`--session` option sets the dataset session column name (`session` by default).
- The `-s`/`--save` option saves the inference results to the specified <filename>.
- Two dataset formats are supported for inference: CSV text files (`.csv`) and Edge AI Lab dataset binary files (`.bin`).
- The CSV dataset must have a header and contain only number fields separated by commas.
- The `metrics` command only works when the provided dataset contains target values, and the dataset must include a header with a target column named `target`.
- Solution info example reports Model bit depth: 16 bits.
- Solution info example reports Float support: 1.
- Solution info example reports Task type: Binary classification.
- Solution info example reports Input type: float.
- Solution info example reports Unique inputs count: 10.
- Solution info example reports Window size: 1.
- Solution info example reports Input scaling type: unified.
- Solution info example reports Outputs count: 2.
- Solution info example reports Neurons count: 11.
- Solution info example reports Model NVM usage: 241 bytes.

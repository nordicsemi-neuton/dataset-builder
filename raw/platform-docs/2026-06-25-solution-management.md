# RAW SOURCE — Solution Management

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/solution_management.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=solution-management fetch_ok=True anchors=2/3

---

<!-- source segment: pass=p2 slug=solution-management fetch_ok=True anchors=2/3 -->

# Solution Management: user interface, solution information, managing solutions

## User interface

> [not retrieved]

## Solution information

In the information area, you can find the following details about each solution:

* **Technology** — Selected technology for the solution (Neuton or Axon)
* **Task Type** — Type of problem the solution addresses (Regression, Binary Classification, Multiclass Classification, Anomaly Detection, or Wake Word)
* **Signal Processing** — Indicator of whether the Signal Processing option for this solution was enabled or not
* **Data Type** — Selected input data type
* **Sessions** — A number of sessions that were launched for the solution (available only for LiteRT framework, since the Neuton framework allows only one session per solution)
* **Created** — Date and time when a solution was created

There are the following possible solution statuses:

* **Created** — If you specified a name for your solution and saved it.
* **Dataset configured** — If solution was created and dataset was specified.
* **Training in progress** — If model is in the training process.
* **Training completed** — If model was successfully created.
* **Training stopped** — If you stop the training manually or if the stoppage is triggered by the settings, such as reaching a specific accuracy or time limit.
* **Training cancelled** — If you cancel the training manually for Wake Word Task Type.

## Managing the solutions

In the control area, you can find the following control buttons and indicators:

- **Solution Details** — By clicking this option, you will be redirected to the screen with the current solution stage: training dataset selection, data preprocessing configuration, model training, or results.
- **Settings menu** — By clicking the gear icon on any solution you can rename the solution, delete, or copy it.
- **Solution_ID** — This is a unique solution number.

Solutions can be managed with the following actions:

- **Rename Solution** — To rename a solution, click the gear icon on the solution you would like to rename, then click **Rename**. You can specify the new **Solution name** and **Description**.
- **Delete Solution** — To delete a solution, click the gear icon associated with the solution that should be deleted, then click **Delete**. The platform will ask to confirm if the solution and all associated data in Dataset Storage are to be permanently deleted. Once confirmed, this cannot be undone.
- **Copy Solution** — To copy a solution, click the gear icon next to the desired solution and select **Copy**. This will create a new solution using the same training pipeline settings as the original (copying is not available for Wake Word Task Type).

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Technology for a solution is one of: Neuton or Axon.
- Task Type is one of: Regression, Binary Classification, Multiclass Classification, Anomaly Detection, or Wake Word.
- The Sessions count is available only for the LiteRT framework.
- The Neuton framework allows only one session per solution.
- Possible solution statuses are: Created, Dataset configured, Training in progress, Training completed, Training stopped, and Training cancelled.
- Training stopped status occurs if you stop training manually or if stoppage is triggered by settings such as reaching a specific accuracy or time limit.
- Training cancelled status applies if you cancel the training manually for Wake Word Task Type.
- Deleting a solution permanently deletes the solution and all associated data in Dataset Storage, and once confirmed it cannot be undone.
- Copying a solution creates a new solution using the same training pipeline settings as the original.
- Copying a solution is not available for Wake Word Task Type.

# RAW SOURCE — Analytics Tools (data analysis, model quality, FIM, confusion matrix)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/analytics_tools.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=analytics-tools fetch_ok=True anchors=4/4

---

<!-- source segment: pass=p2 slug=analytics-tools fetch_ok=True anchors=4/4 -->

# Analytics Tools: data analysis, model quality diagram, FIM, confusion matrix

## Data Analysis

The data analysis tool automates examination of processed training data and its connection to target variables. A report generates during model training for each solution. Given the potentially broad feature space, up to 20 of the most important features with the highest statistical significance are selected based on machine learning modeling.

To access this tool, navigate to the **Model Training** tab and select the **Data Analysis** button.

**Note:** The final model might show a slightly different feature set with the highest importance due to comprehensive iterations during training. This can create discrepancies between features selected for data analysis and the final Feature Importance Matrix.

### Sections

| Section | Description |
|---------|-------------|
| Dataset overview | Displays brief statistics of your training dataset, including problem type, dataset dimensions, missing values, and record count. |
| Continuous data distribution and relation to the target variable | Visualizes each continuous variable using two plots: **Variable density distribution chart** — A density plot visualizing data distribution across all rows using kernel smoothing to produce smoother distributions. **Feature relation to the target variable** — Presented as either a line chart showing continuous variable changes with continuous target variables (regression) or a histogram showing mean variable values for each target class (classification). |
| Feature correlations | Visualizes correlations using two plots: **Heatmap** — Displays binary correlation of the 10 most important variables with each other and the target variable. **Histogram (horizontal)** — Displays high mutual correlation between independent variable pairs exceeding 0.7. |
| Target variable distribution | Visualizes target variable statistics as either a **Violin plot** (regression) displaying distribution, median, and outliers, or a **Histogram/count plot** (classification) showing number and percentage of each target class. |
| Outliers | Visualizes outliers through a scatter plot illustrating individual data point distribution relative to the target variable (regression task type). |

## Model Quality Diagram

The **Model Quality Diagram** streamlines the evaluation of model quality by assessing all metric values on a 0 to 1 scale, where 1 indicates maximum accuracy.

This visualization tool also reveals metric balance for your selected model. When the displayed figure approximates a regular polygon's shape, it suggests healthy equilibrium across all metric indicators.

![Model Quality Diagram visualization showing metric balance assessment]

The diagram aids in understanding how well different performance metrics are balanced against one another, helping practitioners identify potential weaknesses in model performance across multiple dimensions.

## Feature Importance Matrix (FIM)

After model training completes, the platform displays a chart showing the 10 features with the most significant impact on the model's prediction of the target variable. This chart appears in the **Results** tab.

### Purpose

The Feature Importance Matrix helps you assess how individual features influence model predictions. Features with a normalized value of 0 have no effect on the model and can be excluded from future model development.

### Controls

The FIM interface provides three main controls:

- **Top 10/Bottom 10** — Displays either the 10 most or least important features
- **Select features** — Allows you to choose or deselect specific features for analysis
- **Classes** — Filters which classes appear in the bar chart (available only for classification tasks)

## Confusion Matrix

The **Confusion Matrix** visualization displays "the number of correct and incorrect predictions based on the validation data for the selected model."

This tool is available in the **Results** tab exclusively for solutions utilizing a classification task type.

The matrix provides a clear breakdown of model prediction accuracy by comparing expected versus actual classifications across your validation dataset.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- The data analysis report selects up to 20 of the most important features with the highest statistical significance based on machine learning modeling.
- To access the data analysis tool, navigate to the Model Training tab and select the Data Analysis button.
- The Feature correlations Heatmap displays binary correlation of the 10 most important variables with each other and the target variable.
- The Feature correlations Histogram (horizontal) displays high mutual correlation between independent variable pairs exceeding 0.7.
- The Model Quality Diagram assesses all metric values on a 0 to 1 scale, where 1 indicates maximum accuracy.
- When the Model Quality Diagram figure approximates a regular polygon's shape, it suggests healthy equilibrium across all metric indicators.
- After model training completes, the Feature Importance Matrix displays a chart showing the 10 features with the most significant impact on the model's prediction of the target variable, appearing in the Results tab.
- Features with a normalized value of 0 have no effect on the model and can be excluded from future model development.
- The FIM Top 10/Bottom 10 control displays either the 10 most or least important features.
- The FIM Classes control filters which classes appear in the bar chart and is available only for classification tasks.
- The Confusion Matrix is available in the Results tab exclusively for solutions utilizing a classification task type.

# RAW SOURCE — Pipeline: Data Preprocessing (input type, normalization, task type, metrics)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/data_preprocessing.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=data-preprocessing-options fetch_ok=True anchors=7/7

---

<!-- source segment: pass=p2 slug=data-preprocessing-options fetch_ok=True anchors=7/7 -->

# Data Preprocessing: signal processing, input data type, normalization, task type & evaluation metrics

## Signal Processing

Signal processing enables automatic processing of your raw data, including windowing, feature extraction, and feature selection. You can flexibly adjust these settings as needed to optimize your data for training.

## Input Data Type

Choose a single **data type** for all features in your training dataset: INT8, INT16, or FLOAT32. For mixed-type datasets, choose the widest type present (for example, FLOAT32 if any value is a float).

Input data type specification allows you to optimize the preprocessing operation and reduce SRAM and NVM usage on the device, and inference time. The data of the same type must be used for prediction. You must select the correct data type, as incorrect selection of input data type may cause target metric degradation or total footprint increase.

You only need to choose one data type for the entire dataset. For example, if you have a dataset with three features and two of them are represented as INT16 while the third one is represented as FLOAT32, you should choose FLOAT32 as the data type for the entire dataset. The platform automatically determines the data type based on this logic. However, if the data type is not determined correctly, you can change it manually.

> Choosing the wrong input data type may reduce model accuracy or increase model size.

System uses the entire dataset to determine the data type:

*   **8-bit Integer** — The range of values in the dataset is from -128 to 127.
*   **16-bit Integer** — The range of values in the dataset is -32 768 to 32 767.
*   **32-bit Floating point** — At least one value in the dataset is a floating point number.

> If you selected Axon as the technology during the solution creation step, the only currently available option for the input data type is 32-bit floating point.

## Normalization Type

Set how features are scaled: **Unique scale for each feature** (increases accuracy, may increase model size) or **Unified scale for all features** (reduces size if values are already on the same scale).

If Signal Processing (SP) is enabled:

*   Features created during feature extraction are normalized within their own scale
*   Raw data is normalized within the scale of each variable and axis

## Task Type and Evaluation Metric

**Task Type**, defined at the solution creation step when using dataset-based pipelines, can be Regression, Binary Classification, Multi-class Classification, or Anomaly Detection. Select the appropriate **Metric** to assess model performance. The default metric is `Accuracy` for classification, `RMSE` for regression.

See the supported task types, and the metrics available for each one:

| Task type | Description | Available metrics |
|-----------|-------------|-------------------|
| Binary Classification | The model predicts one of two possible classes (for example, "yes/no", "healthy/unhealthy"). | Accuracy, AUC, Balanced Accuracy, F1, Gini, Lift, LogLoss, Precision, Recall |
| Multi-class Classification | The model predicts one of three or more possible categories (for example, types of activities, types of events). | Accuracy, Balanced Accuracy, F1 (weighted, macro), LogLoss, Precision (weighted, macro), Recall (weighted, macro) |
| Regression | The model predicts a continuous numerical value (for example, temperature, heart rate, pressure level). | MAE, MSE, R², RMSE, RMSLE, RMSPE |
| Anomaly Detection | The model identifies unusual patterns or outliers that do not conform to expected behavior (for example, detecting faults in machinery, gear shifts in sensor data). | Reconstruction Accuracy |

## Classification Metrics

The following metrics apply to binary classification, multi-class classification, or both:

| Metric | Description | Use case |
|--------|-------------|----------|
| Accuracy | The fraction of correct predictions out of all predictions. For example, 73 out of 100 correct predictions gives an accuracy of 0.73. Higher is better. Does not account for class imbalance. | When classes have similar sample sizes. |
| AUC | Area Under the ROC Curve. Measures how well a binary classifier separates classes. Ranges from 0 to 1, where 1.0 is perfect and 0.5 is no better than random. | When you need an overall measure of binary classification quality. |
| Balanced Accuracy | The average accuracy across all classes. Compensates for class imbalance by weighting each class equally. | When classes are imbalanced. |
| F1 Score | The harmonic mean of Precision and Recall. Ranges from 0 (worst) to 1 (best). | When you need a balance between Precision and Recall, especially with imbalanced data. |
| F1 (macro) | Computes the F1 score independently for each class and averages without weights. Does not account for class imbalance. | When all classes are equally important regardless of size. |
| F1 (weighted) | Computes the F1 score per class and averages weighted by class support. | When classes are imbalanced. |
| Gini | Measures overall predictive power in binary classification by ranking samples by likelihood of belonging to the positive class. A value of 0% means no ability to distinguish between classes. | When you need to evaluate ranking quality in imbalanced datasets. |
| Lift | Measures how much better the model predicts positive cases compared to random chance. A value greater than 1 means the model outperforms random selection. | When identifying top-performing cases is critical. |
| LogLoss | Measures the confidence of predictions by comparing predicted probabilities with actual class labels. Lower is better. Considers prediction probabilities rather than rounded class labels. | When prediction confidence matters, not just the final class label. |
| Precision | The fraction of relevant samples among retrieved samples. Ranges from 0 to 1. | When minimizing false positives is important, even if some relevant samples are missed. |
| Precision (macro) | Computes precision independently for each class and averages without weights. | When all classes are equally important regardless of size. |
| Precision (weighted) | Computes precision per class and averages weighted by class support. | When classes are imbalanced. |
| Recall | The fraction of relevant samples found out of all relevant samples. Ranges from 0 to 1. | When capturing as many relevant samples as possible is important, even if some false positives occur. |
| Recall (macro) | Computes recall independently for each class and averages without weights. | When all classes are equally important regardless of size. |
| Recall (weighted) | Computes recall per class and averages weighted by class support. | When classes are imbalanced. |

## Regression Metrics

The following metrics apply to regression tasks:

| Metric | Description | Use case |
|--------|-------------|----------|
| MAE | "Mean Absolute Error. The average absolute difference between predicted and actual values." Direction of error does not matter. | When you want to minimize average prediction error. |
| MSE | "Mean Squared Error. The average of squared differences between predicted and actual values." Always non-negative, lower is better. Penalizes large errors more strongly. | When large individual errors should be penalized. |
| R² | "Coefficient of Determination. Measures the proportion of variance in the target variable explained by the model." A value of 1 means perfect predictions, 0 means no explanatory power. | When you want to know how well the model explains the variance in the data. |
| RMSE | "Root Mean Squared Error. The square root of MSE. Lower is better." | When large individual errors should be penalized heavily. |
| RMSLE | "Root Mean Squared Logarithmic Error. Lower is better." Penalizes underestimates more than overestimates. | When large differences between high-value predictions should be penalized less. |
| RMSPE | "Root Mean Squared Percentage Error. Measures percentage error between predicted and actual values." Lower is better. Rows with 0 in the target variable are excluded. | When you need errors expressed as percentages. |
| Max AE | "Maximum Absolute Error. The largest absolute difference between predicted and actual values." | When you want to understand the maximum possible deviation. |
| Min AE | "Minimum Absolute Error. The smallest absolute difference between predicted and actual values." It indicates the best-case prediction accuracy for individual samples. | When you want to see how close the model can get to perfect predictions. |

## Anomaly Detection Metrics

The following metric applies to anomaly detection tasks:

| Metric | Description | Use case |
|--------|-------------|----------|
| Reconstruction Accuracy | "Measures how well the model can recreate the input data. The model learns normal data patterns and identifies anomalies based on reconstruction errors." | Anomaly detection tasks. |

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Input data type must be a single data type for all features in the training dataset: INT8, INT16, or FLOAT32.
- For mixed-type datasets, choose the widest type present (for example, FLOAT32 if any value is a float).
- 8-bit Integer (INT8) input data type applies when the range of values in the dataset is from -128 to 127.
- 16-bit Integer (INT16) input data type applies when the range of values in the dataset is -32 768 to 32 767.
- 32-bit Floating point (FLOAT32) input data type applies when at least one value in the dataset is a floating point number.
- The platform automatically determines the data type; if it is not determined correctly, you can change it manually.
- If Axon was selected as the technology during the solution creation step, the only currently available input data type option is 32-bit floating point.
- Incorrect selection of input data type may cause target metric degradation or total footprint increase, and may reduce model accuracy or increase model size.
- Normalization Type options are: Unique scale for each feature (increases accuracy, may increase model size) or Unified scale for all features (reduces size if values are already on the same scale).
- If Signal Processing (SP) is enabled, features created during feature extraction are normalized within their own scale, and raw data is normalized within the scale of each variable and axis.
- Task Type is defined at the solution creation step when using dataset-based pipelines and can be Regression, Binary Classification, Multi-class Classification, or Anomaly Detection.
- The default evaluation metric is Accuracy for classification and RMSE for regression.
- Binary Classification available metrics: Accuracy, AUC, Balanced Accuracy, F1, Gini, Lift, LogLoss, Precision, Recall.
- Multi-class Classification available metrics: Accuracy, Balanced Accuracy, F1 (weighted, macro), LogLoss, Precision (weighted, macro), Recall (weighted, macro).
- Regression available metrics: MAE, MSE, R², RMSE, RMSLE, RMSPE.
- Anomaly Detection available metric: Reconstruction Accuracy.
- Multi-class Classification predicts one of three or more possible categories.
- Binary Classification predicts one of two possible classes.
- AUC ranges from 0 to 1, where 1.0 is perfect and 0.5 is no better than random.
- F1 Score ranges from 0 (worst) to 1 (best).
- Gini value of 0% means no ability to distinguish between classes.
- Lift value greater than 1 means the model outperforms random selection.
- Precision ranges from 0 to 1; Recall ranges from 0 to 1.
- R² value of 1 means perfect predictions, 0 means no explanatory power.
- RMSE is the square root of MSE; lower is better.
- RMSPE excludes rows with 0 in the target variable.
- Signal processing performs windowing, feature extraction, and feature selection on raw data.

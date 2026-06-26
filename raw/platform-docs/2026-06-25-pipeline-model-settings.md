# RAW SOURCE — Pipeline: Model Settings (bit depth, output format, target hw, training params, architecture, layers)

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/model_creating_pipeline/model_settings.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=model-settings-core fetch_ok=True anchors=6/7
> - pass=p2 slug=model-settings-architecture fetch_ok=True anchors=7/7

---

<!-- source segment: pass=p2 slug=model-settings-core fetch_ok=True anchors=6/7 -->

# Model Settings: new session, bit depth, output format, training stop, target hardware, LiteRT, training parameters

## Starting a New Session

Start by entering a session name. The training framework (Neuton or LiteRT) is preselected automatically based on the technology defined during the Solution Creation step. You can then adjust the available settings as needed.

## Weights and Coefficients (Bit Depth)

Select the storage format for model **coefficients and weights**: 8-bit, 16-bit, or 32-bit. Lower bit depths (8 or 16) help minimize model size and optimize device resource usage. For 8-bit and 16-bit storage, calculations can be performed in both floats and integers. For 32-bit storage, only floats are used. By default, this setting matches your dataset type, but you can adjust it as needed.

**Note:** When the LiteRT framework is used, the value is predefined to 32-bit floating point and cannot be changed. Training uses 32-bit floating point, but the final model is quantized.

## Output Format

Choose how the model **outputs prediction results**: quantized (integer) or floating point. The following options are available:

*   **Quantized 8-bit** — Probabilities from 0 to 255.
*   **Quantized 16-bit** — Probabilities from 0 to 65,535.
*   **Floating-point 32-bit** — Probabilities from 0 to 1.

Quantized format is only available when quantized weights and coefficients are selected. For 32-bit (floating-point) weights, only floating-point output is available and cannot be changed.

![Output format](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/OY5PCZg1IongDS3o2G5beQ-aNQtRTyvjlJdHnUOv1c8sw/content?v=1376e0067df3c1dc)

**Note**

When the LiteRT framework is used, the value is predefined to 32-bit probabilities and cannot be changed.

## Training Stop Options

Control model complexity and training time using the following options:

* **Maximum Number of Coefficients** — Limits the number of coefficients in the model. By default, this is unlimited.
* **Maximum Training Duration (hours)** — Limits training time. The best model is saved automatically if the time limit is reached.
* **Maximum Value of Evaluation Metric** — Training stops once the specified metric value is reached, if achievable for your data.

**Note:** Training stop options are not available for the Axon technology (LiteRT framework).

## Target Hardware

Select one or more **hardware targets** for model deployment. Supported options include **Cortex-M0**, **Cortex-M4**, and **Cortex-M33**, covering the entire Nordic wireless SoC lineup. The platform automatically optimizes model conversion and code generation based on the selected hardware.

![Target hardware](https://docs.nordicsemi.com/api/khub/maps/aNQtRTyvjlJdHnUOv1c8sw/resources/FrHJo85JJfHmt9rbtVmJRg-aNQtRTyvjlJdHnUOv1c8sw/content?v=467b1e01b922cfef)

**Note:** When the LiteRT framework is used, the target hardware is predefined to Axon NPU and cannot be changed.

## LiteRT model settings

> [not retrieved]
>
> (Intro fragment present in fetched content: "When using the LiteRT framework for Axon NPU model creation, the following additional settings are available:" — the substantive body that follows this introduction was not returned after one retry with a directive prompt.)

## Training Parameters

- **Epochs** — Number of times the full dataset is used during training. Higher values can improve learning but may increase training time.

- **Batch size** — Number of samples processed at once during training. Affects training speed and memory usage.

- **Epochs without improvement** — Controls early stopping. Defines how many epochs to wait before stopping if the validation metric does not improve.

- **Learning rate** — Controls the step size during learning. Small steps result in slower but more careful learning, while large steps are faster but riskier. The value must be between 0 and 1.

(An image labeled "LiteRT training parameters" is referenced in the original content.)

---

<!-- source segment: pass=p2 slug=model-settings-architecture fetch_ok=True anchors=7/7 -->

# Model Settings: architecture, presets, layers (core, convolutional, pooling)

## Model architecture

The model architecture defines how data flows through the neural network and how patterns are learned from the input features. It consists of different types of layers, each serving a specific purpose in feature transformation and pattern extraction.

The section also includes a visual diagram labeled "Model architecture" that illustrates these concepts.

## Architecture presets

The platform provides predefined architecture presets that let you quickly configure a neural network without manually assembling layers. The following presets are available:

* **Fully Connected Preset** — A fully connected architecture composed of multiple Dense layers with intermediate Dropout layers. This preset is designed to improve generalization by reducing overfitting while maintaining strong learning capacity.

* **Simple Fully Connected Preset** — A compact architecture consisting of three stacked Dense layers with decreasing numbers of neurons. This preset is suitable for simpler tasks or scenarios where a lightweight model is preferred.

## Input and output layers

### Input Layer

The **Input Layer** indicates the quantity of input features supplied to the model during each inference cycle. This value is computed automatically based on:

- Dataset columns
- Enabled signal processing features
- Window settings
- Feature selection configuration

When you modify preprocessing or feature settings, this value refreshes automatically. Manual configuration of the input layer is not necessary. Increasing input features may enhance model accuracy but also expands model size and memory consumption, which matters for devices with restricted resources.

### Output Layer

The **Output Layer** specifies the final prediction structure. This setup is determined automatically according to your task type:

- **Regression**: 1 neuron (linear activation)
- **Binary classification**: 1 neuron (softmax)
- **Multi-class classification**: N neurons (softmax), where N equals the number of classes

The output layer is configured automatically and aligns with your chosen task.

## Adding and configuring layers

Besides using presets, you can build a custom architecture by adding and configuring layers manually. To add a layer, click the **+ Add Layer** button and select the desired layer type.

[Image: Add Layer button interface]

## Core layers

Core layers are the fundamental building blocks of the network. They are responsible for learning relationships between features, shaping data flow, and controlling model complexity.

| Layer | Description | Parameters |
|-------|-------------|-----------|
| Dense | A fully connected layer that links every input to every output through learnable weights. | **Neurons** — Number of neurons in this layer.<br>**Activation** — Function applied to the output. Available options: Linear, ReLU, Sigmoid, Tanh. |
| Dropout | Randomly disables a fraction of neurons during training to reduce overfitting. | **Rate** — Fraction of neurons that are randomly deactivated during training (for example, 0.2 means 20%). |
| Flatten | Converts multi-dimensional data into a one-dimensional vector to match the input requirements of the next layer. | No parameters required. |
| Reshape | Changes the shape of the input data to ensure compatibility with subsequent layers. | No parameters required. |

## Convolutional layers

Convolutional layers extract meaningful patterns from sequential or time-series data. They apply learnable filters across the input to detect local structures and important signal characteristics.

| Layer | Description | Parameters |
|-------|-------------|------------|
| Conv1D | Creates feature maps using convolutional filters to highlight important patterns in sequential or time-series data. | **Filters** — Number of convolutional filters (feature detectors) in this layer.<br><br>**Kernel Size** — Size of the sliding window (filter) used to extract features.<br><br>**Activation** — Function applied to the output. Available options: Linear, ReLU, Sigmoid, Softmax, Tanh. |

## Pooling layers

Pooling layers reduce the dimensionality of feature maps produced by convolutional layers. They summarize information within a region or across the entire sequence, helping improve efficiency and generalization.

| Layer | Description | Parameters |
|-------|-------------|------------|
| MaxPooling1D | Retains the maximum value within each window, reducing the size of feature maps while preserving their number. | **Pool Size** — Size of the pooling window. |

Once you have configured the model settings and architecture, you are ready to start training. See the Model Results section to learn how to initiate training and evaluate model performance.

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Weights and coefficients (bit depth) options are: 8-bit, 16-bit, or 32-bit.
- For 8-bit and 16-bit storage, calculations can be performed in both floats and integers.
- For 32-bit storage, only floats are used.
- By default, the bit depth setting matches your dataset type.
- When the LiteRT framework is used, the bit depth value is predefined to 32-bit floating point and cannot be changed.
- Under LiteRT, training uses 32-bit floating point, but the final model is quantized.
- Output format Quantized 8-bit gives probabilities from 0 to 255.
- Output format Quantized 16-bit gives probabilities from 0 to 65,535.
- Output format Floating-point 32-bit gives probabilities from 0 to 1.
- Quantized output format is only available when quantized weights and coefficients are selected.
- For 32-bit (floating-point) weights, only floating-point output is available and cannot be changed.
- When the LiteRT framework is used, the output format is predefined to 32-bit probabilities and cannot be changed.
- Maximum Number of Coefficients limits the number of coefficients in the model; by default this is unlimited.
- Maximum Training Duration is specified in hours; the best model is saved automatically if the time limit is reached.
- Maximum Value of Evaluation Metric stops training once the specified metric value is reached, if achievable for your data.
- Training stop options are not available for the Axon technology (LiteRT framework).
- Supported target hardware options include Cortex-M0, Cortex-M4, and Cortex-M33.
- When the LiteRT framework is used, the target hardware is predefined to Axon NPU and cannot be changed.
- The training framework (Neuton or LiteRT) is preselected automatically based on the technology defined during the Solution Creation step.
- Learning rate value must be between 0 and 1.
- Epochs without improvement controls early stopping by defining how many epochs to wait before stopping if the validation metric does not improve.
- Architecture presets: Fully Connected Preset is a fully connected architecture composed of multiple Dense layers with intermediate Dropout layers, designed to improve generalization by reducing overfitting while maintaining strong learning capacity.
- Architecture presets: Simple Fully Connected Preset is a compact architecture consisting of three stacked Dense layers with decreasing numbers of neurons, suitable for simpler tasks or scenarios where a lightweight model is preferred.
- The Input Layer value is computed automatically based on dataset columns, enabled signal processing features, window settings, and feature selection configuration; manual configuration is not necessary.
- Output Layer for Regression: 1 neuron (linear activation).
- Output Layer for Binary classification: 1 neuron (softmax).
- Output Layer for Multi-class classification: N neurons (softmax), where N equals the number of classes.
- To add a layer, click the + Add Layer button and select the desired layer type.
- Dense layer parameters: Neurons (number of neurons in this layer) and Activation with available options Linear, ReLU, Sigmoid, Tanh.
- Dropout layer parameter: Rate — fraction of neurons randomly deactivated during training (for example, 0.2 means 20%).
- Flatten layer requires no parameters.
- Reshape layer requires no parameters.
- Conv1D layer parameters: Filters (number of convolutional filters), Kernel Size (size of the sliding window used to extract features), and Activation with available options Linear, ReLU, Sigmoid, Softmax, Tanh.
- MaxPooling1D layer parameter: Pool Size — size of the pooling window; it retains the maximum value within each window, reducing feature map size while preserving their number.

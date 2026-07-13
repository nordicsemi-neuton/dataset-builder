---
type: discovery
status: active
updated: 2026-07-10
sources:
  - ../../raw/platform-docs/2026-06-25-neural-network-framework.md
  - ../../raw/platform-docs/2026-06-25-overview-neuton-axon-workflow.md
  - ../../raw/platform-docs/2026-06-25-welcome-overview-domains.md
  - owner-supplied platform knowledge (10.07.2026, direct, not in the doc bundle)
tags: [platform, neuton, neural-network, framework, background]
---

# platform — The Neuton neural-network framework

Background on *why* the platform produces tiny models. Not a data-preparation rule, but it explains the platform's automation and minimal-input philosophy (data + target + metric → done).

## The idea

Neuton is a patented NN framework by Nordic Semiconductor. Instead of a fixed architecture trained with backpropagation/stochastic gradient descent, **Neuton grows the network neuron by neuron** using a **patented global optimization algorithm**. The minimum structural unit during optimization is the **neuron's input**, giving fine-grained growth and very compact networks. Networks expand with **built-in overfitting control**, adding neurons until maximum generalization, then stopping.

## Why traditional approaches fall short (per the docs)

- Modern NNs use huge parameter counts; building them is manual tuning of random seed, #neurons, #layers, activation, learning rate, #epochs, CV folds, dropout.
- Size-reduction approaches each have costs: **pruning** shrinks a network only *after* training a full-size one, at an accuracy cost; **NAS** trains many candidate models (resource-intensive, coarse search).
- **SGD optimization problems:** local minima / saddle points / plateaus, non-uniform parameter updates, undetermined learning rate, vanishing/exploding gradients. SGD variants (Nesterov, Adagrad, Momentum, RMSProp, Adadelta, Adam, Adamax) mitigate but don't fully solve these.

## Neuton vs NAS (as stated)

| Criterion | Neuton | NAS |
|---|---|---|
| Architecture | Automatic neuron-by-neuron growth | Search over candidate structures |
| Size optimized | **During** training | Before/after training |
| Optimizer | Proprietary global optimization | Gradient descent |
| Accuracy loss from size reduction | **No** | Possible |
| Manual hyperparameter tuning | **Not required** | Required |
| Built-in overfitting control | **Yes** | No |
| Training cost | Free (via Edge AI Lab) | Very high |

**Consequence for data prep:** the only required inputs are **the data, a target variable, and a metric**; "training, validation, and model selection all happen automatically." So the entire burden on the user (and our tool) is **getting the dataset right** — which is exactly what [the dataset contract](../architecture/platform-dataset-requirements.md) specifies. The contrast is the **Axon NPU / LiteRT** path, which *does* expose manual architecture/training settings → [overview](platform-overview.md), [deployment](../architecture/platform-deployment-inference.md).

## Observed in practice: the metric is evaluation-only, not a training input

The phrase above ("data, a target variable, and a metric") reads as if the metric were fed into the
optimizer alongside the data — it isn't. **Neuton's internal optimization always minimizes cross-entropy
loss; the selected metric (Accuracy, Balanced Accuracy, F1, …) is computed for reporting/model-comparison
only and never changes what the network learns or when growth stops.** Concretely: switching from Accuracy
to Balanced Accuracy before a retrain will not make the model try harder on a small/weak class — it will
only make the *existing* result easier to read correctly (a small-class improvement can be invisible in
plain Accuracy against big background classes). Don't advise a metric change as a fix for a training
outcome; advise it for correctly evaluating one. See [domain P-13](../principles/domain.md).
**Source:** owner-supplied platform knowledge (10.07.2026), direct, not from the doc bundle — flagged here
because the doc bundle's own phrasing is what led to the wrong inference in the first place.

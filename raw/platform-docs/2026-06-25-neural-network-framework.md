# RAW SOURCE — Neuton Neural Network Framework

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/neural_network_framework.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=neural-network-framework fetch_ok=True anchors=3/3

---

<!-- source segment: pass=p2 slug=neural-network-framework fetch_ok=True anchors=3/3 -->

# Neuton NN Framework: traditional approaches, optimization problems, Neuton comparison

## Traditional Approaches to Building Neural Networks

Modern neural networks tend to use large numbers of coefficients and neurons, which increases processing power requirements. Models with hundreds of thousands of parameters are common. Building a neural network structure is largely a manual process that involves tuning many variables at once to find a good balance between model size and accuracy. These variables include:

* Random seed
* Number of neurons
* Number of layers
* Activation function (Sigmoid, ReLU, and others)
* Learning rate
* Number of epoches
* Cross validation folds
* Dropout

Most modern neural networks use a fixed architecture defined by the researcher and rely on stochastic gradient descent (with minor variations) to optimize neuron parameters. The architecture itself does not change during training.

Because only the parameters are optimized while the structure stays fixed, networks often end up larger than necessary. This increases prediction costs due to redundant computations within the network. Two main approaches to reducing network volume that can currently be distinguished are:

* **Optimizing the structures of already-trained networks (pruning)** — Methods that follow this approach typically work by removing neurons and connections from an already-trained network based on certain criteria. This reduces the network size but comes at the cost of accuracy. The full-size network still has to be trained first, so the size reduction only happens after training, not during it.
* **Automated neural architecture search (NAS)** — This approach generates optimized network architectures that can match or exceed the performance of manually designed architectures. In practice, most NAS methods work by evaluating a set of candidate architectures, training a full model for each one, and selecting the best result. The typical process is as follows:

This process is resource-intensive, so in practice the search space of possible architectures is heavily restricted. The result is a coarse search that often produces a less-than-optimal architecture. Cross-validation, which is needed for consistent results, multiplies this overhead further.

Another obstacle to obtaining an efficiently sized, highly accurate model is the choice of the optimization algorithm. The widely-known problem of local extremes and plateaus significantly reduces the efficiency of using stochastic gradient descent for these purposes. On top of that, results are sensitive to hyperparameters such as learning rate, batch size, and weight initialization. Determining when training is complete is also not straightforward. Together, these factors add uncertainty to each step and increase the overall cost of the process.

## Common Optimization Problems

The following are the main problems that arise when using local gradient optimization methods in neural network frameworks:

* **Getting stuck in multiple local minima or at saddle points** — The loss landscape contains both plateau regions where the gradient is near zero and strongly nonlinear regions where a sudden drop can push the search too far from the optimum.

* **Non-uniform parameter updates** — Some parameters are updated much less frequently than others, particularly when the data contains informative but rare attributes. Giving too much weight to rare attributes can lead to overfitting.

* **Undetermined learning rate** — A learning rate that is too low causes slow convergence and gets stuck in local minima. A rate that is too high skips over good minima or causes divergence.

* **Vanishing and exploding gradients** — In networks with many successive layers, the error gradient can shrink or grow uncontrollably as weight corrections propagate from the output back to the input. This reduces learning efficiency in layers located far from the output.

Major modifications of stochastic gradient descent use heuristics to address these problems. The most common ideas are accumulating momentum along the gradient and applying weaker updates for frequent attributes. These ideas have led to algorithms such as Nesterov Accelerated Gradient, Adagrad, Momentum, RMSProp, Adadelta, Adam, and Adamax. However, none of these fully solves all of the problems listed above.

Addressing these limitations requires a different approach to building neural networks — one that solves both the inefficiency of the training algorithm and the limited ability to search for an optimal architecture.

## The Neuton Approach Compared to Traditional Frameworks

Neuton takes a fundamentally different approach to building perceptron neural networks. Rather than employing fixed architectures or enumerating candidate structures like most NAS methods, "Neuton grows the network neuron by neuron." The minimum structural unit during optimization is the neuron's input, which reduces architecture search granularity and produces compact networks.

### Key Technical Differences

The platform uses "a patented global optimization algorithm to identify network parameters, which avoids the local extrema and plateau problems associated with gradient descent." This algorithm supports parallelization across multiple hosts and GPUs without accuracy loss, making cross-validation feasible within practical training timeframes.

During training, the network expands automatically with integrated overfitting controls. Neurons are added until reaching maximum generalization capability. The global optimization approach maintains neuron efficiency, constraining overall network size while preserving accuracy.

### Comparative Overview

| Criteria | Neuton | NAS |
|----------|--------|-----|
| Architecture definition | Automatic neuron-by-neuron growth | Automated search over candidate structures |
| Moment of size optimization | During training | Before or after training |
| Optimization algorithm | Proprietary (global optimization) | Gradient descent |
| Accuracy loss from size reduction | No | Possible |
| Manual hyperparameter tuning | Not required | Required |
| Built-in overfitting control | Yes | No |
| Training cost | Free (through Edge AI Lab) | Very high (multiple full trainings) |

The only required inputs are the data, a target variable, and a metric. "Training, validation, and model selection all happen automatically."

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Manually tuned neural network variables include: random seed, number of neurons, number of layers, activation function (Sigmoid, ReLU, and others), learning rate, number of epoches, cross validation folds, and dropout.
- Most modern neural networks use a fixed architecture defined by the researcher and rely on stochastic gradient descent to optimize neuron parameters; the architecture itself does not change during training.
- Two main approaches to reducing network volume are pruning (optimizing the structures of already-trained networks) and automated neural architecture search (NAS).
- Pruning reduces network size but comes at the cost of accuracy, and the full-size network must still be trained first.
- Heuristic SGD modifications include Nesterov Accelerated Gradient, Adagrad, Momentum, RMSProp, Adadelta, Adam, and Adamax; none of these fully solves all of the listed optimization problems.
- In Neuton, the minimum structural unit during optimization is the neuron's input; Neuton grows the network neuron by neuron.
- Neuton uses a patented global optimization algorithm to identify network parameters, which avoids the local extrema and plateau problems associated with gradient descent.
- Neuton's algorithm supports parallelization across multiple hosts and GPUs without accuracy loss.
- Neuton optimizes size during training, requires no manual hyperparameter tuning, has built-in overfitting control, and incurs no accuracy loss from size reduction; NAS optimizes size before or after training, requires manual hyperparameter tuning, has no built-in overfitting control, and may lose accuracy from size reduction.
- Neuton training cost is free through Edge AI Lab, whereas NAS training cost is very high (multiple full trainings).
- The only required inputs for Neuton are the data, a target variable, and a metric; training, validation, and model selection all happen automatically.

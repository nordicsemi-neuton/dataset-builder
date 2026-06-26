# RAW SOURCE — Welcome / Overview / Ready-to-use Models / Supported Application Domains

> Immutable archive copy of Nordic Edge AI Lab platform documentation. Do not edit.
> - Source URL: https://docs.nordicsemi.com/r/bundle/edge-ai-lab/page/index.html
> - Date received: 2026-06-25
> - Document publication date: [unknown]
> - Publisher/author: Nordic Semiconductor
> - Captured by: WebFetch (Cloudflare-protected Zoomin SPA; bodies fetched per-section by contentId).
> - Fidelity: bodies reproduced verbatim by the capture step; HTML entities un-escaped. Capture/provenance notes from the fetch are retained inline.
> Provenance segments:
> - pass=p2 slug=welcome-and-domains fetch_ok=True anchors=3/3
> - pass=p1 slug=overview-welcome fetch_ok=True

---

<!-- source segment: pass=p2 slug=welcome-and-domains fetch_ok=True anchors=3/3 -->

# Welcome / Overview / Ready-to-use Models / Supported Application Domains

## Overview

The neural network framework does not create models with a predefined structure. It grows the network neuron by neuron, using a unique patented algorithm to adjust coefficients within a model. This approach enables users to build tiny and accurate models without any compression techniques. As a result, the models are:

- Well-optimized
- With fewer coefficients and neurons
- Up to 10 times smaller compared to other frameworks

You can deploy Neuton's models on the smallest MCUs, where they show fast inference time. In addition to Neuton, the Nordic Edge AI Lab supports building LiteRT models for the new Axon NPU, enabling you to leverage standard deep learning architectures. The platform also adds native Wake Word support, enabling always-on, low-power voice-triggered applications for hands-free and context-aware device interaction.

The Nordic Edge AI Lab is easy to use and you do not need any special data science or embedded engineering experience. It automates the entire process of creating models for edge devices using innovative, cutting-edge technology. You can implement common TinyML tasks such as:

- Gesture recognition
- Wake word detection
- Vital sign determination
- Human-machine interfaces
- Human activity recognition
- Machine fault classification
- Asset tracking and monitoring
- Any sensor-based time series task:
  - Regression
  - Classification
  - Anomaly detection

## Ready-to-use Models

The Nordic Edge AI Lab offers a library of pre-trained AI models available for download and deployment. These models enable users to quickly prototype and integrate Edge AI capabilities into your product, without collecting data or running a training pipeline.

The platform provides access to a growing library of pre-trained AI models that you can download and deploy directly to your device, allowing developers to bypass traditional model development workflows. For the complete catalog of available models, consult the dedicated Ready-to-use Models page.

## Supported Application Domains

The Nordic Edge AI Lab supports Edge AI development across diverse sectors. Key application areas include:

**Wearable Technology**: Devices like smartwatches, smart rings, and fitness trackers requiring real-time data processing.

**Healthcare**: Portable diagnostic devices and health-monitoring tools (heart rate, oxygen levels, ECG, PPG, etc.).

**Environmental Monitoring**: Animal tracking, poaching detection, and quality assessment systems.

**Energy Management**: Smart grid solutions and smart home energy-management systems.

**Logistics & Transportation**: Package tracking, fleet optimization, and asset monitoring.

**Agriculture**: Soil analysis, crop assessment, and automated irrigation.

**Smart Home**: Smart speakers, thermostats, security cameras, and appliances benefiting from on-device processing.

**Predictive Maintenance**: Equipment monitoring for anomaly detection and failure prediction.

**Smart Cities**: Traffic management and emergency response.

**Retail**: Inventory systems and supply-chain optimization.

**Automotive**: Autonomous vehicles and driver-assistance systems (lane keeping, collision avoidance, driver monitoring).

An important constraint: Models built with the Edge AI Lab are exclusively available for Nordic wireless SoCs and deployable across their customer base as a premium offering.

---

<!-- source segment: pass=p1 slug=overview-welcome fetch_ok=True -->

# Welcome to the Nordic Edge AI Lab

> Capture note: This URL (`/r/bundle/edge-ai-lab/page/index.html`) is the entry page of a Cloudflare-protected single-page documentation viewer (Nordic / ZoominSoftware platform). The WebFetch tool successfully passed the Cloudflare JavaScript challenge and rendered the page, but on this index URL the main article column renders ONLY the page title and the lead overview paragraph below; the full table of contents (in-page navigation) is also rendered. The body prose for the deeper sub-sections — including "Ready-to-use Models" and "Supported application domains" — is lazy-loaded per topic and was NOT present in the rendered index page. Multiple alternate path/API guesses (`/page/intro.html`, `/page/overview.html`, `/page/welcome.html`, `/api/...`) returned HTTP 404, and raw `curl` is blocked by the Cloudflare challenge. The content reproduced below is verbatim and faithful to what was retrievable; the lazy-loaded sub-section bodies will need to be captured from their individual topic URLs.

## Welcome to the Nordic Edge AI Lab

tags

edge-ai-lab

Nordic Edge Ai Lab is an automated no-code platform that allows you to build extremely compact models and embed them across the wide portfolio of all Nordic Semiconductor wireless connectivity SoCs. The platform uses Nordic Semiconductor's patented neural network framework (NN), Neuton, which is built from the ground up and does not rely on any existing frameworks or non-neural algorithms.

Back to home page

---

## In-page navigation / Table of contents (verbatim)

- Welcome to the Nordic Edge AI Lab
- Overview
- Ready-to-use Models
- Supported application domains
- Overview of Nordic Edge AI Lab
- Neuton overview
- Axon overview
- Workflow
- Neuton Neural Network framework
- Traditional approaches to building neural networks
- Common optimization problems
- The Neuton approach compared to traditional frameworks
- Registration and login
- Getting started
- Use-case description
- Preparing raw dataset
- Requirements
- Setting up firmware project
- Preparing data for gesture recognition
- Data collection
- Recording sessions
- Gesture execution
- Labeling data after recording
- Data segmentation
- Data cleaning
- Combining CSV files
- Data overview
- Signing in and creating a solution
- Data preprocessing
- Enabling signal processing
- Feature extraction
- Selecting a feature
- Model training
- Defining target hardware
- Starting training
- Checking the results
- Embedding a Neuton model into firmware project
- Model tuning and improvement
- Ready-to-use models
- Prerequisites
- Exploring the model library
- Working with the model
- Solution management
- User interface
- Solution information
- Managing the solutions
- Dataset storage
- Dataset management
- Model creating pipeline
- Model creating pipeline
- Solution creation
- Dataset requirements
- Requirements for training datasets
- How to identify and change file encoding
- Data uploading and setup
- Uploading dataset
- Selecting an uploaded or preloaded dataset
- Using preloaded use cases
- Dataset options
- Session ID
- Holdout validation
- Data preprocessing
- Signal processing
- Input data type
- Normalization type
- Task type and evaluation metric
- Classification metrics
- Regression metrics
- Anomaly detection metrics
- Signal processing
- Guided setup
- Windowing
- Sliding shift
- Estimated SRAM usage
- Raw data option
- Sub-windowing
- Feature extraction
- Time-domain features
- Statistical features
- Regression features
- Crossing-rate features
- Signal shape and variation
- Hjorth parameters
- Peak-to-peak features
- Frequency-domain features
- Spectral analysis
- Dominant frequency features
- Energy ratio features
- Feature selection
- Model training
- Sessions
- Model results
- Training progress
- Processed data
- Solution options
- Model growth chart
- Performance metrics and footprint
- Downloadable model archive
- Analytics tools
- Model settings
- Starting a new session
- Weights and coefficients (bit depth)
- Output format
- Training stop options
- Target hardware
- LiteRT model settings
- Training parameters
- Model architecture
- Architecture presets
- Input and output layers
- Adding and configuring layers
- Core layers
- Convolutional layers
- Pooling layers
- Run Inference on MCU
- Inference engine
- Key features
- Run inference on desktop
- Available commands
- Getting solution information
- Running inference
- Getting metrics
- Customizing CSV file reading settings
- Wake Word Detection
- Overview
- Requirements and best practices
- Training custom wake word
- Using pre-built model (Okay Nordic)
- Results
- Live testing
- Automatic tuning
- Manual testing
- Detection settings
- Live results
- Detections and log
- Inference on device
- Anomaly detection
- Overview
- Cosine distance distribution plot
- Reconstruction accuracy
- Inference and anomaly score threshold
- Analytics tools
- Data analysis
- Model quality diagram
- Feature Importance Matrix (FIM)
- Confusion matrix

---

## Extracted hard requirements (key_facts, verbatim from capture)

- Neuton's neural network framework grows the network neuron by neuron using a patented algorithm, building tiny and accurate models without any compression techniques.
- Models produced are up to 10 times smaller compared to other frameworks.
- The Nordic Edge AI Lab supports building LiteRT models for the Axon NPU, enabling standard deep learning architectures.
- The platform adds native Wake Word support for always-on, low-power voice-triggered applications.
- Supported TinyML tasks include gesture recognition, wake word detection, vital sign determination, human-machine interfaces, human activity recognition, machine fault classification, asset tracking and monitoring, and any sensor-based time series task (regression, classification, anomaly detection).
- Models built with the Edge AI Lab are exclusively available for Nordic wireless SoCs.

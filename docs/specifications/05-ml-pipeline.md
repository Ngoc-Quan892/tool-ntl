# ML Pipeline Specification

## Overview

The ML pipeline includes:

1. **Feature Engineering**: Extract features from game history
2. **Model Training**: Train ensemble models
3. **Inference**: Real-time prediction
4. **Evaluation**: Model performance metrics

## Features

- Pattern sequences (last N hands)
- Card count metrics
- Statistical indicators
- Roadmap-derived features

## Models

- **Pattern Detector**: Rule-based pattern matching
- **Bayesian Model**: Transition probability matrix
- **Neural Network**: Small feedforward network (optional)

## Training

- Data: Historical game results
- Validation: Time-series cross-validation
- Metrics: Accuracy, Precision, Recall

## Deployment

- Models saved as `.pkl` files
- Loaded at application startup
- Updated via training scripts


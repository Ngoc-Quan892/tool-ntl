"""Configuration dataclasses for ML prediction service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModelConfig:
    """Model configuration for inference and training."""

    model_dir: Path = Path("./ml-training/models")
    checkpoint_dir: Path = Path("./ml-training/checkpoints")
    log_dir: Path = Path("./ml-training/logs")
    ensemble_size: int = 3
    device: str = "auto"  # "cpu", "cuda", or "auto"
    sequence_length: int = 30
    input_size: int = 35
    hidden_size: int = 128
    num_layers: int = 3
    dropout: float = 0.3
    attention_heads: int = 8
    batch_size: int = 32
    epochs: int = 100
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    optimizer: str = "adamw"  # adam, adamw, sgd
    lr_scheduler: str = "reduce_on_plateau"  # reduce_on_plateau, cosine, step, none
    loss_function: str = "cross_entropy"  # cross_entropy, focal_loss
    label_smoothing: float = 0.0
    early_stopping_patience: int = 10
    enable_wandb: bool = False
    wandb_project: str = "baccarat-predictor"
    wandb_run_name: Optional[str] = None

    def ensure_paths(self) -> None:
        """Ensure important directories exist."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class FeatureConfig:
    """Feature extraction configuration."""

    history_window: int = 120
    normalize_counts: bool = True
    include_temporal_features: bool = True
    include_composition_features: bool = True


@dataclass
class PerformanceConfig:
    """Performance-related configuration."""

    enable_prediction_cache: bool = True
    prediction_cache_ttl: int = 60  # seconds
    log_slow_predictions: bool = True
    slow_prediction_threshold: float = 0.2  # seconds
    max_accuracy_buffer: int = 1000



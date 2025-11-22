"""
Full PyTorch training pipeline for Baccarat prediction.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import f1_score, roc_auc_score
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from app.ml.advanced_model import BaccaratLSTM, ModelConfig as TorchModelConfig
from app.ml.config import FeatureConfig, ModelConfig
from app.ml.dataset import create_dataloaders

logger = logging.getLogger(__name__)


class FocalLoss(nn.Module):
    """Multi-class focal loss."""

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.ce = nn.CrossEntropyLoss(reduction="none")

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = self.ce(inputs, targets)
        pt = torch.exp(-ce_loss)
        focal = self.alpha * (1 - pt) ** self.gamma * ce_loss
        return focal.mean()


def create_model(config: ModelConfig, device: str) -> BaccaratLSTM:
    torch_config = TorchModelConfig(
        input_size=config.input_size,
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        dropout=config.dropout,
        attention_heads=config.attention_heads,
        sequence_length=config.sequence_length,
    )
    model = BaccaratLSTM(torch_config)
    return model.to(device)


def save_model(
    model: nn.Module,
    path: str,
    optimizer: optim.Optimizer,
    epoch: int,
    metrics: Dict[str, float],
) -> None:
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "metrics": metrics,
    }
    torch.save(checkpoint, path)
    logger.info("Checkpoint saved to %s", path)


class EarlyStopping:
    def __init__(self, patience: int = 10, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss: Optional[float] = None
        self.should_stop = False

    def __call__(self, val_loss: float) -> bool:
        if self.best_loss is None or val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        return self.should_stop


class MetricTracker:
    def __init__(self):
        self.metrics: Dict[str, list] = {
            "train_loss": [],
            "val_loss": [],
            "train_acc": [],
            "val_acc": [],
            "val_f1": [],
            "val_auc": [],
        }

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if key in self.metrics:
                self.metrics[key].append(value)

    def save(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.metrics, handle, indent=2)


class BaccaratTrainer:
    def __init__(
        self,
        model: BaccaratLSTM,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: ModelConfig,
        device: str,
    ):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = torch.device(device)
        self.model.to(self.device)
        self.metric_tracker = MetricTracker()
        self.early_stopping = EarlyStopping(config.early_stopping_patience)
        self.writer = SummaryWriter(config.log_dir / f"run_{datetime.utcnow():%Y%m%d_%H%M%S}")
        self.wandb_run = self._init_wandb()
        self._setup_training_components()

    def _init_wandb(self):
        if not self.config.enable_wandb:
            return None
        try:
            import wandb

            wandb.init(
                project=self.config.wandb_project,
                name=self.config.wandb_run_name,
                config=self.config.__dict__,
            )
            return wandb
        except Exception as exc:  # pragma: no cover - optional
            logger.warning("Failed to init Weights & Biases: %s", exc)
            return None

    def _setup_training_components(self) -> None:
        dataset: Dataset = self.train_loader.dataset  # type: ignore[assignment]
        if self.config.loss_function == "focal_loss":
            self.criterion = FocalLoss()
        else:
            weights = dataset.get_class_weights().to(self.device)
            self.criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=self.config.label_smoothing)

        if self.config.optimizer == "adam":
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
        elif self.config.optimizer == "sgd":
            self.optimizer = optim.SGD(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
                momentum=0.9,
            )
        else:
            self.optimizer = optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )

        if self.config.lr_scheduler == "reduce_on_plateau":
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer, mode="min", factor=0.5, patience=5, verbose=True
            )
        elif self.config.lr_scheduler == "cosine":
            self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=self.config.epochs)
        elif self.config.lr_scheduler == "step":
            self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=20, gamma=0.5)
        else:
            self.scheduler = None

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        self.model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        progress = tqdm(self.train_loader, desc=f"Train {epoch+1}/{self.config.epochs}")
        for step, (inputs, targets) in enumerate(progress):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            self.optimizer.zero_grad()
            outputs, confidence = self.model(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            if step % 10 == 0:
                self.writer.add_scalar("train/batch_loss", loss.item(), epoch * len(self.train_loader) + step)
            progress.set_postfix(loss=f"{loss.item():.4f}", acc=f"{100 * correct / total:.2f}%")

        avg_loss = running_loss / len(self.train_loader)
        accuracy = 100 * correct / max(total, 1)
        return {"loss": avg_loss, "accuracy": accuracy}

    def validate(self) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        all_preds: List[int] = []
        all_targets: List[int] = []
        all_probs: List[List[float]] = []
        with torch.no_grad():
            for inputs, targets in self.val_loader:
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                outputs, confidence = self.model(inputs)
                loss = self.criterion(outputs, targets)
                total_loss += loss.item()
                probs = torch.softmax(outputs, dim=1)
                _, predicted = probs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                all_preds.extend(predicted.cpu().tolist())
                all_targets.extend(targets.cpu().tolist())
                all_probs.extend(probs.cpu().tolist())

        avg_loss = total_loss / len(self.val_loader)
        accuracy = 100 * correct / max(total, 1)
        f1 = f1_score(all_targets, all_preds, average="weighted")
        try:
            auc = roc_auc_score(all_targets, all_probs, multi_class="ovr")
        except ValueError:
            auc = 0.0
        return {"loss": avg_loss, "accuracy": accuracy, "f1": f1, "auc": auc}

    def train(self) -> Dict[str, float]:
        best_val_acc = 0.0
        best_epoch = 0
        best_metrics: Dict[str, float] = {}
        self.config.ensure_paths()

        for epoch in range(self.config.epochs):
            train_metrics = self.train_epoch(epoch)
            val_metrics = self.validate()
            current_lr = self.optimizer.param_groups[0]["lr"]

            self.writer.add_scalar("train/loss", train_metrics["loss"], epoch)
            self.writer.add_scalar("train/accuracy", train_metrics["accuracy"], epoch)
            self.writer.add_scalar("val/loss", val_metrics["loss"], epoch)
            self.writer.add_scalar("val/accuracy", val_metrics["accuracy"], epoch)
            self.writer.add_scalar("val/f1", val_metrics["f1"], epoch)
            self.writer.add_scalar("val/auc", val_metrics["auc"], epoch)
            self.writer.add_scalar("learning_rate", current_lr, epoch)

            if self.wandb_run:
                self.wandb_run.log(
                    {
                        "train/loss": train_metrics["loss"],
                        "train/accuracy": train_metrics["accuracy"],
                        "val/loss": val_metrics["loss"],
                        "val/accuracy": val_metrics["accuracy"],
                        "val/f1": val_metrics["f1"],
                        "val/auc": val_metrics["auc"],
                        "lr": current_lr,
                        "epoch": epoch,
                    }
                )

            self.metric_tracker.update(
                train_loss=train_metrics["loss"],
                val_loss=val_metrics["loss"],
                train_acc=train_metrics["accuracy"],
                val_acc=val_metrics["accuracy"],
                val_f1=val_metrics["f1"],
                val_auc=val_metrics["auc"],
            )

            if self.scheduler:
                if isinstance(self.scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_metrics["loss"])
                else:
                    self.scheduler.step()

            if val_metrics["accuracy"] > best_val_acc:
                best_val_acc = val_metrics["accuracy"]
                best_epoch = epoch
                best_metrics = val_metrics
                save_model(
                    self.model,
                    str(self.config.model_dir / "baccarat_lstm_best.pth"),
                    self.optimizer,
                    epoch,
                    val_metrics,
                )

            if (epoch + 1) % 10 == 0:
                save_model(
                    self.model,
                    str(self.config.checkpoint_dir / f"checkpoint_epoch_{epoch+1}.pth"),
                    self.optimizer,
                    epoch,
                    val_metrics,
                )

            if self.early_stopping(val_metrics["loss"]):
                logger.info("Early stopping triggered at epoch %s", epoch + 1)
                break

        final_path = self.config.model_dir / "baccarat_lstm_final.pth"
        save_model(self.model, str(final_path), self.optimizer, best_epoch, best_metrics)
        self.metric_tracker.save(self.config.model_dir / "training_metrics.json")
        self.writer.close()
        if self.wandb_run:
            self.wandb_run.finish()
        return {"best_val_acc": best_val_acc, "best_epoch": best_epoch}


def train_model(
    train_data_path: str,
    val_data_path: str,
    config: ModelConfig,
    device: str = "cuda",
) -> Dict[str, float]:
    feature_config = FeatureConfig()
    train_loader, val_loader = create_dataloaders(
        train_data_path,
        val_data_path,
        feature_config,
        config,
        batch_size=config.batch_size,
    )
    device_to_use = device
    if device_to_use == "auto":
        device_to_use = "cuda" if torch.cuda.is_available() else "cpu"
    model = create_model(config, device_to_use)
    trainer = BaccaratTrainer(model, train_loader, val_loader, config, device_to_use)
    return trainer.train()
"""
Training pipeline for ML models.

This module provides:
- Data preparation
- Model training
- Evaluation metrics
- Model saving and versioning
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .model import LSTMPredictor, FeatureEngineer
from .versioning import ModelVersionManager


# ==================== DATA PREPARATION ====================

def prepare_training_data(
    outcomes: List[List[str]],
    labels: List[str],
    sequence_length: int = 30,
    test_size: float = 0.2,
    validation_size: float = 0.1
) -> Tuple[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]:
    """
    Prepare training data from outcomes and labels.
    
    Args:
        outcomes: List of outcome sequences
        labels: List of labels ('B' or 'P')
        sequence_length: Length of sequences
        test_size: Test set size ratio
        validation_size: Validation set size ratio
        
    Returns:
        Tuple of (train_data, val_data, test_data)
    """
    feature_engineer = FeatureEngineer(sequence_length=sequence_length)
    
    X_sequence = []
    X_stat = []
    y = []
    
    for seq, label in zip(outcomes, labels):
        if len(seq) < 2:
            continue
        
        seq_feat, stat_feat = feature_engineer.extract_features(seq)
        seq_feat = seq_feat.reshape(-1, 1)
        
        X_sequence.append(seq_feat)
        X_stat.append(stat_feat)
        
        # Encode label
        if label == 'B':
            y.append([1.0, 0.0])
        elif label == 'P':
            y.append([0.0, 1.0])
        else:
            continue  # Skip ties
    
    X_sequence = np.array(X_sequence)
    X_stat = np.array(X_stat)
    y = np.array(y, dtype=np.float32)
    
    # Split data
    from sklearn.model_selection import train_test_split
    
    # First split: train+val vs test
    X_seq_train_val, X_seq_test, X_stat_train_val, X_stat_test, y_train_val, y_test = train_test_split(
        X_sequence, X_stat, y, test_size=test_size, random_state=42
    )
    
    # Second split: train vs val
    X_seq_train, X_seq_val, X_stat_train, X_stat_val, y_train, y_val = train_test_split(
        X_seq_train_val, X_stat_train_val, y_train_val,
        test_size=validation_size / (1 - test_size), random_state=42
    )
    
    train_data = ((X_seq_train, X_stat_train), y_train)
    val_data = ((X_seq_val, X_stat_val), y_val)
    test_data = ((X_seq_test, X_stat_test), y_test)
    
    return train_data, val_data, test_data


# ==================== EVALUATION METRICS ====================

def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray
) -> Dict[str, float]:
    """
    Calculate evaluation metrics.
    
    Args:
        y_true: True labels (one-hot encoded)
        y_pred: Predicted labels (one-hot encoded)
        y_proba: Predicted probabilities
        
    Returns:
        Dictionary of metrics
    """
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
    
    # Convert to class labels
    y_true_labels = np.argmax(y_true, axis=1)
    y_pred_labels = np.argmax(y_pred, axis=1)
    
    accuracy = accuracy_score(y_true_labels, y_pred_labels)
    precision = precision_score(y_true_labels, y_pred_labels, average='weighted', zero_division=0)
    recall = recall_score(y_true_labels, y_pred_labels, average='weighted', zero_division=0)
    f1 = f1_score(y_true_labels, y_pred_labels, average='weighted', zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_true_labels, y_pred_labels)
    
    # Per-class metrics
    if len(np.unique(y_true_labels)) == 2:
        precision_banker = precision_score(y_true_labels, y_pred_labels, pos_label=0, zero_division=0)
        recall_banker = recall_score(y_true_labels, y_pred_labels, pos_label=0, zero_division=0)
        precision_player = precision_score(y_true_labels, y_pred_labels, pos_label=1, zero_division=0)
        recall_player = recall_score(y_true_labels, y_pred_labels, pos_label=1, zero_division=0)
    else:
        precision_banker = precision_player = recall_banker = recall_player = 0.0
    
    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'precision_banker': float(precision_banker),
        'recall_banker': float(recall_banker),
        'precision_player': float(precision_player),
        'recall_player': float(recall_player),
        'confusion_matrix': cm.tolist()
    }


# ==================== TRAINING PIPELINE ====================

class ModelTrainer:
    """
    Training pipeline for LSTM models.
    """
    
    def __init__(
        self,
        models_dir: str = "ml-training/models",
        version_manager: Optional[ModelVersionManager] = None
    ):
        """
        Initialize trainer.
        
        Args:
            models_dir: Directory to save models
            version_manager: Model version manager
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.version_manager = version_manager or ModelVersionManager()
    
    def train(
        self,
        train_data: Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray],
        val_data: Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray],
        test_data: Tuple[Tuple[np.ndarray, np.ndarray], np.ndarray],
        hyperparameters: Dict[str, Any],
        version: Optional[str] = None,
        description: Optional[str] = None,
        save_model: bool = True
    ) -> Dict[str, Any]:
        """
        Train LSTM model.
        
        Args:
            train_data: Training data
            val_data: Validation data
            test_data: Test data
            hyperparameters: Model hyperparameters
            version: Model version identifier
            description: Model description
            save_model: Whether to save model
            
        Returns:
            Training results dictionary
        """
        # Create model
        model = LSTMPredictor(
            sequence_length=hyperparameters.get('sequence_length', 30),
            lstm_units=hyperparameters.get('lstm_units', 64),
            dense_units=hyperparameters.get('dense_units', 32),
            dropout_rate=hyperparameters.get('dropout_rate', 0.2),
            learning_rate=hyperparameters.get('learning_rate', 0.001)
        )
        model.build_model()
        
        # Prepare data
        (X_seq_train, X_stat_train), y_train = train_data
        (X_seq_val, X_stat_val), y_val = val_data
        (X_seq_test, X_stat_test), y_test = test_data
        
        # Train
        print(f"Training model with {len(y_train)} samples...")
        history = model.train(
            X_seq_train,
            X_stat_train,
            y_train,
            validation_split=0.0,  # Already split
            epochs=hyperparameters.get('epochs', 50),
            batch_size=hyperparameters.get('batch_size', 32),
            verbose=1
        )
        
        # Evaluate on validation set
        val_pred_proba = model.model.predict([X_seq_val, X_stat_val], verbose=0)
        val_pred = np.argmax(val_pred_proba, axis=1)
        val_pred_onehot = np.eye(2)[val_pred]
        
        val_metrics = calculate_metrics(y_val, val_pred_onehot, val_pred_proba)
        
        # Evaluate on test set
        test_pred_proba = model.model.predict([X_seq_test, X_stat_test], verbose=0)
        test_pred = np.argmax(test_pred_proba, axis=1)
        test_pred_onehot = np.eye(2)[test_pred]
        
        test_metrics = calculate_metrics(y_test, test_pred_onehot, test_pred_proba)
        
        # Generate version if not provided
        if version is None:
            from datetime import datetime
            version = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Save model
        model_path = None
        if save_model:
            model_path = str(self.models_dir / version)
            model.save(model_path)
            print(f"Model saved to {model_path}")
        
        # Register version
        self.version_manager.register_version(
            version=version,
            model_path=model_path or str(self.models_dir / version),
            accuracy=test_metrics['accuracy'],
            precision=test_metrics['precision'],
            recall=test_metrics['recall'],
            f1_score=test_metrics['f1_score'],
            training_samples=len(y_train),
            validation_samples=len(y_test),
            hyperparameters=hyperparameters,
            description=description,
            is_production=False
        )
        
        return {
            'version': version,
            'model_path': model_path,
            'training_history': history,
            'validation_metrics': val_metrics,
            'test_metrics': test_metrics,
            'hyperparameters': hyperparameters
        }
    
    def train_from_sequences(
        self,
        sequences: List[List[str]],
        labels: List[str],
        hyperparameters: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train model from sequences and labels.
        
        Args:
            sequences: List of outcome sequences
            labels: List of labels
            hyperparameters: Model hyperparameters
            version: Model version
            description: Model description
            
        Returns:
            Training results
        """
        if hyperparameters is None:
            hyperparameters = {
                'sequence_length': 30,
                'lstm_units': 64,
                'dense_units': 32,
                'dropout_rate': 0.2,
                'learning_rate': 0.001,
                'epochs': 50,
                'batch_size': 32
            }
        
        # Prepare data
        train_data, val_data, test_data = prepare_training_data(
            sequences,
            labels,
            sequence_length=hyperparameters.get('sequence_length', 30)
        )
        
        # Train
        return self.train(
            train_data,
            val_data,
            test_data,
            hyperparameters,
            version=version,
            description=description
        )


"""
Entry-point script for training the Baccarat ML model.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

from app.ml.config import ModelConfig
from app.ml.dataset import prepare_training_data
from app.ml.trainer import train_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("train")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Baccarat prediction model")
    parser.add_argument("--data", type=str, required=True, help="Path to raw CSV data")
    parser.add_argument("--output-dir", type=str, default="./ml-training/models", help="Model output directory")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"], help="Training device")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare train/val splits")
    parser.add_argument("--enable-wandb", action="store_true", help="Enable Weights & Biases logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Using device: %s", device)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Preparing train/val splits...")
    train_path, val_path = prepare_training_data(args.data, output_dir / "data")

    if args.prepare_only:
        logger.info("Data preparation complete.")
        return

    config = ModelConfig()
    config.model_dir = output_dir
    config.checkpoint_dir = output_dir / "checkpoints"
    config.log_dir = output_dir / "logs"
    config.epochs = args.epochs
    config.batch_size = args.batch_size
    config.learning_rate = args.lr
    config.device = device
    config.enable_wandb = args.enable_wandb
    config.ensure_paths()

    logger.info("Starting training...")
    results = train_model(train_path, val_path, config, device)
    logger.info("Training finished. Best val acc: %.2f%% (epoch %s)", results["best_val_acc"], results["best_epoch"])


if __name__ == "__main__":
    main()


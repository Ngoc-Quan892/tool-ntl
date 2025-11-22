"""
PyTorch dataset utilities for Baccarat prediction.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from app.ml.features import FeatureExtractor
from app.ml.config import FeatureConfig, ModelConfig

logger = logging.getLogger(__name__)


class BaccaratSequenceDataset(Dataset):
    """Dataset that builds sliding-window sequences from Baccarat hands."""

    def __init__(
        self,
        data_path: str,
        feature_extractor: FeatureExtractor,
        sequence_length: int = 30,
        stride: int = 1,
        augment: bool = True,
        max_samples: Optional[int] = None,
    ):
        self.feature_extractor = feature_extractor
        self.sequence_length = sequence_length
        self.stride = stride
        self.augment = augment
        df = self._load_data(data_path)
        self.sequences = self._create_sequences(df, max_samples=max_samples)
        logger.info("Dataset built with %s sequences (%s)", len(self.sequences), data_path)

    def _load_data(self, data_path: str) -> pd.DataFrame:
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        if path.suffix == ".csv":
            df = pd.read_csv(path)
        elif path.suffix in {".pkl", ".pickle"}:
            df = pd.read_pickle(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        required_cols = ["result", "shoe_id"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if "hand_number" in df.columns:
            df = df.sort_values(["shoe_id", "hand_number"])
        else:
            df = df.sort_values(["shoe_id"]).reset_index(drop=True)

        return df

    def _create_sequences(self, df: pd.DataFrame, max_samples: Optional[int]) -> List[Dict[str, any]]:
        sequences: List[Dict[str, any]] = []
        for shoe_id, shoe_df in df.groupby("shoe_id"):
            outcomes = shoe_df["result"].tolist()
            if len(outcomes) <= self.sequence_length:
                continue

            for start in range(0, len(outcomes) - self.sequence_length):
                if start % self.stride != 0:
                    continue
                history = outcomes[start : start + self.sequence_length]
                target = outcomes[start + self.sequence_length]
                shoe_state = self._get_shoe_state(shoe_df, start + self.sequence_length)
                sequences.append(
                    {
                        "history": history,
                        "target": target,
                        "shoe_state": shoe_state,
                        "shoe_id": shoe_id,
                        "index": start,
                    }
                )
                if max_samples and len(sequences) >= max_samples:
                    return sequences
        return sequences

    def _get_shoe_state(self, shoe_df: pd.DataFrame, idx: int) -> Dict[str, any]:
        row = shoe_df.iloc[min(idx, len(shoe_df) - 1)]
        shoe_state = {
            "cards_remaining": row.get("cards_remaining", 416 - idx * 6),
            "true_count_b": row.get("true_count_b", 0.0),
            "true_count_p": row.get("true_count_p", 0.0),
            "running_count_b": row.get("running_count_b", 0.0),
            "running_count_p": row.get("running_count_p", 0.0),
            "decks_remaining": row.get("decks_remaining", 8.0),
            "hands_played": row.get("hand_number", idx),
            "edge": {"max_edge": row.get("max_edge", 0.0)},
        }
        if "composition" in row:
            shoe_state["composition"] = row["composition"]
        return shoe_state

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        seq = self.sequences[idx]
        try:
            features = self.feature_extractor.extract_all_features(seq["shoe_state"], seq["history"])
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Feature extraction failed (idx=%s): %s", idx, exc)
            features = np.zeros((self.sequence_length, 35), dtype=np.float32)

        if self.augment:
            features = self._augment_features(features)

        target_map = {"B": 0, "P": 1, "T": 2}
        target = target_map.get(seq["target"], 0)
        return torch.tensor(features, dtype=torch.float32), torch.tensor(target, dtype=torch.long)

    def _augment_features(self, features: np.ndarray) -> np.ndarray:
        augmented = features.copy()
        noise = np.random.normal(0, 0.01, augmented.shape)
        augmented += noise
        if np.random.random() < 0.3:
            mask = np.random.rand(*augmented.shape) > 0.1
            augmented *= mask
        return np.clip(augmented, -10, 10)

    def get_class_weights(self) -> torch.Tensor:
        counts = Counter(seq["target"] for seq in self.sequences)
        total = sum(counts.values())
        weights = {
            "B": total / (counts.get("B", 1) * 3),
            "P": total / (counts.get("P", 1) * 3),
            "T": total / (counts.get("T", 1) * 3),
        }
        weight_tensor = torch.tensor([weights["B"], weights["P"], weights["T"]], dtype=torch.float32)
        logger.info("Class distribution %s | weights %s", counts, weights)
        return weight_tensor

    def get_statistics(self) -> Dict[str, any]:
        counts = Counter(seq["target"] for seq in self.sequences)
        return {
            "total_sequences": len(self.sequences),
            "unique_shoes": len({seq["shoe_id"] for seq in self.sequences}),
            "class_distribution": dict(counts),
            "sequence_length": self.sequence_length,
            "stride": self.stride,
        }


def create_dataloaders(
    train_path: str,
    val_path: str,
    feature_config: FeatureConfig,
    model_config: ModelConfig,
    batch_size: int = 32,
    num_workers: int = 4,
    pin_memory: bool = True,
) -> Tuple[DataLoader, DataLoader]:
    extractor = FeatureExtractor(feature_config)
    train_dataset = BaccaratSequenceDataset(
        train_path,
        extractor,
        sequence_length=model_config.sequence_length,
        stride=1,
        augment=True,
    )
    val_dataset = BaccaratSequenceDataset(
        val_path,
        extractor,
        sequence_length=model_config.sequence_length,
        stride=1,
        augment=False,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )

    logger.info("Train batches: %s | Val batches: %s", len(train_loader), len(val_loader))
    return train_loader, val_loader


def prepare_training_data(
    csv_path: str,
    output_dir: str,
    train_ratio: float = 0.8,
    random_seed: int = 42,
) -> Tuple[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path)
    shoes = df["shoe_id"].unique()
    rng = np.random.default_rng(random_seed)
    rng.shuffle(shoes)
    split_idx = int(len(shoes) * train_ratio)
    train_shoes = shoes[:split_idx]
    val_shoes = shoes[split_idx:]
    train_df = df[df["shoe_id"].isin(train_shoes)]
    val_df = df[df["shoe_id"].isin(val_shoes)]
    train_path = output_path / "train.csv"
    val_path = output_path / "val.csv"
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    logger.info(
        "Prepared data -> Train: %s hands (%s shoes), Val: %s hands (%s shoes)",
        len(train_df),
        len(train_shoes),
        len(val_df),
        len(val_shoes),
    )
    return str(train_path), str(val_path)


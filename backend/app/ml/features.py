"""Feature extractor wrapper used by predictors and training pipeline."""

from __future__ import annotations

from typing import Optional

from app.ml.advanced_model import FeatureExtractor as AdvancedFeatureExtractor
from app.ml.config import FeatureConfig


class FeatureExtractor(AdvancedFeatureExtractor):
    """Thin wrapper that keeps a reference to feature config."""

    def __init__(self, config: Optional[FeatureConfig] = None):
        super().__init__()
        self.config = config or FeatureConfig()



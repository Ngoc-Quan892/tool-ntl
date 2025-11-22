"""
Model versioning system for ML models.

This module provides:
- Model version management
- Version metadata tracking
- Model registry
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ModelVersion:
    """Model version metadata."""
    version: str
    model_path: str
    created_at: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_samples: int
    validation_samples: int
    hyperparameters: Dict[str, Any]
    description: Optional[str] = None
    is_active: bool = False
    is_production: bool = False


class ModelVersionManager:
    """
    Manage ML model versions.
    
    Tracks model versions, metadata, and provides
    version selection and loading.
    """
    
    def __init__(self, registry_path: str = "ml-training/models/registry.json"):
        """
        Initialize version manager.
        
        Args:
            registry_path: Path to version registry file
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.versions: Dict[str, ModelVersion] = {}
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load version registry from file."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for version, version_data in data.items():
                        self.versions[version] = ModelVersion(**version_data)
            except Exception as e:
                print(f"Error loading registry: {e}")
                self.versions = {}
        else:
            self.versions = {}
    
    def _save_registry(self) -> None:
        """Save version registry to file."""
        data = {
            version: asdict(v) for version, v in self.versions.items()
        }
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_version(
        self,
        version: str,
        model_path: str,
        accuracy: float,
        precision: float,
        recall: float,
        f1_score: float,
        training_samples: int,
        validation_samples: int,
        hyperparameters: Dict[str, Any],
        description: Optional[str] = None,
        is_production: bool = False
    ) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            version: Version identifier
            model_path: Path to model file
            accuracy: Model accuracy
            precision: Model precision
            recall: Model recall
            f1_score: F1 score
            training_samples: Number of training samples
            validation_samples: Number of validation samples
            hyperparameters: Model hyperparameters
            description: Optional description
            is_production: Whether this is production version
            
        Returns:
            ModelVersion instance
        """
        # If setting as production, unset other production versions
        if is_production:
            for v in self.versions.values():
                v.is_production = False
        
        model_version = ModelVersion(
            version=version,
            model_path=model_path,
            created_at=datetime.utcnow().isoformat(),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            training_samples=training_samples,
            validation_samples=validation_samples,
            hyperparameters=hyperparameters,
            description=description,
            is_active=True,
            is_production=is_production
        )
        
        self.versions[version] = model_version
        self._save_registry()
        
        return model_version
    
    def get_version(self, version: str) -> Optional[ModelVersion]:
        """
        Get version by identifier.
        
        Args:
            version: Version identifier
            
        Returns:
            ModelVersion or None
        """
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """
        Get latest version identifier.
        
        Returns:
            Latest version string or None
        """
        if not self.versions:
            return None
        
        # Get version with latest created_at
        latest = max(
            self.versions.values(),
            key=lambda v: v.created_at
        )
        return latest.version
    
    def get_production_version(self) -> Optional[str]:
        """
        Get production version identifier.
        
        Returns:
            Production version string or None
        """
        for version, model_version in self.versions.items():
            if model_version.is_production:
                return version
        return None
    
    def get_model_path(self, version: str) -> Optional[str]:
        """
        Get model file path for version.
        
        Args:
            version: Version identifier
            
        Returns:
            Model file path or None
        """
        model_version = self.get_version(version)
        if model_version:
            return model_version.model_path
        return None
    
    def list_versions(self) -> List[ModelVersion]:
        """
        List all registered versions.
        
        Returns:
            List of ModelVersion instances
        """
        return list(self.versions.values())
    
    def set_production(self, version: str) -> bool:
        """
        Set version as production.
        
        Args:
            version: Version identifier
            
        Returns:
            True if successful
        """
        model_version = self.get_version(version)
        if model_version:
            # Unset other production versions
            for v in self.versions.values():
                v.is_production = False
            
            model_version.is_production = True
            self._save_registry()
            return True
        return False
    
    def deactivate_version(self, version: str) -> bool:
        """
        Deactivate a version.
        
        Args:
            version: Version identifier
            
        Returns:
            True if successful
        """
        model_version = self.get_version(version)
        if model_version:
            model_version.is_active = False
            self._save_registry()
            return True
        return False
    
    def delete_version(self, version: str) -> bool:
        """
        Delete a version from registry.
        
        Args:
            version: Version identifier
            
        Returns:
            True if successful
        """
        if version in self.versions:
            del self.versions[version]
            self._save_registry()
            return True
        return False


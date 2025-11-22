#!/usr/bin/env python3
"""
Train ML models for Baccarat prediction.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import pandas as pd
import argparse
from typing import List, Optional

from app.ml.trainer import ModelTrainer
from app.ml.versioning import ModelVersionManager


def load_training_data(filepath: str) -> tuple[List[List[str]], List[str]]:
    """
    Load training data from CSV file.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Tuple of (sequences, labels)
    """
    df = pd.read_csv(filepath)
    
    sequences = []
    labels = []
    
    for _, row in df.iterrows():
        seq_str = row['sequence']
        seq = seq_str.split(',')
        label = row['label']
        
        sequences.append(seq)
        labels.append(label)
    
    print(f"Loaded {len(sequences)} sequences from {filepath}")
    return sequences, labels


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Train ML model')
    parser.add_argument('--data', type=str, default='ml-training/data/training_data.csv',
                       help='Training data file path')
    parser.add_argument('--version', type=str, help='Model version identifier')
    parser.add_argument('--description', type=str, help='Model description')
    parser.add_argument('--sequence-length', type=int, default=30,
                       help='Sequence length')
    parser.add_argument('--lstm-units', type=int, default=64,
                       help='LSTM units')
    parser.add_argument('--dense-units', type=int, default=32,
                       help='Dense units')
    parser.add_argument('--dropout-rate', type=float, default=0.2,
                       help='Dropout rate')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                       help='Learning rate')
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--models-dir', type=str, default='ml-training/models',
                       help='Models directory')
    
    args = parser.parse_args()
    
    print("🤖 Training ML model...")
    print(f"   Data: {args.data}")
    print(f"   Sequence length: {args.sequence_length}")
    print(f"   LSTM units: {args.lstm_units}")
    print(f"   Epochs: {args.epochs}")
    
    # Load data
    if not Path(args.data).exists():
        print(f"Error: Data file not found: {args.data}")
        print("Run prepare_data.py first to generate training data")
        return
    
    sequences, labels = load_training_data(args.data)
    
    if len(sequences) < 100:
        print(f"Warning: Only {len(sequences)} sequences. Consider generating more data.")
    
    # Hyperparameters
    hyperparameters = {
        'sequence_length': args.sequence_length,
        'lstm_units': args.lstm_units,
        'dense_units': args.dense_units,
        'dropout_rate': args.dropout_rate,
        'learning_rate': args.learning_rate,
        'epochs': args.epochs,
        'batch_size': args.batch_size
    }
    
    # Initialize trainer
    trainer = ModelTrainer(models_dir=args.models_dir)
    
    # Train
    try:
        results = trainer.train_from_sequences(
            sequences=sequences,
            labels=labels,
            hyperparameters=hyperparameters,
            version=args.version,
            description=args.description
        )
        
        print("\n✅ Training complete!")
        print(f"   Version: {results['version']}")
        print(f"   Model path: {results['model_path']}")
        print(f"\nTest Metrics:")
        test_metrics = results['test_metrics']
        print(f"   Accuracy: {test_metrics['accuracy']:.4f}")
        print(f"   Precision: {test_metrics['precision']:.4f}")
        print(f"   Recall: {test_metrics['recall']:.4f}")
        print(f"   F1 Score: {test_metrics['f1_score']:.4f}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

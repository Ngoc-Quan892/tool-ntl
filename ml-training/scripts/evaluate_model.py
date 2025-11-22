#!/usr/bin/env python3
"""
Evaluate trained ML models.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import argparse
from app.ml.model import LSTMPredictor
from app.ml.versioning import ModelVersionManager
from app.ml.trainer import calculate_metrics
import numpy as np


def evaluate_model(
    model_path: str,
    test_sequences: List[List[str]],
    test_labels: List[str]
) -> dict:
    """
    Evaluate model on test data.
    
    Args:
        model_path: Path to model file
        test_sequences: Test sequences
        test_labels: Test labels
        
    Returns:
        Evaluation metrics
    """
    # Load model
    model = LSTMPredictor()
    model.load(model_path)
    
    # Prepare test data
    from app.ml.trainer import prepare_training_data
    
    # Convert to format expected by prepare_training_data
    # (It expects sequences and labels separately)
    sequences = []
    labels = []
    for seq, label in zip(test_sequences, test_labels):
        sequences.append(seq)
        labels.append(label)
    
    _, _, test_data = prepare_training_data(
        sequences,
        labels,
        sequence_length=model.sequence_length
    )
    
    (X_seq_test, X_stat_test), y_test = test_data
    
    # Predict
    y_pred_proba = model.model.predict([X_seq_test, X_stat_test], verbose=0)
    y_pred = np.argmax(y_pred_proba, axis=1)
    y_pred_onehot = np.eye(2)[y_pred]
    
    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred_onehot, y_pred_proba)
    
    return metrics


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Evaluate ML model')
    parser.add_argument('--model', type=str, required=True,
                       help='Model path (without .h5 extension)')
    parser.add_argument('--version', type=str,
                       help='Model version to evaluate')
    parser.add_argument('--test-data', type=str,
                       help='Test data file path')
    
    args = parser.parse_args()
    
    print("📊 Evaluating model...")
    
    # Get model path
    if args.version:
        version_manager = ModelVersionManager()
        model_path = version_manager.get_model_path(args.version)
        if not model_path:
            print(f"Error: Version {args.version} not found")
            return
    else:
        model_path = args.model
    
    if not Path(f"{model_path}.h5").exists():
        print(f"Error: Model file not found: {model_path}.h5")
        return
    
    # Load test data if provided
    if args.test_data:
        import pandas as pd
        df = pd.read_csv(args.test_data)
        test_sequences = [row['sequence'].split(',') for _, row in df.iterrows()]
        test_labels = df['label'].tolist()
    else:
        print("Warning: No test data provided. Using model's test metrics from registry.")
        version_manager = ModelVersionManager()
        if args.version:
            version = version_manager.get_version(args.version)
            if version:
                print(f"\nModel: {version.version}")
                print(f"Accuracy: {version.accuracy:.4f}")
                print(f"Precision: {version.precision:.4f}")
                print(f"Recall: {version.recall:.4f}")
                print(f"F1 Score: {version.f1_score:.4f}")
        return
    
    # Evaluate
    try:
        metrics = evaluate_model(model_path, test_sequences, test_labels)
        
        print("\n✅ Evaluation complete!")
        print(f"\nMetrics:")
        print(f"   Accuracy: {metrics['accuracy']:.4f}")
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall: {metrics['recall']:.4f}")
        print(f"   F1 Score: {metrics['f1_score']:.4f}")
        print(f"\nPer-class Metrics:")
        print(f"   Banker - Precision: {metrics['precision_banker']:.4f}, Recall: {metrics['recall_banker']:.4f}")
        print(f"   Player - Precision: {metrics['precision_player']:.4f}, Recall: {metrics['recall_player']:.4f}")
        print(f"\nConfusion Matrix:")
        print(f"   {metrics['confusion_matrix']}")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

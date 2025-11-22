#!/usr/bin/env python3
"""
Prepare training data from game results.

Extracts sequences and labels from database or files.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from app.models.database import GameResult, db_manager
from sqlalchemy.orm import Session


def load_data_from_database(
    db: Session,
    min_sequence_length: int = 30,
    max_sequences: Optional[int] = None
) -> Tuple[List[List[str]], List[str]]:
    """
    Load training data from database.
    
    Args:
        db: Database session
        min_sequence_length: Minimum sequence length
        max_sequences: Maximum number of sequences to load
        
    Returns:
        Tuple of (sequences, labels)
    """
    # Get all results
    results = db.query(GameResult).order_by(GameResult.timestamp.asc()).all()
    
    if not results:
        print("No data in database")
        return [], []
    
    outcomes = [r.result for r in results]
    
    # Generate sequences
    sequences = []
    labels = []
    
    sequence_length = min_sequence_length + 1  # +1 for label
    
    for i in range(sequence_length, len(outcomes)):
        if max_sequences and len(sequences) >= max_sequences:
            break
        
        # Skip if label is 'T'
        if outcomes[i] == 'T':
            continue
        
        # Get sequence (excluding current outcome)
        seq = outcomes[i - min_sequence_length:i]
        label = outcomes[i]
        
        sequences.append(seq)
        labels.append(label)
    
    print(f"Generated {len(sequences)} sequences from {len(outcomes)} outcomes")
    return sequences, labels


def load_data_from_file(filepath: str) -> Tuple[List[List[str]], List[str]]:
    """
    Load training data from CSV file.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Tuple of (sequences, labels)
    """
    df = pd.read_csv(filepath)
    
    if 'result' not in df.columns:
        raise ValueError("CSV file must have 'result' column")
    
    outcomes = df['result'].tolist()
    
    # Generate sequences
    sequences = []
    labels = []
    min_sequence_length = 30
    
    for i in range(min_sequence_length + 1, len(outcomes)):
        if outcomes[i] == 'T':
            continue
        
        seq = outcomes[i - min_sequence_length:i]
        label = outcomes[i]
        
        sequences.append(seq)
        labels.append(label)
    
    print(f"Generated {len(sequences)} sequences from file")
    return sequences, labels


def generate_synthetic_data(
    num_sequences: int = 1000,
    sequence_length: int = 30
) -> Tuple[List[List[str]], List[str]]:
    """
    Generate synthetic training data.
    
    Args:
        num_sequences: Number of sequences to generate
        sequence_length: Length of each sequence
        
    Returns:
        Tuple of (sequences, labels)
    """
    import random
    
    # Theoretical probabilities
    probs = {'B': 0.458597, 'P': 0.446247, 'T': 0.095156}
    
    sequences = []
    labels = []
    
    for _ in range(num_sequences):
        # Generate sequence
        seq = []
        for _ in range(sequence_length):
            outcome = random.choices(
                ['B', 'P', 'T'],
                weights=[probs['B'], probs['P'], probs['T']]
            )[0]
            seq.append(outcome)
        
        # Generate label (slightly biased by recent outcomes)
        recent_banker = seq[-10:].count('B')
        recent_player = seq[-10:].count('P')
        
        if recent_banker > recent_player + 2:
            label = 'B'
        elif recent_player > recent_banker + 2:
            label = 'P'
        else:
            label = random.choices(['B', 'P'], weights=[0.5, 0.5])[0]
        
        sequences.append(seq)
        labels.append(label)
    
    print(f"Generated {len(sequences)} synthetic sequences")
    return sequences, labels


def save_data(
    sequences: List[List[str]],
    labels: List[str],
    output_path: str
) -> None:
    """
    Save training data to file.
    
    Args:
        sequences: List of sequences
        labels: List of labels
        output_path: Output file path
    """
    data = {
        'sequence': [','.join(seq) for seq in sequences],
        'label': labels
    }
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(sequences)} sequences to {output_path}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prepare training data')
    parser.add_argument('--source', choices=['database', 'file', 'synthetic'], default='synthetic',
                       help='Data source')
    parser.add_argument('--input', type=str, help='Input file path (for file source)')
    parser.add_argument('--output', type=str, default='ml-training/data/training_data.csv',
                       help='Output file path')
    parser.add_argument('--num-sequences', type=int, default=1000,
                       help='Number of sequences (for synthetic)')
    parser.add_argument('--sequence-length', type=int, default=30,
                       help='Sequence length')
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    if args.source == 'database':
        db = next(db_manager.get_session())
        try:
            sequences, labels = load_data_from_database(db)
            if sequences:
                save_data(sequences, labels, args.output)
            else:
                print("No data found in database")
        finally:
            db.close()
    
    elif args.source == 'file':
        if not args.input:
            print("Error: --input required for file source")
            return
        sequences, labels = load_data_from_file(args.input)
        save_data(sequences, labels, args.output)
    
    elif args.source == 'synthetic':
        sequences, labels = generate_synthetic_data(
            num_sequences=args.num_sequences,
            sequence_length=args.sequence_length
        )
        save_data(sequences, labels, args.output)
    
    print("✅ Data preparation complete")


if __name__ == "__main__":
    main()

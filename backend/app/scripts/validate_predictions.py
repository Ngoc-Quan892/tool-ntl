"""
Validate prediction accuracy in production.

Usage:
    python -m app.scripts.validate_predictions
    python -m app.scripts.validate_predictions --duration=60
    python -m app.scripts.validate_predictions --duration=30 --output=reports/
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import argparse

from app.services.predictive_cache_warmer import AccessPatternAnalyzer

logger = logging.getLogger(__name__)


async def main(duration_minutes: int = 60, output_dir: str = "logs"):
    """
    Make predictions, wait, then validate accuracy.
    
    Args:
        duration_minutes: How long to wait before validation
        output_dir: Directory to save prediction and validation reports
    """
    print(f"🔮 Making predictions for next {duration_minutes} minutes...")
    
    # 1. Initialize analyzer
    analyzer = AccessPatternAnalyzer(
        lookback_days=30,
        min_confidence=0.7,
    )
    
    # Ensure model is trained
    print("📚 Checking model status...")
    if analyzer.model is None:
        print("⚠️  Model not trained. Training now...")
        training_result = await analyzer.train_prediction_model()
        if training_result.get("status") != "success":
            print(f"❌ Model training failed: {training_result}")
            return None
        print("✅ Model trained successfully")
    else:
        print("✅ Model already loaded")
    
    # 2. Make predictions
    print(f"🔮 Generating predictions...")
    predictions = await analyzer.predict_next_access(
        time_horizon=duration_minutes,
        top_k=20
    )
    
    if not predictions:
        print("⚠️  No predictions generated. Model may need retraining.")
        return None
    
    prediction_time = datetime.now()
    print(f"✅ Made {len(predictions)} predictions at {prediction_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 3. Save predictions
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    predictions_file = output_path / f"predictions_{prediction_time.strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(predictions_file, "w", encoding="utf-8") as f:
        json.dump({
            "prediction_time": prediction_time.isoformat(),
            "duration_minutes": duration_minutes,
            "predictions": predictions,
            "model_info": {
                "min_confidence": analyzer.min_confidence,
                "lookback_days": analyzer.lookback_days,
            }
        }, f, indent=2)
    
    print(f"💾 Predictions saved to {predictions_file}")
    
    # 4. Wait
    print(f"⏳ Waiting {duration_minutes} minutes for validation...")
    print(f"   (Started at {prediction_time.strftime('%H:%M:%S')}, will validate at {(prediction_time + timedelta(minutes=duration_minutes)).strftime('%H:%M:%S')})")
    
    # For testing, you can reduce wait time
    # In production, use: await asyncio.sleep(duration_minutes * 60)
    if duration_minutes > 60:
        print("   ⚠️  Long wait time detected. Use --duration for shorter tests.")
    
    await asyncio.sleep(duration_minutes * 60)
    
    # 5. Get actual accesses
    print("📊 Fetching actual accesses...")
    validation_time = datetime.now()
    
    try:
        actual_accesses = await analyzer._get_access_logs(
            start_date=prediction_time,
            end_date=validation_time
        )
        
        if not actual_accesses:
            print("⚠️  No actual accesses found in the time window")
            actual_game_ids = set()
        else:
            # Extract unique game IDs from actual accesses
            actual_game_ids = {int(access.get("game_id", 0)) for access in actual_accesses if access.get("game_id")}
    except Exception as exc:
        logger.error(f"Failed to get access logs: {exc}", exc_info=True)
        print(f"❌ Error fetching actual accesses: {exc}")
        actual_game_ids = set()
    
    # 6. Calculate accuracy
    predicted_game_ids = {int(p["game_id"]) for p in predictions if "game_id" in p}
    
    correct_predictions = predicted_game_ids & actual_game_ids
    
    precision = len(correct_predictions) / len(predicted_game_ids) if predicted_game_ids else 0.0
    recall = len(correct_predictions) / len(actual_game_ids) if actual_game_ids else 0.0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    
    # 7. Generate report
    report = {
        "prediction_time": prediction_time.isoformat(),
        "validation_time": validation_time.isoformat(),
        "duration_minutes": duration_minutes,
        "predictions_count": len(predictions),
        "actual_accesses_count": len(actual_game_ids),
        "correct_predictions": len(correct_predictions),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1_score),
        "predicted_games": sorted(list(predicted_game_ids)),
        "actual_games": sorted(list(actual_game_ids)),
        "correct_games": sorted(list(correct_predictions)),
        "model_info": {
            "min_confidence": analyzer.min_confidence,
            "lookback_days": analyzer.lookback_days,
        },
        "predictions_detail": predictions,
    }
    
    # 8. Save report
    report_file = output_path / f"prediction_validation_{prediction_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    # 9. Print summary
    print("\n" + "="*60)
    print("📈 PREDICTION VALIDATION REPORT")
    print("="*60)
    print(f"Prediction Time:  {prediction_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Validation Time:  {validation_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:         {duration_minutes} minutes")
    print("-"*60)
    print(f"Predictions:      {len(predictions)}")
    print(f"Actual Accesses:  {len(actual_game_ids)}")
    print(f"Correct:          {len(correct_predictions)}")
    print("-"*60)
    print(f"Precision:        {precision:.2%}")
    print(f"Recall:           {recall:.2%}")
    print(f"F1 Score:         {f1_score:.2%}")
    print("-"*60)
    
    if correct_predictions:
        print(f"✅ Correctly predicted games: {sorted(list(correct_predictions))[:10]}")
        if len(correct_predictions) > 10:
            print(f"   ... and {len(correct_predictions) - 10} more")
    
    if predicted_game_ids - actual_game_ids:
        missed = predicted_game_ids - actual_game_ids
        print(f"❌ Predicted but not accessed: {sorted(list(missed))[:10]}")
        if len(missed) > 10:
            print(f"   ... and {len(missed) - 10} more")
    
    if actual_game_ids - predicted_game_ids:
        missed = actual_game_ids - predicted_game_ids
        print(f"⚠️  Accessed but not predicted: {sorted(list(missed))[:10]}")
        if len(missed) > 10:
            print(f"   ... and {len(missed) - 10} more")
    
    print(f"\n📄 Full report saved to: {report_file}")
    print("="*60)
    
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate prediction accuracy in production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate predictions for next 60 minutes (default)
  python -m app.scripts.validate_predictions
  
  # Validate for 30 minutes
  python -m app.scripts.validate_predictions --duration=30
  
  # Save reports to custom directory
  python -m app.scripts.validate_predictions --output=reports/
  
  # Quick test (1 minute)
  python -m app.scripts.validate_predictions --duration=1
        """
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in minutes to wait before validation (default: 60)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs",
        help="Output directory for prediction and validation reports (default: logs)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.duration < 1:
        print("❌ Error: Duration must be at least 1 minute")
        exit(1)
    
    if args.duration > 1440:
        print("⚠️  Warning: Duration > 24 hours. This will take a very long time.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            exit(0)
    
    # Run validation
    try:
        report = asyncio.run(main(args.duration, args.output))
        if report:
            exit(0)
        else:
            exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        exit(130)
    except Exception as exc:
        logger.error(f"Validation failed: {exc}", exc_info=True)
        print(f"\n❌ Validation failed: {exc}")
        exit(1)


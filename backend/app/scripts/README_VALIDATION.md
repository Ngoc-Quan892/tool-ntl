# Prediction Validation Script

Script để validate prediction accuracy trong production environment.

## Usage

### Basic Usage

```bash
# Run validation với default 60 minutes
python -m app.scripts.validate_predictions

# Custom duration (30 minutes)
python -m app.scripts.validate_predictions --duration=30

# Custom output directory
python -m app.scripts.validate_predictions --output=reports/

# Quick test (1 minute)
python -m app.scripts.validate_predictions --duration=1
```

### Arguments

- `--duration`: Thời gian chờ trước khi validate (minutes). Default: 60
- `--output`: Thư mục lưu reports. Default: `logs/`

## How It Works

1. **Make Predictions**: Tạo predictions cho next N minutes
2. **Save Predictions**: Lưu predictions vào JSON file
3. **Wait**: Đợi duration_minutes
4. **Fetch Actual Accesses**: Lấy actual accesses từ database
5. **Calculate Metrics**: Tính precision, recall, F1 score
6. **Generate Report**: Tạo validation report

## Output Files

### Predictions File
`logs/predictions_YYYYMMDD_HHMMSS.json`
```json
{
  "prediction_time": "2024-01-15T14:30:00",
  "duration_minutes": 60,
  "predictions": [...],
  "model_info": {...}
}
```

### Validation Report
`logs/prediction_validation_YYYYMMDD_HHMMSS.json`
```json
{
  "prediction_time": "2024-01-15T14:30:00",
  "validation_time": "2024-01-15T15:30:00",
  "precision": 0.65,
  "recall": 0.72,
  "f1_score": 0.68,
  "predicted_games": [...],
  "actual_games": [...],
  "correct_games": [...]
}
```

## Scheduling

### Linux/Mac (Crontab)

```bash
# Edit crontab
crontab -e

# Add daily validation at 2 AM
0 2 * * * cd /path/to/project/backend && python -m app.scripts.validate_predictions --duration=60 >> logs/validation.log 2>&1

# Weekly validation (every Monday at 3 AM)
0 3 * * 1 cd /path/to/project/backend && python -m app.scripts.validate_predictions --duration=120 >> logs/validation.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (Daily at 2:00 AM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `-m app.scripts.validate_predictions --duration=60`
7. Start in: `C:\path\to\project\backend`

### Using Python Schedule Library

```python
import schedule
import time
import subprocess

def run_validation():
    subprocess.run([
        "python", "-m", "app.scripts.validate_predictions",
        "--duration=60"
    ])

# Schedule daily at 2 AM
schedule.every().day.at("02:00").do(run_validation)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Metrics Explained

- **Precision**: % of predictions that were correct
  - Formula: `correct_predictions / total_predictions`
  - Higher = fewer false positives

- **Recall**: % of actual accesses that were predicted
  - Formula: `correct_predictions / total_actual_accesses`
  - Higher = fewer false negatives

- **F1 Score**: Harmonic mean of precision and recall
  - Formula: `2 * (precision * recall) / (precision + recall)`
  - Balanced metric

## Troubleshooting

### Model Not Trained
Script sẽ tự động train model nếu chưa có. Nếu training fails:
- Check database connection
- Ensure sufficient data (> 100 logs)
- Check logs for errors

### No Predictions Generated
- Model may need retraining
- Check min_confidence threshold
- Verify access logs exist

### No Actual Accesses Found
- Check time window
- Verify database has data for the period
- Check database connection

## Best Practices

1. **Run regularly**: Daily or weekly validation
2. **Monitor trends**: Track precision/recall over time
3. **Adjust thresholds**: Tune min_confidence based on results
4. **Review reports**: Analyze missed predictions
5. **Retrain model**: If accuracy drops significantly

## Example Output

```
🔮 Making predictions for next 60 minutes...
📚 Checking model status...
✅ Model already loaded
🔮 Generating predictions...
✅ Made 15 predictions at 2024-01-15 14:30:00
💾 Predictions saved to logs/predictions_20240115_143000.json
⏳ Waiting 60 minutes for validation...
📊 Fetching actual accesses...

============================================================
📈 PREDICTION VALIDATION REPORT
============================================================
Prediction Time:  2024-01-15 14:30:00
Validation Time:  2024-01-15 15:30:00
Duration:         60 minutes
------------------------------------------------------------
Predictions:      15
Actual Accesses:  20
Correct:          10
------------------------------------------------------------
Precision:        66.67%
Recall:           50.00%
F1 Score:         57.14%
------------------------------------------------------------
✅ Correctly predicted games: [1, 2, 3, 5, 7, 9, 11, 13, 15, 17]
❌ Predicted but not accessed: [4, 6, 8]
⚠️  Accessed but not predicted: [10, 12, 14, 16, 18, 19, 20]

📄 Full report saved to: logs/prediction_validation_20240115_143000.json
============================================================
```


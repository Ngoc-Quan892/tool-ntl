# Database Schema

## Tables

### game_results
- `id` (INTEGER, PRIMARY KEY)
- `result` (VARCHAR(1)) - B, P, or T
- `prediction` (JSON) - Full prediction object
- `shoe_number` (INTEGER)
- `hand_number` (INTEGER)
- `timestamp` (DATETIME)
- `true_count` (FLOAT)
- `edge` (FLOAT)

### simulation_runs
- `id` (INTEGER, PRIMARY KEY)
- `task_id` (VARCHAR(50), UNIQUE)
- `total_shoes` (INTEGER)
- `completed_shoes` (INTEGER)
- `results` (JSON)
- `status` (VARCHAR(20))
- `started_at` (DATETIME)
- `completed_at` (DATETIME, NULLABLE)

## Indexes

- `game_results.timestamp` - For history queries
- `simulation_runs.task_id` - For status lookups

## Migrations

Using Alembic for schema versioning and migrations.


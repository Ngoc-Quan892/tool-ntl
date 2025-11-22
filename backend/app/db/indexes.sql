-- Database indexes for optimal query performance

-- =========================
-- GAME_RESULTS TABLE
-- =========================

CREATE INDEX IF NOT EXISTS idx_game_results_shoe_number
ON game_results (shoe_number);

CREATE INDEX IF NOT EXISTS idx_game_results_result
ON game_results (result);

CREATE INDEX IF NOT EXISTS idx_game_results_shoe_hand_number
ON game_results (shoe_number, hand_number);

CREATE INDEX IF NOT EXISTS idx_game_results_timestamp_desc
ON game_results (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_game_results_result_timestamp
ON game_results (result, timestamp);

CREATE INDEX IF NOT EXISTS idx_game_results_true_count
ON game_results (true_count)
WHERE true_count IS NOT NULL;

-- =========================
-- SIMULATION_RUNS TABLE
-- =========================

CREATE INDEX IF NOT EXISTS idx_sim_runs_status_started_at
ON simulation_runs (status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_sim_runs_task_id
ON simulation_runs (task_id);

-- =========================
-- STATISTICS VIEW (optional)
-- =========================

CREATE MATERIALIZED VIEW IF NOT EXISTS game_result_statistics AS
SELECT
    shoe_number,
    COUNT(id) AS total_hands,
    SUM(CASE WHEN result = 'B' THEN 1 ELSE 0 END) AS banker_wins,
    SUM(CASE WHEN result = 'P' THEN 1 ELSE 0 END) AS player_wins,
    SUM(CASE WHEN result = 'T' THEN 1 ELSE 0 END) AS ties,
    AVG(true_count) AS avg_true_count,
    MAX(ABS(true_count)) AS max_true_count
FROM game_results
GROUP BY shoe_number;

CREATE UNIQUE INDEX IF NOT EXISTS idx_game_result_stats_shoe
ON game_result_statistics (shoe_number);

-- REFRESH MATERIALIZED VIEW CONCURRENTLY game_result_statistics;


-- Create tables for raw storage, cleaned storage, and pipeline observability.

CREATE TABLE IF NOT EXISTS raw_events (
  event_id        TEXT PRIMARY KEY,
  raw_payload     JSONB NOT NULL,
  created_at      TIMESTAMPTZ,
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events_clean (
  event_id        TEXT PRIMARY KEY,
  event_type      TEXT NOT NULL,
  actor_id        BIGINT,
  actor_login     TEXT,
  repo_id         BIGINT,
  repo_name       TEXT,
  created_at      TIMESTAMPTZ NOT NULL,
  hour_bucket     TIMESTAMPTZ NOT NULL,
  day_bucket      DATE NOT NULL,
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id          UUID PRIMARY KEY,
  started_at      TIMESTAMPTZ NOT NULL,
  finished_at     TIMESTAMPTZ,
  status          TEXT NOT NULL, -- STARTED | SUCCESS | FAILED
  rows_fetched    INT NOT NULL DEFAULT 0,
  rows_inserted   INT NOT NULL DEFAULT 0,
  error_message   TEXT
);

-- Helpful indexes for analytics
CREATE INDEX IF NOT EXISTS idx_events_clean_created_at ON events_clean(created_at);
CREATE INDEX IF NOT EXISTS idx_events_clean_hour_bucket ON events_clean(hour_bucket);
CREATE INDEX IF NOT EXISTS idx_events_clean_repo_name ON events_clean(repo_name);
CREATE INDEX IF NOT EXISTS idx_events_clean_actor_login ON events_clean(actor_login);
CREATE INDEX IF NOT EXISTS idx_events_clean_event_type ON events_clean(event_type);

-- Simple views (optional but nice)
CREATE OR REPLACE VIEW v_events_per_hour AS
SELECT hour_bucket, COUNT(*) AS total_events
FROM events_clean
GROUP BY hour_bucket
ORDER BY hour_bucket;

CREATE OR REPLACE VIEW v_event_type_distribution AS
SELECT event_type, COUNT(*) AS total
FROM events_clean
GROUP BY event_type
ORDER BY total DESC;

CREATE OR REPLACE VIEW v_top_repos AS
SELECT repo_name, COUNT(*) AS total_events
FROM events_clean
GROUP BY repo_name
ORDER BY total_events DESC;

CREATE OR REPLACE VIEW v_top_actors AS
SELECT actor_login, COUNT(*) AS total_events
FROM events_clean
GROUP BY actor_login
ORDER BY total_events DESC;


-- Anomoly Detection
CREATE OR REPLACE VIEW v_hourly_activity_with_avg AS
WITH hourly AS (
  SELECT hour_bucket,
         COUNT(*) AS total_events
  FROM events_clean
  GROUP BY hour_bucket
)
SELECT hour_bucket,
       total_events,
       AVG(total_events) OVER () AS overall_avg,
       CASE
         WHEN total_events > (AVG(total_events) OVER () * 1.8)
         THEN TRUE
         ELSE FALSE
       END AS is_anomaly
FROM hourly
ORDER BY hour_bucket DESC;


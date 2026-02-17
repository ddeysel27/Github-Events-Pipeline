import os
from pathlib import Path
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GITHUB_EVENTS_URL = "https://api.github.com/events"


def env(name: str, default: Optional[str] = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def db_conn():
    return psycopg2.connect(
        host=env("DB_HOST"),
        port=int(env("DB_PORT", "5432")),
        dbname=env("DB_NAME"),
        user=env("DB_USER"),
        password=env("DB_PASSWORD"),
    )


def parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    # GitHub: "2026-02-17T14:12:45Z"
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hour_bucket(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def fetch_events(limit: int) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    ua = env("GITHUB_USER_AGENT", "github-events-pipeline")

    headers = {"User-Agent": ua, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(GITHUB_EVENTS_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError("Unexpected response from GitHub API (expected list).")

    # limit locally (GitHub returns ~30 per page typically)
    return data[:limit], dict(resp.headers)


def insert_run_start(cur, run_id: uuid.UUID) -> None:
    cur.execute(
        """
        INSERT INTO pipeline_runs (run_id, started_at, status)
        VALUES (%s, NOW(), 'STARTED')
        """,
        (str(run_id),),
    )


def finish_run(cur, run_id: uuid.UUID, status: str, rows_fetched: int, rows_inserted: int, error: Optional[str]) -> None:
    cur.execute(
        """
        UPDATE pipeline_runs
        SET finished_at = NOW(),
            status = %s,
            rows_fetched = %s,
            rows_inserted = %s,
            error_message = %s
        WHERE run_id = %s
        """,
        (status, rows_fetched, rows_inserted, error, str(run_id)),
    )


def upsert_events(cur, events: List[Dict[str, Any]]) -> int:
    inserted = 0

    for e in events:
        event_id = str(e.get("id"))
        if not event_id or event_id == "None":
            continue

        created = parse_ts(e.get("created_at"))
        etype = e.get("type") or "Unknown"

        actor = e.get("actor") or {}
        repo = e.get("repo") or {}

        actor_id = actor.get("id")
        actor_login = actor.get("login")
        repo_id = repo.get("id")
        repo_name = repo.get("name")

        if created is None:
            # skip if no timestamp (shouldn’t happen, but keep it safe)
            continue

        hb = hour_bucket(created)
        db_day = created.date()

        # 1) raw_events upsert
        cur.execute(
            """
            INSERT INTO raw_events (event_id, raw_payload, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE
              SET raw_payload = EXCLUDED.raw_payload,
                  created_at = EXCLUDED.created_at
            """,
            (event_id, Json(e), created),
        )

        # 2) events_clean upsert
        cur.execute(
            """
            INSERT INTO events_clean (
              event_id, event_type, actor_id, actor_login,
              repo_id, repo_name, created_at, hour_bucket, day_bucket
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE
              SET event_type = EXCLUDED.event_type,
                  actor_id = EXCLUDED.actor_id,
                  actor_login = EXCLUDED.actor_login,
                  repo_id = EXCLUDED.repo_id,
                  repo_name = EXCLUDED.repo_name,
                  created_at = EXCLUDED.created_at,
                  hour_bucket = EXCLUDED.hour_bucket,
                  day_bucket = EXCLUDED.day_bucket
            """,
            (event_id, etype, actor_id, actor_login, repo_id, repo_name, created, hb, db_day),
        )

        inserted += 1

    return inserted


def print_rate_info(headers: Dict[str, str]) -> None:
    # Helpful for interviews: show rate-limit awareness
    remaining = headers.get("X-RateLimit-Remaining")
    limit = headers.get("X-RateLimit-Limit")
    reset = headers.get("X-RateLimit-Reset")
    if remaining is not None:
        reset_dt = None
        try:
            if reset:
                reset_dt = datetime.fromtimestamp(int(reset), tz=timezone.utc)
        except Exception:
            reset_dt = None

        msg = f"GitHub rate limit: remaining={remaining}/{limit}"
        if reset_dt:
            msg += f", resets_at={reset_dt.isoformat()}"
        print(msg)


def main():
    limit = int(env("INGEST_LIMIT", "50"))
    run_id = uuid.uuid4()

    conn = db_conn()
    conn.autocommit = False

    rows_fetched = 0
    rows_inserted = 0

    try:
        with conn.cursor() as cur:
            insert_run_start(cur, run_id)
            conn.commit()

        events, headers = fetch_events(limit=limit)
        rows_fetched = len(events)
        print(f"Fetched {rows_fetched} events.")
        print_rate_info(headers)

        with conn.cursor() as cur:
            rows_inserted = upsert_events(cur, events)
            finish_run(cur, run_id, "SUCCESS", rows_fetched, rows_inserted, None)
        conn.commit()

        print(f"Inserted/Upserted {rows_inserted} events. run_id={run_id}")

    except Exception as ex:
        conn.rollback()
        err = f"{type(ex).__name__}: {ex}"
        try:
            with conn.cursor() as cur:
                finish_run(cur, run_id, "FAILED", rows_fetched, rows_inserted, err)
            conn.commit()
        except Exception:
            conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

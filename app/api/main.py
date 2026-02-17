"""
main.py — GitHub Public Events Pipeline API

What this API does:
- Loads environment variables from the project root .env
- Connects to Postgres (psycopg2) for metrics endpoints (read-only analytics views)
- Exposes /metrics/* endpoints used by the React dashboard
- Adds CORS so the Vite frontend (localhost:5173) can call the API
- Adds Basic Auth–protected /admin/* endpoints to browse Postgres tables

Notes:
- We keep DB access consistent by using psycopg2 everywhere (no SQLAlchemy engine needed).
- The admin endpoints are protected with HTTP Basic Auth (username/password in .env).
"""

import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# -------------------------------------------------------------------
# ENV LOADING (works in Docker + local)
# -------------------------------------------------------------------
# This resolves to: <repo_root>/.env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# -------------------------------------------------------------------
# APP INIT
# -------------------------------------------------------------------
app = FastAPI(title="GitHub Public Events Pipeline API")

# Allow frontend dev server to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# BASIC AUTH (Admin endpoints)
# -------------------------------------------------------------------
security = HTTPBasic()

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    HTTP Basic auth guard.
    - Uses constant-time comparison to avoid timing attacks.
    """
    ok_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    ok_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)

    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# -------------------------------------------------------------------
# DB HELPERS
# -------------------------------------------------------------------
def env(name: str, default: Optional[str] = None) -> str:
    """
    Read environment variable or raise if missing and no default.
    """
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def get_conn():
    """
    Create a new psycopg2 connection using env vars.
    In Docker: DB_HOST=db
    Locally:  DB_HOST=localhost
    """
    return psycopg2.connect(
        host=env("DB_HOST"),
        port=int(env("DB_PORT", "5432")),
        dbname=env("DB_NAME"),
        user=env("DB_USER"),
        password=env("DB_PASSWORD"),
    )


# -------------------------------------------------------------------
# HEALTH
# -------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


# -------------------------------------------------------------------
# METRICS ENDPOINTS (used by the dashboard)
# -------------------------------------------------------------------
@app.get("/metrics/events-per-hour")
def events_per_hour(limit: int = 48) -> List[Dict[str, Any]]:
    """
    Returns time-bucketed event totals.
    Backed by SQL view: v_events_per_hour
    """
    sql = """
      SELECT hour_bucket, total_events
      FROM v_events_per_hour
      ORDER BY hour_bucket DESC
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    # Reverse so chart draws left→right oldest→newest
    return [{"hour_bucket": r[0].isoformat(), "total_events": int(r[1])} for r in rows][::-1]


@app.get("/metrics/event-types")
def event_types(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Returns distribution of event types.
    Backed by SQL view: v_event_type_distribution
    """
    sql = """
      SELECT event_type, total
      FROM v_event_type_distribution
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [{"event_type": r[0], "total_events": int(r[1])} for r in rows]


@app.get("/metrics/top-repos")
def top_repos(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top repos by event count.
    Backed by SQL view: v_top_repos
    """
    sql = """
      SELECT repo_name, total_events
      FROM v_top_repos
      WHERE repo_name IS NOT NULL
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [{"repo_name": r[0], "total_events": int(r[1])} for r in rows]


@app.get("/metrics/top-actors")
def top_actors(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns top actors by event count.
    Backed by SQL view: v_top_actors
    """
    sql = """
      SELECT actor_login, total_events
      FROM v_top_actors
      WHERE actor_login IS NOT NULL
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [{"actor_login": r[0], "total_events": int(r[1])} for r in rows]


@app.get("/metrics/pipeline-runs")
def pipeline_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Returns ingestion run logs.
    Backed by table: pipeline_runs
    """
    sql = """
      SELECT run_id, started_at, finished_at, status, rows_fetched, rows_inserted, error_message
      FROM pipeline_runs
      ORDER BY started_at DESC
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [
        {
            "run_id": str(r[0]),
            "started_at": r[1].isoformat() if r[1] else None,
            "finished_at": r[2].isoformat() if r[2] else None,
            "status": r[3],
            "rows_fetched": int(r[4]),
            "rows_inserted": int(r[5]),
            "error_message": r[6],
        }
        for r in rows
    ]


@app.get("/metrics/anomalies")
def anomalies(limit: int = 24) -> List[Dict[str, Any]]:
    """
    Returns anomaly flags (simple avg-based).
    Backed by SQL view: v_hourly_activity_with_avg
    """
    sql = """
      SELECT hour_bucket, total_events, overall_avg, is_anomaly
      FROM v_hourly_activity_with_avg
      LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [
        {
            "hour_bucket": r[0].isoformat(),
            "total_events": int(r[1]),
            "overall_avg": float(r[2]),
            "is_anomaly": bool(r[3]),
        }
        for r in rows
    ]


# -------------------------------------------------------------------
# ADMIN ENDPOINTS (protected with Basic Auth)
# -------------------------------------------------------------------
admin_router = APIRouter()


@admin_router.get("/admin/tables", dependencies=[Depends(require_admin)])
def list_tables() -> List[str]:
    """
    Lists tables in public schema.
    """
    sql = """
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema='public' AND table_type='BASE TABLE'
      ORDER BY table_name
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    return [r[0] for r in rows]


@admin_router.get("/admin/table/{table_name}", dependencies=[Depends(require_admin)])
def read_table(table_name: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Reads rows from a single table with pagination.
    - Very basic table-name validation to prevent injection.
    """
    if not table_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name")

    # Table identifiers can't be parameterized in psycopg2, so we quote it safely.
    sql = f'SELECT * FROM "{table_name}" LIMIT %s OFFSET %s'

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            colnames = [d.name for d in cur.description]
            rows = cur.fetchall()

    # Return list-of-dicts for easy rendering in the frontend
    out_rows = [dict(zip(colnames, r)) for r in rows]

    return {"table": table_name, "limit": limit, "offset": offset, "rows": out_rows}


# Mount admin router
app.include_router(admin_router)

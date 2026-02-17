# GitHub Events Data Pipeline + Full-Stack Dashboard

A lightweight, production-style data platform that ingests **GitHub Public Events** from the GitHub REST API, stores both **raw JSON** and **cleaned/analytics-ready** data in **PostgreSQL**, exposes **metrics endpoints** via **FastAPI**, and visualizes them in a **React (Vite) dashboard**.

Built as a **2–3 day interview-ready portfolio project** that demonstrates real-world data engineering patterns: ingestion, ETL, schema + views, Dockerized services, observability, and a simple admin interface.

---

## Why this project exists

This repo is designed to show you can build a small but realistic data platform end-to-end:

- API ingestion + repeatable ETL
- Postgres schema design (raw + clean + observability)
- SQL analytics views
- FastAPI backend as a metrics service
- React dashboard with charts
- Docker Compose multi-service networking
- Basic auth–protected admin table viewer

---

## Architecture

**Data flow:**

GitHub REST API  
→ **Ingestor service (Python)**  
→ **PostgreSQL (raw + cleaned tables)**  
→ **SQL views (analytics + anomaly)**  
→ **FastAPI (metrics + admin endpoints)**  
→ **React dashboard (Vite + Recharts)**

---

## Services (Docker Compose)

- `db` — PostgreSQL 15
- `api` — FastAPI (Uvicorn) metrics service
- `ingestor` — Python scheduled ingestion loop
- `frontend` — React dashboard (Vite dev locally; containerizable)

**Networking rule (important):**
- Inside Docker: `DB_HOST=db`
- Outside Docker (local scripts): `DB_HOST=localhost`

---

## Database design

### Tables
- `raw_events`  
  Stores the full GitHub event payload (JSON) for traceability/reprocessing.
- `events_clean`  
  Flattened rows for analytics (repo, actor, event type, timestamps, etc.).
- `pipeline_runs`  
  Ingestion observability: start/end, rows fetched/inserted, status, errors.

### Views
- `v_events_per_hour`
- `v_event_type_distribution`
- `v_top_repos`
- `v_top_actors`
- `v_hourly_activity_with_avg` (basic anomaly detection)

---

## API Endpoints

### Health
- `GET /health`

### Metrics (used by dashboard)
- `GET /metrics/events-per-hour`
- `GET /metrics/event-types`
- `GET /metrics/top-repos`
- `GET /metrics/top-actors`
- `GET /metrics/pipeline-runs`
- `GET /metrics/anomalies`

### Admin (Basic Auth protected)
- `GET /admin/tables`
- `GET /admin/table/{table_name}?limit=50&offset=0`

---

## Local Setup (recommended)

### 1) Prereqs
- Docker + Docker Compose
- Node.js **20 LTS**
- Python 3.12 (optional if you run everything in Docker)

### 2) Environment variables
Create a **root** `.env` file (not committed):

```env
# Postgres (Docker)
DB_HOST=db
DB_PORT=5432
DB_NAME=github_events
DB_USER=postgres
DB_PASSWORD=postgres
```

### 3) Start backend services
```
docker compose up -d --build
```
{confirm: API: http://localhost:8000/health}

### 4) Start frontend (dev)
```
cd frontend/frontend
npm install
npm run dev
```
{Open Frontend: http://localhost:5173}

## Frontend Dashboard

#### Dashboard shows:
-  Top repositories by event volume
-  Event type distribution
-  Top actors
-  vents per hour
-  Recent pipeline runs
-  Anomaly flags (avg-based)

#### Admin tab (login required) lets you:
-  list Postgres tables
-  browse rows with pagination in a table view
-  Production Notes (what makes this “real”)
-  Raw + clean separation enables reprocessing and auditing
-  Views provide stable metrics contracts for the API
-  pipeline_runs acts as built-in observability
-  Docker networking mirrors real microservice connectivity
-  Basic auth protects internal/admin endpoints
-  Designed to be deployable to EC2/ECS later

#### roubleshooting
“Failed to fetch” in dashboard
-  Ensure API is running: http://localhost:8000/health
-  Ensure CORS allows http://localhost:5173
-  Ensure frontend .env has:
```{env}
VITE_API_BASE_URL=http://localhost:8000
```
{Restart npm run dev after editing}

#### GitHub
-  Never commit .env with secrets
-  Rotate leaked tokens immediately
-  GITHUB_TOKEN=YOUR_TOKEN_HERE

#### Admin (Basic Auth)
ADMIN_USER=admin
ADMIN_PASS=admin123

#### Roadmap (optional)
-  Containerize frontend + add reverse proxy (single origin)
-  Add a small “data freshness” indicator on dashboard
-  Add rate-limit backoff + idempotent ingestion guarantees
-  Deploy to AWS (EC2 first, then ECS)

# GitHub Public Events Pipeline (AWS-Ready)

A lightweight end-to-end data engineering project that ingests real-time public events from the GitHub REST API, stores raw + cleaned records in PostgreSQL, and exposes analytics via a small API. Designed to be containerized and deployed to AWS (EC2/ECS).

## Architecture
Scheduler (cron/EventBridge) → Python ingestor → Postgres (raw + clean) → FastAPI metrics

## Quickstart (Local)

1) Copy env:
```bash
cp .env.example .env

2) Start Postgres + API:
docker compose up -d

3) Run ingestion:
pip install -r requirements.txt
python app/ingestor/ingest.py

4) Hit endpoints:
Hit endpoints:

  http://localhost:8000/health

  http://localhost:8000/metrics/events-per-hour

  http://localhost:8000/metrics/event-types

  http://localhost:8000/metrics/top-repos

  http://localhost:8000/metrics/top-actors

  http://localhost:8000/metrics/pipeline-runs


---

# Run it now (in order)

### A) Create your `.env`
```bash
cp .env.example .env

B) Start DB + API
docker compose up -d

C) Run ingestion (from local env)
python -m venv .venv
# source .venv/bin/activate   # mac/linux
 .venv\Scripts\activate    # windows
pip install -r requirements.txt

python app/ingestor/ingest.py

D) Confirm API works
Open:
  http://localhost:8000/metrics/top-repos
  
  http://localhost:8000/metrics/pipeline-runs

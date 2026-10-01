# CLAUDE.md (backend)

Guidance for Claude Code when working in `backend/` — the Python/FastAPI implementation of the Measured API. See the [root CLAUDE.md](../CLAUDE.md) for the project overview and shared data model.

## Stack

Python 3.12, FastAPI, async PostgreSQL via `databases` / `asyncpg`. Raw parameterized SQL, no ORM.

## Commands

```bash
uvicorn app.main:app --reload   # dev server on port 8000
pytest                          # all tests
pytest tests/test_sessions.py   # single file
pytest tests/test_sessions.py::test_create_session  # single test
```

## Structure (`app/`)
- `main.py` — FastAPI app, CORS allowlist, lifespan (DB connect/disconnect), custom 400 handler for validation errors
- `database.py` — async DB connection pool, schema init (`init_db`)
- `models.py` — dataclasses for DB row mapping
- `schemas.py` — Pydantic request/response models
- `routers/` — `health.py`, `projects.py`, `sessions.py`, `session_stats.py` (`/sessions/stats`; also holds the project display order)
- `sessions-migration/` — one-time SQLite→Postgres migration scripts (historical, not used at runtime)

FastAPI `Depends()` injects the DB connection. Uses Postgres's `RETURNING` clause on inserts/updates.

## API (base `/api/`)
- `GET /api/health`
- `GET /api/projects` (optional `?sort=MOST_RECENTLY_USED`), `POST /api/projects`
- `POST /api/sessions`, `GET /api/sessions` (paginated, filterable by `min_date`/`max_date` and one or more `project_id`), `GET/PUT/DELETE /api/sessions/{id}`
- `GET /api/sessions/stats` (`from_date` inclusive, `to_date` exclusive, `aggregation_by=day|week|month`, optional repeated `project_id`) — per-segment, per-project minute totals aggregated in SQL; weeks start Monday

## Testing

pytest with `asyncio_mode = auto` (`pytest.ini`). `conftest.py` starts a real Postgres via `testcontainers`, scoped once per test session; each test gets a fresh schema (`init_db()` recreates it, dropped again after the test runs).

## Database

- Dev: Docker Compose Postgres (`docker compose up -d` from repo root), then `DATABASE_URL=postgresql://measured:measured@localhost:5432/measured`
- Production: Fly Postgres cluster `measured-database`, attached to `measured-backend` via a `DATABASE_URL` secret — no default, app fails fast at startup if unset
- Reach production DB from a local machine: `fly proxy 15432:5432 -a measured-database`, then connect to `localhost:15432` with the app's DB credentials
- Daily backups via GitHub Actions (`.github/workflows/backup-postgres-database.yml`)
- Seed data and schema migration SQL in `sql/`
- Full deploy/backup/restore walkthrough: [DEPLOYMENT.md](DEPLOYMENT.md)

## Deployment

```bash
fly deploy    # deploy backend
fly logs      # production logs
fly status    # check running state
```

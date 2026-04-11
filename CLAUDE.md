# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Measured** is a personal time tracking app. Users log sessions (with a project and duration), view history, and analyze activity via charts.

- **Frontend**: React 19 + TypeScript + Vite + React Router + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python 3.12) + async SQLite via `databases` / `aiosqlite`
- **Deployment**: Vercel (frontend) + Fly.io (backend)

## Commands

### Frontend (`frontend/`)
```bash
npm run dev       # dev server on port 5173
npm run build     # TypeScript check + Vite build
npm run lint      # ESLint
```

### Backend (`backend/`)
```bash
uvicorn app.main:app --reload   # dev server on port 8000
pytest                          # all tests
pytest tests/test_sessions.py   # single file
pytest tests/test_sessions.py::test_create_session  # single test
```

### Deployment
```bash
fly deploy    # deploy backend
fly logs      # production logs
```

## Architecture

### Data Model
```sql
projects (id, name, color VARCHAR(7), extra_color VARCHAR(7))
sessions (id, project_id, start_time TIMESTAMP, end_time TIMESTAMP, created_at TIMESTAMP)
```

Sessions store absolute start/end timestamps. Duration is computed from the difference. The "Log Session" UI works retroactively — user inputs a duration and the backend stores `now - duration` as `start_time`.

### Backend (`backend/app/`)
- `main.py` — FastAPI app, CORS allowlist, lifespan (DB connect/disconnect), custom 400 handler for validation errors
- `database.py` — async DB connection pool, schema init
- `models.py` — Python dataclasses for DB row mapping
- `schemas.py` — Pydantic models for API request/response
- `routers/` — `health.py`, `projects.py`, `sessions.py`

Uses raw parameterized SQL (no ORM). Uses SQLite `RETURNING` clause (requires SQLite 3.35+). FastAPI `Depends()` injects the DB connection.

API base: `/api/`
- `GET /api/projects`
- `POST /api/sessions`, `GET /api/sessions` (paginated, filterable by date range + project IDs), `GET/PUT/DELETE /api/sessions/{id}`

### Frontend (`frontend/src/`)
- `pages/` — `LogSession`, `Sessions`, `Projects`, `Charts`
- `components/` — `Layout` (responsive sidebar), `DateIntervalChooser`, `ProjectFilterSelect`, `SessionsChart`, shadcn/ui components in `ui/`
- `hooks/` — `useProjects`, `useSessions` (fetch with loading/error states, abort signal cleanup)
- `lib/` — shared TypeScript types, formatting utilities, project filtering/sorting

`@/` is the path alias for `src/`.

Frontend reads `VITE_API_URL` for the backend URL.

### Testing
Backend tests use pytest with `asyncio_mode = auto` (see `pytest.ini`). `conftest.py` sets up an in-memory SQLite test database for each test.

### Database
- Dev: `measured.db` (local file)
- Production: mounted Fly.io volume at `/data/measured.db`
- Daily backups via GitHub Actions (`.github/workflows/backup-database.yml`)
- Seed data and schema in `sql/`

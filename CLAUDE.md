# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Measured** is a personal time tracking app. Users log sessions (a project, a date, and a duration), view history, and analyze activity via charts.

The service has three parts, each with its own `CLAUDE.md` for stack, commands, and structure:
- [backend/CLAUDE.md](backend/CLAUDE.md) — current production backend (Python/FastAPI)
- [backend-kotlin/CLAUDE.md](backend-kotlin/CLAUDE.md) — new backend under development (Kotlin), intended to replace `backend/`
- [frontend/CLAUDE.md](frontend/CLAUDE.md) — React frontend

## Deployment

- Frontend → Vercel, auto-deployed from `main`
- Backend (Python) → Fly.io (`measured-backend` app) + Fly Postgres (`measured-database`)
- Backend (Kotlin) → not yet deployed

## Data Model

The shared contract any backend implementation must honor:

```sql
projects (id, name, color VARCHAR(7), extra_color VARCHAR(7))
sessions (id, project_id, date DATE, duration_minutes INTEGER, create_time BIGINT)
```

Sessions store a calendar `date` and a `duration_minutes` directly — not absolute start/end timestamps. `create_time` is an epoch-millisecond audit timestamp (when the row was created), used only for ordering, not for duration math. A dead `sessions_legacy_data` table (old `start_time`/`end_time` text values) still exists from a prior schema but is never read or written by application code.

## Repository Layout

- `backend/` — Python/FastAPI backend (current production)
- `backend-kotlin/` — Kotlin backend (in development)
- `frontend/` — React frontend
- `docker-compose.yml` — local Postgres for dev
- `.github/workflows/` — CI, daily production DB backup

# SQLite → PostgreSQL migration plan

## Recovery note

The original detailed plan document for this migration is unrecoverable — it lived at a global, non-project-scoped path (`~/.claude/plans/`) that gets overwritten by other sessions on this machine, and no copy exists anywhere (checked filesystem, git history, stash). This plan is freshly written, informed by three real sources: a project memory record explaining the original motivation and a since-resolved blocker, two actual git commits (`3ad9de0` / `16e9199`) from a first implementation attempt that was deliberately reverted, and this repo's own `backend/DEPLOYMENT.md`, which already sketches the intended provider (Fly Postgres) in its "Migration to PostgreSQL (Optional)" section.

## Context

**Why**: PostgreSQL for better concurrency than SQLite offers under this app's access patterns.

**Why now**: a prerequisite schema migration (`sessions.start_time`/`end_time` → `date`/`duration_minutes`/`create_time`) was required first — it eliminated a class of timezone bug and, as a side effect relevant here, removed every `TIMESTAMP` column from the schema. That migration is now complete. This matters concretely: the one genuinely tricky part of the earlier reverted attempt was reconciling how `aiosqlite` and `asyncpg` return datetime values differently (native `datetime` objects vs. ISO strings). With no `TIMESTAMP` columns left, that whole problem class is gone — `sessions` now only has `id`, `project_id`, `date` (`TEXT`), `duration_minutes` (`INTEGER`), `create_time` (`BIGINT`), all of which round-trip identically through both drivers with zero dialect-specific code.

**Provider decision**: Fly Postgres (Fly's own managed Postgres, attached to the existing `measured-backend` app). This isn't a new decision — `DEPLOYMENT.md` already names this as the intended path. Keeping everything on one platform avoids adding a second vendor relationship for a single-user app.

**Schema decision — use Postgres's native `DATE` type for `sessions.date`.** `schemas.py` already types `SessionCreate.date` / `SessionUpdate.date` as `datetime.date`, so a native `date` object coming back from Postgres is the natural fit. `asyncpg` requires an actual `date` object bound against a `DATE` column — a plain `str` is rejected — so the write-side `.isoformat()` calls in `routers/sessions.py` (`create_session`, `update_session`, and the `min_date`/`max_date` filters in `get_sessions`) become dialect-aware: convert to `.isoformat()` only for SQLite, pass the `date` object through unchanged for Postgres. `database.py` gains a small `is_sqlite_db(db)` helper (the same `str(db.url).startswith("sqlite")` check `init_db` already does internally) to back this. The read side needs no dialect flag at all — `models.py`'s `Session.from_row` checks `isinstance(row["date"], date)`, since the value is either already a `date` object (Postgres) or a `str` (SQLite). This also means `min_date`/`max_date` filtering and `ORDER BY date` become genuine typed date comparisons enforced by the column itself, rather than relying on ISO-8601 strings happening to sort lexicographically like the dates they represent.

**Test suite runs against a real Postgres via `testcontainers`, not SQLite.** `tests/conftest.py` (rewritten in [Step 2](#step-2--backend-dual-driver-support-prod-stays-on-sqlite)) starts a real `postgres:18` container via `testcontainers-python`'s `PostgresContainer`, scoped once per test *session* (container startup cost paid once, not per test), runs `init_db()` against it once to create the schema, then does a full `TRUNCATE ... RESTART IDENTITY` clean of the data tables after each test. Isolation is via cleanup, not a wrapping transaction that's rolled back — a test is free to open and commit its own separate transactions (needed for anything exercising multi-request/multi-transaction behavior) without losing isolation from the next test. This needs Docker locally, which Step 1 already assumes for the dev Postgres container; GitHub Actions runners have Docker preinstalled too. SQLite isn't exercised by the automated suite at all — any concern about that path (e.g. does `init_db`'s `is_sqlite` branch still produce a working schema) gets a manual smoke test instead — start the app with no `DATABASE_URL` set and hit a couple endpoints.

**Known driver gotcha, handled by convention, not code**: the `databases` library (and modern SQLAlchemy, which it wraps) requires the `postgresql://` URL scheme and rejects the older `postgres://` alias, which is what `fly postgres attach` always prints. Since `DATABASE_URL` is only ever set by hand (`fly secrets set`, see Step 1 and Step 5), the scheme is corrected to `postgresql://` at the point it's typed in — no runtime normalization in `database.py` needed.

---

## Step 1 — Provision Postgres, capture credentials

**Local dev**, add `docker-compose.yml` at the repo root:

```yaml
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_USER: measured
      POSTGRES_PASSWORD: measured
      POSTGRES_DB: measured
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

A developer opts into it locally by running `docker compose up -d` and setting `DATABASE_URL=postgresql://measured:measured@localhost:5432/measured` in their shell before starting uvicorn. `database.py`'s existing `os.getenv("DATABASE_URL", "sqlite:///./measured.db")` fallback means nobody is forced into this — SQLite stays the zero-setup default until Step 5.

**Fly Postgres cluster**:

```bash
fly postgres create --name measured-database --region ams
```

Attach it right away:

```bash
fly postgres attach --app measured-backend measured-database
```

This provisions the real, dedicated `measured-backend`-scoped database and role on the cluster, and writes the resulting connection string to the `DATABASE_URL` secret — which triggers an immediate redeploy of `measured-backend`. The currently deployed code is still SQLite-only at this point (Step 2's `asyncpg` support doesn't exist yet), so that redeploy will crash on startup. This is expected and brief.

`fly postgres attach` prints the generated connection string to stdout — copy it down before it's gone (rewriting `postgres://` to `postgresql://`), since it's needed for Step 4's migration script and any pre-cutover testing.

Then bring production back up by resetting `DATABASE_URL` to SQLite:

```bash
fly secrets set DATABASE_URL='sqlite:////data/measured.db'
```

This triggers another redeploy, back onto the working SQLite code. Production is down for roughly the time these two redeploys take (typically well under a minute). The captured Postgres connection string sits inert — nothing reads it — until Step 5 puts it back.

---

## Step 2 — Backend: dual-driver support, prod stays on SQLite

`backend/requirements.txt` — add the Postgres driver, plus `testcontainers` for the new Postgres-backed test suite:
```
databases[asyncpg]==0.9.0
asyncpg==0.29.0
testcontainers[postgres]  # pin to latest stable at implementation time
```

`backend/app/database.py` — branch the DDL that differs between dialects (autoincrementing primary keys, and now `date`'s column type too), and add a small helper other modules use to know which dialect they're talking to:
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./measured.db")
database = databases.Database(DATABASE_URL)


def is_sqlite_db(db: databases.Database) -> bool:
    return str(db.url).startswith("sqlite")


async def init_db(db: databases.Database | None = None):
    target_db = db if db is not None else database
    is_sqlite = is_sqlite_db(target_db)
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
    date_type = "TEXT" if is_sqlite else "DATE"

    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS projects (
            id {pk},
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)

    await target_db.execute(f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id {pk},
            project_id INTEGER NOT NULL,
            date {date_type} NOT NULL,
            duration_minutes INTEGER NOT NULL,
            create_time BIGINT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Dead archive table (see Step 4's original schema migration) -- not read or written by
    # any application code, kept only in case start_time/end_time are ever needed again.
    # In production this table was created via `CREATE TABLE ... AS SELECT` from the old
    # sessions.start_time/end_time (declared TIMESTAMP), which SQLite's affinity rules map to
    # NUMERIC -- but the actual values are ISO 8601 strings that don't parse as numeric
    # literals, so they're stored as plain TEXT regardless of the column's affinity. A TEXT
    # column here is a faithful, lossless copy; no identity/FK either, matching production.
    await target_db.execute("""
        CREATE TABLE IF NOT EXISTS sessions_legacy_data (
            id INTEGER NOT NULL,
            start_time TEXT,
            end_time TEXT
        )
    """)
```
`GENERATED ALWAYS AS IDENTITY` is Postgres's SQL-standard replacement for the old `SERIAL` pseudo-type — still a sequence-backed auto-incrementing column under the hood, just standard syntax. `ALWAYS` rejects any `INSERT` that supplies an explicit `id` unless it's overridden (see Step 4's migration script), which is the stricter, more deliberate default.

`backend/app/routers/sessions.py` — the four spots that currently call `session.date.isoformat()` / `.isoformat()` on a filter value need to skip that conversion for Postgres, since `asyncpg` rejects a plain `str` bound against a `DATE` column:
```python
from app.database import get_db, is_sqlite_db

def adapt_date(db: databases.Database, d: date) -> "str | date":
    return d.isoformat() if is_sqlite_db(db) else d
```
and replace each `session.date.isoformat()` / `min_date.isoformat()` / `max_date.isoformat()` call site with `adapt_date(db, session.date)` / `adapt_date(db, min_date)` / `adapt_date(db, max_date)`.

`backend/app/models.py` — `Session.from_row` needs no dialect flag; the value is either already a `date` (Postgres) or a `str` (SQLite), so a type check covers both and is actually simpler than the current unconditional parse:
```python
date=row["date"] if isinstance(row["date"], date) else date.fromisoformat(row["date"])
```

`RETURNING` needs no branching — valid syntax in both SQLite (3.35+, already required) and Postgres (where it originated). Every other column type (`TEXT`, `INTEGER`, `BIGINT`, `VARCHAR`) still round-trips identically through both drivers.

**`backend/tests/conftest.py` — uses a real Postgres container, not SQLite:**
```python
import pytest
import databases
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import init_db, get_db


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:18") as pg:
        yield pg


@pytest.fixture(scope="session")
async def postgres_url(postgres_container) -> str:
    # driver=None gives a bare postgresql:// URL (asyncpg-compatible),
    # not the postgresql+psycopg2:// default testcontainers builds for SQLAlchemy sync use.
    url = postgres_container.get_connection_url(driver=None)
    setup_db = databases.Database(url)
    await setup_db.connect()
    await init_db(setup_db)
    await setup_db.disconnect()
    return url


@pytest.fixture(scope="function")
async def test_db(postgres_url: str):
    test_database = databases.Database(postgres_url)
    await test_database.connect()
    await seed_test_projects(test_database)
    yield test_database
    # Full clean, not a rolled-back transaction -- lets a test open and commit its own
    # separate transactions without losing isolation from the next test. RESTART IDENTITY
    # also resets the id sequences, which a rollback wouldn't have (sequence advances in
    # Postgres are not transactional, so force_rollback would leak ids across tests).
    await test_database.execute("TRUNCATE TABLE sessions, projects RESTART IDENTITY CASCADE")
    await test_database.disconnect()


async def seed_test_projects(db: databases.Database):
    test_projects = [
        {"name": "Work", "color": "#ff5733", "extra_color": "#c70039"},
        {"name": "Personal", "color": "#33ff57", "extra_color": None},
        {"name": "Learning", "color": "#3357ff", "extra_color": "#1d3a8f"},
        {"name": "Exercise", "color": "#f3ff33", "extra_color": None},
        {"name": "Hobbies", "color": "#ff33f3", "extra_color": "#8f1d8a"},
    ]
    for project in test_projects:
        await db.execute(
            "INSERT INTO projects (name, color, extra_color) VALUES (:name, :color, :extra_color)",
            project,
        )


@pytest.fixture(scope="function")
async def client(test_db: databases.Database):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```
Note `INSERT OR IGNORE` (SQLite-only syntax) is dropped in favor of plain `INSERT`, since each test now gets a freshly truncated, empty table rather than a shared/reused one — the "ignore duplicates" behavior it existed for no longer applies.

Deploy this. Since `DATABASE_URL` hasn't changed, production keeps running SQLite exactly as before — this step only proves the code *can* speak Postgres, without affecting anything live. `pytest` runs against a `testcontainers` Postgres instance as part of this step (this is the main verification). Separately, smoke-test the SQLite path by running the app locally with no `DATABASE_URL` set (SQLite default) and manually exercising `create_session`/`get_sessions`, since that path has no automated coverage.

---

## Step 3 — Backups: add a Postgres backup workflow, verify it before relying on it

The existing `.github/workflows/backup-database.yml` SSHes into `measured-backend`, runs `sqlite3 /data/measured.db .dump`, gzips it, and uploads it as a 30-day-retention GitHub Actions artifact. That approach doesn't translate — Fly Postgres apps live on Fly's private network, not reachable directly from a GitHub Actions runner, and there's no SQLite file to dump.

Add a parallel workflow, `backup-postgres-database.yml`, using Fly's own documented pattern for reaching a private Postgres instance from outside Fly's network — a `flyctl proxy` tunnel:

```yaml
name: Backup Postgres Database

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  backup:
    name: Backup Production Postgres Database
    runs-on: ubuntu-latest

    steps:
      - name: Install Fly.io CLI
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Open tunnel and dump database
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
          PGPASSWORD: ${{ secrets.POSTGRES_BACKUP_PASSWORD }}
        run: |
          set -o pipefail
          TIMESTAMP=$(date +%Y-%m-%d)
          echo "BACKUP_FILENAME=pg-backup-${TIMESTAMP}.sql.gz" >> $GITHUB_ENV

          flyctl proxy 15432:5432 -a measured-database &
          PROXY_PID=$!
          sleep 5  # wait for the tunnel to establish

          # Run pg_dump from a postgres:18 container rather than apt's "postgresql-client"
          # package -- the Fly Postgres cluster runs Postgres 18, and pg_dump refuses to
          # dump from a server newer than itself, which apt's default (16.x) silently was.
          docker run --rm --network host -e PGPASSWORD \
            postgres:18 pg_dump -h localhost -p 15432 -U measured_backend -d measured_backend \
            | gzip > pg-backup-${TIMESTAMP}.sql.gz

          kill $PROXY_PID

      - name: Verify backup is non-empty
        run: |
          set -o pipefail
          if [ ! -s "${{ env.BACKUP_FILENAME }}" ]; then
            echo "Error: Backup file is empty or does not exist"
            exit 1
          fi
          # Check the decompressed content, not just the gzip wrapper's byte count --
          # gzip-of-nothing is still a non-empty file, which is exactly how a silently
          # failed pg_dump slipped past this check before.
          # Deliberately not "grep -q" here: -q exits on the first match, which (with
          # set -o pipefail above) makes gunzip's resulting SIGPIPE/broken-pipe look like
          # a pipeline failure even though grep actually found the match successfully.
          if ! gunzip -c "${{ env.BACKUP_FILENAME }}" | grep "PostgreSQL database dump" > /dev/null; then
            echo "Error: Backup does not look like real pg_dump output"
            exit 1
          fi
          ls -lh ${{ env.BACKUP_FILENAME }}

      - name: Upload backup as artifact
        uses: actions/upload-artifact@v7
        with:
          name: ${{ env.BACKUP_FILENAME }}
          path: ${{ env.BACKUP_FILENAME }}
          retention-days: 30
          compression-level: 0  # Already compressed with gzip
```

Exact database/user names (`measured_backend`, etc.) come from whatever `fly postgres attach` actually names them — check with `fly postgres db list -a measured-database` and `fly postgres users list -a measured-database` and adjust. `POSTGRES_BACKUP_PASSWORD` is a new GitHub secret holding that role's password (visible once at attach time, or resettable via `fly postgres users create`/`fly ssh console -a measured-database` + `psql`).

**Verify this workflow end-to-end before Step 5's cutover** — trigger it manually (`workflow_dispatch`) against the live `measured-database` cluster, confirm a real, restorable dump comes out, before any production data actually depends on it existing.

Keep the existing SQLite backup workflow running unmodified through Step 5 — production is still SQLite until then.

---

## Step 4 — One-time data migration: copy existing SQLite data into Postgres

A one-off Python script, `backend/app/sessions-migration/migrate_to_postgres.py` (matching this repo's existing convention of keeping one-time migration scripts in that folder), run manually, once, against a fresh copy of the production SQLite file and the Postgres cluster, using the connection string captured during Step 1's attach:

```python
#!/usr/bin/env python3
"""One-time copy of projects/sessions from SQLite into PostgreSQL.

Configure via environment variables before running -- never hardcode real
credentials into this file, since it's committed to the repo:
    SQLITE_PATH   path to a local copy of the production SQLite file (not the live file)
    POSTGRES_URL  postgresql:// connection string for the target Postgres database
"""
import os
import sqlite3
import asyncio
import asyncpg
from datetime import date

SQLITE_PATH = os.environ["SQLITE_PATH"]
POSTGRES_URL = os.environ["POSTGRES_URL"]


async def create_schema(pg_conn: asyncpg.Connection):
    """Mirrors database.py's init_db() Postgres branch -- fly postgres attach only
    provisions the database/role, it never runs the app's schema-creation DDL."""
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            color VARCHAR(7) NOT NULL,
            extra_color VARCHAR(7)
        )
    """)
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            project_id INTEGER NOT NULL,
            date DATE NOT NULL,
            duration_minutes INTEGER NOT NULL,
            create_time BIGINT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    await pg_conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions_legacy_data (
            id INTEGER NOT NULL,
            start_time TEXT,
            end_time TEXT
        )
    """)


async def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = await asyncpg.connect(POSTGRES_URL)

    try:
        await create_schema(pg_conn)

        projects = sqlite_conn.execute("SELECT id, name, color, extra_color FROM projects ORDER BY id").fetchall()
        for p in projects:
            await pg_conn.execute(
                """
                INSERT INTO projects (id, name, color, extra_color)
                OVERRIDING SYSTEM VALUE VALUES ($1, $2, $3, $4)
                """,
                p["id"], p["name"], p["color"], p["extra_color"],
            )

        sessions = sqlite_conn.execute(
            "SELECT id, project_id, date, duration_minutes, create_time FROM sessions ORDER BY id"
        ).fetchall()
        for s in sessions:
            await pg_conn.execute(
                """
                INSERT INTO sessions (id, project_id, date, duration_minutes, create_time)
                OVERRIDING SYSTEM VALUE VALUES ($1, $2, $3, $4, $5)
                """,
                # sessions.date is a native DATE column in Postgres (see Step 2) -- asyncpg
                # rejects a plain str here, so parse the SQLite TEXT value into a date object first.
                s["id"], s["project_id"], date.fromisoformat(s["date"]), s["duration_minutes"], s["create_time"],
            )

        # Dead archive table, not used by the app -- copied for completeness, faithfully as-is.
        # No identity column here, so no OVERRIDING SYSTEM VALUE needed for this one.
        legacy = sqlite_conn.execute(
            "SELECT id, start_time, end_time FROM sessions_legacy_data ORDER BY id"
        ).fetchall()
        for row in legacy:
            await pg_conn.execute(
                "INSERT INTO sessions_legacy_data (id, start_time, end_time) VALUES ($1, $2, $3)",
                row["id"], row["start_time"], row["end_time"],
            )

        # projects/sessions use GENERATED ALWAYS AS IDENTITY - the backing sequence doesn't
        # know about these explicitly-inserted ids yet. Advance it past the max, or the next
        # real INSERT (no explicit id) will collide. sessions_legacy_data has no identity column,
        # so it needs no equivalent step.
        await pg_conn.execute(
            "SELECT setval(pg_get_serial_sequence('projects', 'id'), (SELECT MAX(id) FROM projects))"
        )
        await pg_conn.execute(
            "SELECT setval(pg_get_serial_sequence('sessions', 'id'), (SELECT MAX(id) FROM sessions))"
        )

        print(f"Migrated {len(projects)} projects, {len(sessions)} sessions, {len(legacy)} legacy rows.")
    finally:
        sqlite_conn.close()
        await pg_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
```

Two Postgres-specific details worth calling out, both load-bearing:
- **`OVERRIDING SYSTEM VALUE`** — required because `projects`/`sessions` are `GENERATED ALWAYS AS IDENTITY`. Without it, Postgres flatly rejects any `INSERT` that supplies an explicit `id` for such a column.
- **`pg_get_serial_sequence(...)`** — the robust way to find an identity column's backing sequence name, rather than guessing/hardcoding it (e.g. `projects_id_seq`). This is the same category of lesson as the `sqlite_sequence` gotcha encountered during the earlier SQLite schema migration (Step 1 of that plan) — an autoincrement mechanism has separate bookkeeping state that explicit-id inserts can silently leave stale.

Migration order matters — `projects` before `sessions`, for the foreign key. `sessions_legacy_data` has no dependency on either and can go any time.

**Verify after running:**
```sql
SELECT COUNT(*) FROM projects;  -- compare to SQLite's count
SELECT COUNT(*) FROM sessions;  -- compare to SQLite's count
SELECT COUNT(*) FROM sessions_legacy_data;  -- compare to SQLite's count
SELECT seq FROM ... -- N/A in Postgres; instead:
SELECT last_value FROM pg_sequences WHERE sequencename = 'sessions_id_seq';  -- or whatever pg_get_serial_sequence returned
```
Then do one real end-to-end check: run the app locally with `DATABASE_URL` set to the captured Postgres connection string, `POST /api/sessions`, confirm the new row gets an `id` one past the migrated max, not a collision.

This step can be re-run from scratch as many times as needed before cutover (just drop and recreate the Postgres tables via `init_db()` and re-run the script) — nothing here is destructive to the SQLite source.

---

## Step 5 — Cutover: point production at Postgres

This is the actual switch: set `DATABASE_URL` back to the real Postgres connection string captured during Step 1's attach. The database and role already exist on the cluster, so there's no need to run `fly postgres attach` again:

```bash
fly secrets set DATABASE_URL='postgresql://...'   # the connection string captured in Step 1
```

Before running it:
- Re-run Step 4's migration one final time against a *fresh* backup taken immediately before cutover, so no sessions logged since the earlier test migration are lost.
- Remove the plaintext `DATABASE_URL = 'sqlite:////data/measured.db'` line from `fly.toml`'s `[env]` block — `fly deploy` has been printing a warning about this exact thing on every deploy this whole project ("`DATABASE_URL` may be a potentially sensitive environment variable... remove it from the `[env]` section"). A real Postgres connection string with embedded credentials genuinely shouldn't sit in a committed, plaintext config file; `fly secrets` is the correct place for it.

Then `fly deploy` to roll out the `fly.toml` change, and verify: `fly status`, `/api/health`, then a real read (`GET /api/sessions`) and a real write (`POST /api/sessions`, then delete it) against production.

**Rollback plan**: don't delete or unmount the SQLite volume (`measured_data`) or the `measured.db` file at this point, and keep the old SQLite backup workflow running for at least one full backup cycle after cutover. If something's wrong, rollback is just `fly secrets set DATABASE_URL=sqlite:////data/measured.db && fly deploy` — the file is untouched and exactly where it was. Only proceed to Step 6 once production has run against Postgres successfully for a while (a few days of normal use, covering both the create-session and charts-reading paths).

---

## Step 6 — Remove SQLite-specific code paths

Once Postgres is confirmed stable in production and there's no intention of rolling back:

- `backend/app/database.py`: remove the `is_sqlite` branch — collapse to Postgres-only DDL (`INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY`, `date DATE`, unconditionally; `sessions_legacy_data` is already dialect-identical, so it's untouched). Also collapse `routers/sessions.py`'s `adapt_date()` helper — no longer needed once every dialect is Postgres, so its call sites go back to just `session.date` / `min_date` / `max_date` directly.
- `backend/requirements.txt`: remove `databases[aiosqlite]==0.9.0`.
- `backend/tests/conftest.py`: nothing to do here — it's already Postgres-only via `testcontainers` since Step 2, so there's no lingering SQLite test path to retire.

---

## Step 7 — Final cleanup

- `backend/Dockerfile`: remove the `sqlite3` CLI installation (`RUN apt-get install ... sqlite3`) — no longer needed once nothing on the production machine touches a `.sqlite` file.
- `fly volumes list -a measured-backend` → once confident no rollback will ever be needed, `fly volume destroy measured_data`. Not urgent — an idle unused volume costs little and is a free rollback safety net; no rush to remove it.
- Retire `.github/workflows/backup-database.yml` (the SQLite one) — either delete it or leave it disabled, since there's no longer a SQLite file in production for it to back up.
- Update `backend/DEPLOYMENT.md`: its current "Migration to PostgreSQL (Optional)" section describes this as a hypothetical future option — rewrite it to describe the actual setup as it now exists, and fold in the real backup/restore instructions for `pg_dump`/`pg_restore` (mirroring the existing detailed SQLite restore walkthrough there).
- `CLAUDE.md`'s "Database" section describes `measured.db` as the dev/prod database — update to reflect Postgres in prod, Docker Compose Postgres (or SQLite fallback) for dev. Its "Testing" section also still says `conftest.py` sets up an in-memory SQLite database per test — that's been wrong since Step 2; update it to describe the `testcontainers`-backed Postgres setup, with tables truncated after each test. Also document how to reach the production database from a local machine, since `measured-database.flycast` is only reachable from inside Fly's private network: `fly proxy 15432:5432 -a measured-database`, then connect to `localhost:15432` with the app's DB credentials.

---

## Key invariant

Production stays on SQLite throughout, with one brief, deliberate exception: Step 1's attach-then-reset causes a short crash-and-recover blip while `DATABASE_URL` briefly points at Postgres before any code exists to use it — over in the time two redeploys take, and immediately reverted. Everything else in Steps 1–4 is new, inert infrastructure (the Postgres cluster itself, a captured-but-unused connection string, a new backup workflow, a migration script run against copies) that doesn't touch the live app. Step 5 is the real cutover, and it's reversible for as long as the SQLite volume is kept around. Steps 6–7 only remove now-unused code and infrastructure, and only after Postgres has proven itself in production.

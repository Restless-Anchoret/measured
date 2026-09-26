# SQLite → PostgreSQL migration plan

## Recovery note

The original detailed plan document for this migration is unrecoverable — it lived at a global, non-project-scoped path (`~/.claude/plans/`) that gets overwritten by other sessions on this machine, and no copy exists anywhere (checked filesystem, git history, stash). This plan is freshly written, informed by three real sources: a project memory record explaining the original motivation and a since-resolved blocker, two actual git commits (`3ad9de0` / `16e9199`) from a first implementation attempt that was deliberately reverted, and this repo's own `backend/DEPLOYMENT.md`, which already sketches the intended provider (Fly Postgres) in its "Migration to PostgreSQL (Optional)" section.

## Context

**Why**: PostgreSQL for better concurrency than SQLite offers under this app's access patterns.

**Why now**: a prerequisite schema migration (`sessions.start_time`/`end_time` → `date`/`duration_minutes`/`create_time`) was required first — it eliminated a class of timezone bug and, as a side effect relevant here, removed every `TIMESTAMP` column from the schema. That migration is now complete. This matters concretely: the one genuinely tricky part of the earlier reverted attempt was reconciling how `aiosqlite` and `asyncpg` return datetime values differently (native `datetime` objects vs. ISO strings). With no `TIMESTAMP` columns left, that whole problem class is gone — `sessions` now only has `id`, `project_id`, `date` (`TEXT`), `duration_minutes` (`INTEGER`), `create_time` (`BIGINT`), all of which round-trip identically through both drivers with zero dialect-specific code.

**Provider decision**: Fly Postgres (Fly's own managed Postgres, attached to the existing `measured-backend` app). This isn't a new decision — `DEPLOYMENT.md` already names this as the intended path. Keeping everything on one platform avoids adding a second vendor relationship for a single-user app.

**Schema decision — keep `date` as `TEXT` in Postgres too, not native `DATE`.** Postgres does have a real `DATE` type, and it'd be reasonable to use it — but `asyncpg` returns native Postgres `DATE` columns as Python `date` objects, not strings, which would reintroduce exactly the dialect-branching complexity the schema migration just removed. Since the only operations done on `date` are string equality/range comparisons (`date >= :min_date`), which work identically as lexicographic string comparison in Postgres (ISO-8601's sort-order property isn't SQLite-specific), staying with `TEXT` means **zero application code needs to change based on which database is active** — `models.py`, `schemas.py`, and the routers stay byte-for-byte identical between SQLite and Postgres. This is a deliberate simplicity trade-off for a single-developer project; flag if you'd rather use native `DATE` and accept the small conversion shim it requires.

**Test suite stays SQLite-only.** With no remaining dialect-specific data handling, there's little left for a Postgres-backed test run to catch that a SQLite-backed one wouldn't. Keeping `conftest.py`'s in-memory SQLite setup avoids needing a live Postgres instance in CI. Revisit if the two databases ever diverge in behavior that matters.

**Known driver gotcha to handle**: the `databases` library (and modern SQLAlchemy, which it wraps) requires the `postgresql://` URL scheme and rejects the older `postgres://` alias. Fly's auto-generated connection strings use `postgres://`. `database.py` needs to normalize this — see Step 2.

---

## Step 1 — Provision Postgres, without touching the live app yet

**Local dev**, add `docker-compose.yml` at the repo root:

```yaml
services:
  postgres:
    image: postgres:16
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

**Fly Postgres cluster** — create it, but deliberately *don't* attach it to `measured-backend` yet:

```bash
fly postgres create --name measured-db --region ams
```

This stands up an independent Postgres cluster app with no connection to `measured-backend` at all. This separation is intentional: `fly postgres attach` both provisions an app-specific database/role *and* writes a `DATABASE_URL` secret to the target app, which by default triggers an immediate redeploy. Running that now — before Step 2's code exists — would hand the *currently deployed* SQLite-only code a Postgres URL it can't use (no `asyncpg` driver installed) and crash production on startup. Attachment is deferred to Step 5, once the code can actually handle it.

For Step 4's migration script and any pre-cutover testing, get credentials without touching the live app's config, by attaching under a different secret name:

```bash
fly postgres attach --app measured-backend measured-db --variable-name STAGING_DATABASE_URL
```

This still creates the real, dedicated `measured-backend`-scoped database and role on the cluster — it just writes the resulting connection string to `STAGING_DATABASE_URL` instead of `DATABASE_URL`, so it sits there completely inert until Step 5 explicitly promotes it. Note the `postgres://` scheme problem above applies here too — expect to rewrite it to `postgresql://` wherever it's used.

---

## Step 2 — Backend: dual-driver support, prod stays on SQLite

`backend/requirements.txt` — add the Postgres driver alongside the existing one:
```
databases[asyncpg]==0.9.0
asyncpg==0.29.0
```

`backend/app/database.py` — normalize the URL scheme and branch the one piece of DDL that actually differs between dialects (autoincrementing primary keys):
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./measured.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

database = databases.Database(DATABASE_URL)


async def init_db(db: databases.Database | None = None):
    target_db = db if db is not None else database
    is_sqlite = str(target_db.url).startswith("sqlite")
    pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

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
            date TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            create_time BIGINT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
```
This is the *only* file that needs a dialect branch. `models.py`, `schemas.py`, and every router are already dialect-agnostic — `:param`-style bind parameters are translated per-backend by the `databases` library itself, and every remaining column type (`TEXT`, `INTEGER`, `BIGINT`, `VARCHAR`) round-trips identically through both `aiosqlite` and `asyncpg`. `RETURNING` also needs no branching — it's valid syntax in both SQLite (3.35+, already required) and Postgres (where it originated).

Deploy this. Since `DATABASE_URL` hasn't changed, production keeps running SQLite exactly as before — this step only proves the code *can* speak Postgres, without affecting anything live. Sanity-check locally by pointing at the Step 1 Docker Compose instance and running `pytest` plus a manual smoke test (`create_session`, `get_sessions`) against it.

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

      - name: Install PostgreSQL client
        run: sudo apt-get update && sudo apt-get install -y postgresql-client

      - name: Open tunnel and dump database
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          TIMESTAMP=$(date +%Y-%m-%d)
          echo "BACKUP_FILENAME=pg-backup-${TIMESTAMP}.sql.gz" >> $GITHUB_ENV

          flyctl proxy 15432:5432 -a measured-db &
          PROXY_PID=$!
          sleep 5  # wait for the tunnel to establish

          PGPASSWORD="${{ secrets.POSTGRES_BACKUP_PASSWORD }}" \
            pg_dump -h localhost -p 15432 -U measured_backend -d measured_backend \
            | gzip > pg-backup-${TIMESTAMP}.sql.gz

          kill $PROXY_PID

      - name: Verify backup is non-empty
        run: |
          if [ ! -s "${{ env.BACKUP_FILENAME }}" ]; then
            echo "Error: Backup file is empty or does not exist"
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

Exact database/user names (`measured_backend`, etc.) come from whatever `fly postgres attach` actually names them — check with `fly postgres db list -a measured-db` and `fly postgres users list -a measured-db` and adjust. `POSTGRES_BACKUP_PASSWORD` is a new GitHub secret holding that role's password (visible once at attach time, or resettable via `fly postgres users create`/`fly ssh console -a measured-db` + `psql`).

**Verify this workflow end-to-end against the Step 1 staging database before Step 5's cutover** — trigger it manually (`workflow_dispatch`), confirm a real, restorable dump comes out, before any production data actually depends on it existing.

Keep the existing SQLite backup workflow running unmodified through Step 5 — production is still SQLite until then.

---

## Step 4 — One-time data migration: copy existing SQLite data into Postgres

A one-off Python script, `backend/app/sessions-migration/migrate_to_postgres.py` (matching this repo's existing convention of keeping one-time migration scripts in that folder), run manually, once, against a fresh copy of the production SQLite file and the Step 1 staging Postgres database:

```python
#!/usr/bin/env python3
"""One-time copy of projects/sessions from SQLite into PostgreSQL."""
import sqlite3
import asyncio
import asyncpg

SQLITE_PATH = "measured.db"  # a local copy of the prod backup, not the live file
POSTGRES_URL = "postgresql://..."  # the STAGING_DATABASE_URL value from Step 1, postgresql:// scheme


async def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = await asyncpg.connect(POSTGRES_URL)

    try:
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
                s["id"], s["project_id"], s["date"], s["duration_minutes"], s["create_time"],
            )

        # Both tables use GENERATED ALWAYS AS IDENTITY - the backing sequence doesn't know
        # about these explicitly-inserted ids yet. Advance it past the max, or the next
        # real INSERT (no explicit id) will collide.
        await pg_conn.execute(
            "SELECT setval(pg_get_serial_sequence('projects', 'id'), (SELECT MAX(id) FROM projects))"
        )
        await pg_conn.execute(
            "SELECT setval(pg_get_serial_sequence('sessions', 'id'), (SELECT MAX(id) FROM sessions))"
        )

        print(f"Migrated {len(projects)} projects, {len(sessions)} sessions.")
    finally:
        sqlite_conn.close()
        await pg_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
```

Two Postgres-specific details worth calling out, both load-bearing:
- **`OVERRIDING SYSTEM VALUE`** — required because these columns are `GENERATED ALWAYS AS IDENTITY`. Without it, Postgres flatly rejects any `INSERT` that supplies an explicit `id` for such a column. (`GENERATED BY DEFAULT AS IDENTITY` wouldn't need this, but Step 2 already committed to `ALWAYS`, matching the earlier reverted attempt's choice.)
- **`pg_get_serial_sequence(...)`** — the robust way to find an identity column's backing sequence name, rather than guessing/hardcoding it (e.g. `projects_id_seq`). This is the same category of lesson as the `sqlite_sequence` gotcha encountered during the earlier SQLite schema migration (Step 1 of that plan) — an autoincrement mechanism has separate bookkeeping state that explicit-id inserts can silently leave stale.

Migration order matters — `projects` before `sessions`, for the foreign key.

**Verify after running:**
```sql
SELECT COUNT(*) FROM projects;  -- compare to SQLite's count
SELECT COUNT(*) FROM sessions;  -- compare to SQLite's count
SELECT seq FROM ... -- N/A in Postgres; instead:
SELECT last_value FROM pg_sequences WHERE sequencename = 'sessions_id_seq';  -- or whatever pg_get_serial_sequence returned
```
Then do one real end-to-end check: `POST /api/sessions` against the app running with `DATABASE_URL` pointed at staging Postgres, confirm the new row gets an `id` one past the migrated max, not a collision.

This step can be re-run from scratch as many times as needed before cutover (just drop and recreate the Postgres tables via `init_db()` and re-run the script) — nothing here is destructive to the SQLite source.

---

## Step 5 — Cutover: point production at Postgres

This is the actual switch, and the moment `fly postgres attach` (the real one, writing to `DATABASE_URL`) happens:

```bash
fly postgres attach --app measured-backend measured-db
```

Before running it:
- Re-run Step 4's migration one final time against a *fresh* backup taken immediately before cutover, so no sessions logged between the staging copy and now are lost.
- Remove the plaintext `DATABASE_URL = 'sqlite:////data/measured.db'` line from `fly.toml`'s `[env]` block — `fly deploy` has been printing a warning about this exact thing on every deploy this whole project ("`DATABASE_URL` may be a potentially sensitive environment variable... remove it from the `[env]` section"). A real Postgres connection string with embedded credentials genuinely shouldn't sit in a committed, plaintext config file; `fly secrets` is the correct place for it, and `attach` writes there automatically.

Then `fly deploy` to roll out the `fly.toml` change, and verify: `fly status`, `/api/health`, then a real read (`GET /api/sessions`) and a real write (`POST /api/sessions`, then delete it) against production.

**Rollback plan**: don't delete or unmount the SQLite volume (`measured_data`) or the `measured.db` file at this point, and keep the old SQLite backup workflow running for at least one full backup cycle after cutover. If something's wrong, rollback is just `fly secrets set DATABASE_URL=sqlite:////data/measured.db && fly deploy` — the file is untouched and exactly where it was. Only proceed to Step 6 once production has run against Postgres successfully for a while (a few days of normal use, covering both the create-session and charts-reading paths).

---

## Step 6 — Remove SQLite-specific code paths

Once Postgres is confirmed stable in production and there's no intention of rolling back:

- `backend/app/database.py`: remove the `is_sqlite` branch and the `postgres://` → `postgresql://` rewrite's SQLite half — collapse to Postgres-only DDL (`INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY` unconditionally).
- `backend/requirements.txt`: remove `databases[aiosqlite]==0.9.0`.
- `backend/tests/conftest.py`: this currently sets up an in-memory SQLite database per test. Decide here whether to point it at a real (local/CI) Postgres instance instead, or keep a SQLite-only test path indefinitely by *not* fully removing the `aiosqlite` extra from a dev-only dependency group. This is a genuine open decision deferred from Step 2's "tests stay SQLite" call — revisit once Postgres has been live long enough to know whether any behavior actually diverged.

---

## Step 7 — Final cleanup

- `backend/Dockerfile`: remove the `sqlite3` CLI installation (`RUN apt-get install ... sqlite3`) — no longer needed once nothing on the production machine touches a `.sqlite` file.
- `fly volumes list -a measured-backend` → once confident no rollback will ever be needed, `fly volume destroy measured_data`. Not urgent — an idle unused volume costs little and is a free rollback safety net; no rush to remove it.
- Retire `.github/workflows/backup-database.yml` (the SQLite one) — either delete it or leave it disabled, since there's no longer a SQLite file in production for it to back up.
- `fly secrets unset STAGING_DATABASE_URL` (from Step 1) — no longer needed once `DATABASE_URL` itself is the real thing.
- Update `backend/DEPLOYMENT.md`: its current "Migration to PostgreSQL (Optional)" section describes this as a hypothetical future option — rewrite it to describe the actual setup as it now exists, and fold in the real backup/restore instructions for `pg_dump`/`pg_restore` (mirroring the existing detailed SQLite restore walkthrough there).
- `CLAUDE.md`'s "Database" section describes `measured.db` as the dev/prod database — update to reflect Postgres in prod, Docker Compose Postgres (or SQLite fallback) for dev.

---

## Key invariant

At no point does production stop working. Steps 1–4 touch only new, inert infrastructure (a separate Postgres cluster, a `STAGING_DATABASE_URL` secret nothing reads, a new backup workflow, a script run against copies) — the live app keeps running unmodified SQLite-backed code throughout. Step 5 is the single moment of actual change, and it's reversible for as long as the SQLite volume is kept around. Steps 6–7 only remove now-unused code and infrastructure, and only after Postgres has proven itself in production.

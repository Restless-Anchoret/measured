#!/usr/bin/env python3
"""One-time copy of projects/sessions from SQLite into PostgreSQL.

Configure via environment variables before running -- never hardcode real
credentials into this file, since it's committed to the repo:
    SQLITE_PATH   path to a local copy of the production SQLite file (not the live file)
    POSTGRES_URL  postgresql:// connection string for the target Postgres database

Usage:
    SQLITE_PATH=./measured_prod_snapshot.db POSTGRES_URL=postgresql://... \
        python migrate_to_postgres.py
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
                # sessions.date is a native DATE column in Postgres -- asyncpg rejects a
                # plain str here, so parse the SQLite TEXT value into a date object first.
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
        # real INSERT (no explicit id) will collide. sessions_legacy_data has no identity
        # column, so it needs no equivalent step.
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

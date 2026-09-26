# Sessions date+duration+create_time migration plan

## Context

Migrate the `sessions` table:
- `start_time TIMESTAMP` + `end_time TIMESTAMP` → `date TEXT` (YYYY-MM-DD) + `duration_minutes INTEGER`. Precision loss is acceptable.
- `created_at TIMESTAMP` → `create_time BIGINT` (milliseconds since 1970-01-01 UTC epoch). `created_at` is currently written via SQLite's `CURRENT_TIMESTAMP`, which produces a naive `YYYY-MM-DD HH:MM:SS` string — always UTC in practice, but with no timezone marker, and inconsistent historically with a handful of offset-aware rows written by other code paths. An epoch-millisecond integer has no naive/aware distinction to get wrong and sorts/compares correctly as a plain integer.

**API strategy**: no real API versioning is introduced — this is a deliberately messy two-hop routing dance, acceptable because this is a single-use project:

1. The existing `POST`/`PUT /api/sessions` handlers keep their current request contract (`start_time`/`end_time`), but are corrected to also derive and write the new columns internally (Step 2).
2. A **temporary** pair of new-fields-only endpoints is added at `POST`/`PUT /api/v1/sessions-temp` (Step 4). Frontend migrates its writes there (Step 5).
3. The old `/api/sessions` write handlers and old columns are then retired (Steps 6–7).
4. Later, the *same* logic is additionally exposed at its real intended home, `POST`/`PUT /api/v1/sessions`, alongside the still-live `sessions-temp` routes (Step 8). Frontend migrates a second time, from `sessions-temp` to the new `/api/v1/sessions`.
5. `sessions-temp` is then deleted entirely (Step 9), since nothing calls it anymore.

`GET`/`DELETE` are unaffected by any of this — they stay at the plain `/api/sessions` / `/api/sessions/{id}` paths throughout, since read filtering can support old and new query params on the same handler with no contract conflict, and delete-by-id doesn't care which endpoint created the row.

`create_time` is server-generated only, on every write path — it's never part of any request body.

---

## Step 1 — DB: add new nullable columns, relax NOT NULL on old columns

Since `start_time`/`created_at` need `NOT NULL` removed, and SQLite has no `ALTER TABLE ... ALTER COLUMN` for that, **the whole schema change — new columns and relaxed constraints — happens in one table rebuild**, rather than `ALTER TABLE ADD COLUMN` followed by a separate rebuild. This runs as one script, in a transaction, using SQLite's documented recreate-table procedure (the table has no indexes beyond the primary key today, so nothing else needs recreating):

```sql
PRAGMA foreign_keys=off;

CREATE TABLE sessions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP,
    date TEXT,
    duration_minutes INTEGER,
    create_time BIGINT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

INSERT INTO sessions_new (id, project_id, start_time, end_time, created_at)
SELECT id, project_id, start_time, end_time, created_at FROM sessions;

DROP TABLE sessions;
ALTER TABLE sessions_new RENAME TO sessions;

PRAGMA foreign_keys=on;
```

`date`, `duration_minutes`, `create_time` aren't in the `INSERT`'s column list, so every existing row gets them as `NULL` — exactly what Step 3's backfill expects. `created_at` no longer has `DEFAULT CURRENT_TIMESTAMP` — every write path (Step 2's `create_session`) already sets it explicitly, so the default was dead weight.

Verify the `AUTOINCREMENT` sequence carried over correctly (explicit `id` values in the copy don't auto-update `sqlite_sequence` any differently than normal inserts, but worth confirming before trusting future inserts):
```sql
SELECT seq FROM sqlite_sequence WHERE name = 'sessions';
SELECT MAX(id) FROM sessions;
```
These two values should be equal.

Also update `backend/app/database.py:init_db()` `CREATE TABLE IF NOT EXISTS` to match this final nullable shape directly, so fresh test/dev databases get it at creation time:
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP,
    date TEXT,
    duration_minutes INTEGER,
    create_time BIGINT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
)
```

---

## Step 2 — Backend: correct existing `/api/sessions` handlers to also populate new fields

Existing endpoints keep their request contract — no dual-field input handling added.

- `backend/app/models.py`: add `date: Optional[date]`, `duration_minutes: Optional[int]`, `create_time: Optional[datetime]` (tz-aware UTC) to `Session`; also change `start_time: datetime` → `Optional[datetime]` and `created_at: datetime` → `Optional[datetime]` (rows created via the future new-fields-only path will leave these `None`). Update `from_row()`:
  ```python
  start_time=datetime.fromisoformat(row["start_time"]) if row["start_time"] else None,
  end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
  created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
  date=date.fromisoformat(row["date"]) if row["date"] else None,
  duration_minutes=row["duration_minutes"],
  create_time=datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=row["create_time"]) if row["create_time"] else None,
  ```
  Requires `from datetime import date, datetime, timezone, timedelta` (note the field name `date` and type name `date` coincide — safe here since class bodies aren't an enclosing scope for their methods, but worth knowing if it looks odd in a diff). Epoch + `timedelta(milliseconds=...)` is exact integer arithmetic — no floating-point division, unlike `fromtimestamp(ms / 1000, ...)`.
- `backend/app/schemas.py` `Session` response (shared by every endpoint in this plan, old and new): `start_time`, `end_time`, `created_at` become `Optional`; add `date: Optional[date]`, `duration_minutes: Optional[int]`, `create_time: Optional[datetime]`. A row created via the new-fields-only path will simply show `null` for the old fields in JSON.
- `backend/app/routers/sessions.py`: add module-level `from zoneinfo import ZoneInfo` and `AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")`. Using the IANA tz database (via `zoneinfo`, stdlib since Python 3.9) instead of a fixed offset correctly handles the CET/CEST daylight-saving transition (UTC+1 in winter, UTC+2 in summer), rather than assuming a permanent offset.
- `backend/app/routers/sessions.py:create_session` (line ~28): compute before INSERT:
  ```python
  date = session.start_time.astimezone(AMSTERDAM_TZ).date().isoformat()
  duration_minutes = int((session.end_time - session.start_time).total_seconds() / 60) if session.end_time else None
  ```
  `session.start_time` is timezone-aware (the frontend sends `.toISOString()`, always UTC-with-offset); `.astimezone()` converts it to Amsterdam local time before extracting the date. (If `start_time` were ever naive, `.astimezone()` would incorrectly assume the system's local timezone — not a concern today since Pydantic parsing always preserves the incoming UTC offset, but worth knowing.)

  `created_at` and `create_time` are now computed in Python from a single shared "now" value, instead of two separate SQL-side expressions (`CURRENT_TIMESTAMP` and `julianday('now')`), so both are guaranteed to represent the exact same instant:
  ```python
  now = datetime.now(timezone.utc)
  create_time = (now - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(milliseconds=1)
  ```
  (Integer floor-division between two `timedelta`s — exact, no floating-point conversion, same approach as the `from_row` reconstruction in `models.py`.) Requires `from datetime import datetime, timezone, timedelta` at module level.

  INSERT now also sets `date`, `duration_minutes`, `create_time`, and passes `created_at`/`create_time` as bound parameters instead of inline SQL expressions:
  ```sql
  INSERT INTO sessions (project_id, start_time, end_time, created_at, date, duration_minutes, create_time)
  VALUES (:project_id, :start_time, :end_time, :created_at, :date, :duration_minutes, :create_time)
  RETURNING *
  ```
  with `"created_at": now.isoformat()` and `"create_time": create_time` added to the query params.
- `backend/app/routers/sessions.py:update_session` (line ~134): same `date`/`duration_minutes` derivation before UPDATE. `create_time` is not touched (represents original creation).
- `backend/tests/test_sessions.py`: assert `POST`/`PUT /api/sessions` responses populate all 6 fields (3 old + 3 new).

---

## Step 3 — Data migration: backfill existing rows

Run against prod DB (via `fly ssh console`):

```sql
UPDATE sessions
SET
    date = DATE(start_time, '+2 hours'),
    duration_minutes = (CAST(strftime('%s', end_time) AS INTEGER) - CAST(strftime('%s', start_time) AS INTEGER)) / 60,
    create_time = CAST(strftime('%s', created_at) AS INTEGER) * 1000
WHERE date IS NULL;
```
(`end_time` is `NOT NULL` for every row in production today, so the separate no-`end_time` fallback branch is dead code and dropped. All three new columns are backfilled in one pass.)

No `julianday()` anywhere, and no millisecond extraction either — dropped since it's unnecessary here:
- `duration_minutes` only needs minute-level output, so the final `/ 60` throws away sub-second precision regardless of whether the subtraction was done in seconds or milliseconds — using `strftime('%s', x)` (whole seconds) directly is exactly as accurate as the millisecond version for this purpose.
- `create_time`'s source, `created_at`, was always written via SQLite's `CURRENT_TIMESTAMP`, which is documented to produce whole-second precision only — confirmed against the actual historical data (e.g. `'2026-06-20 14:04:26'`, `'2026-06-06 17:11:29'`, no fractional seconds on any row). So the millisecond component would always be `0` for every row this backfill touches; `strftime('%s', created_at) * 1000` is exact, not an approximation.

`strftime('%s', x)` returns the exact integer count of whole seconds since the Unix epoch — still no floats anywhere. `duration_minutes` truncates any leftover sub-minute remainder (integer `/`, not rounded to nearest minute).

`start_time` is stored in UTC; `+2 hours` offsets to UTC+2 before extracting the date. All existing sessions are assumed to belong to a UTC+2 user.

`created_at` backfill treats existing naive values as UTC — safe because SQLite's `CURRENT_TIMESTAMP` is documented to always return UTC, regardless of how it's displayed.

Verify:
- `SELECT COUNT(*) FROM sessions WHERE date IS NULL` → 0.
- `SELECT COUNT(*) FROM sessions WHERE create_time IS NULL` → 0.

---

## Step 4 — New backend: temporary new-fields-only endpoints at `/api/v1/sessions-temp`

- New file `backend/app/routers/sessions_temp.py`, mounted in `main.py`:
  ```python
  app.include_router(sessions_temp.router, prefix="/api/v1", tags=["sessions-temp"])
  ```
  with routes defined as `@router.post("/sessions-temp")` and `@router.put("/sessions-temp/{session_id}")`, giving final paths `POST /api/v1/sessions-temp` and `PUT /api/v1/sessions-temp/{id}`.
- New schemas in `schemas.py` (deliberately not "v2"-named, since these get reused as-is at the final path in Step 8):
  ```python
  class SessionCreateNew(BaseModel):
      project_id: int
      date: date
      duration_minutes: int

  class SessionUpdateNew(BaseModel):
      date: date
      duration_minutes: int
  ```
  Both fields required on each (full-replace semantics on update, matching the existing endpoint's current behavior) — no `start_time`/`end_time` anywhere in this contract, no fallback logic.
- `POST /api/v1/sessions-temp`: verify project exists (same check as the existing handler); INSERT only `project_id, date, duration_minutes, create_time` — `start_time`/`end_time`/`created_at` left `NULL` (possible now that Step 1 relaxed those constraints). Returns the shared `Session` response schema.
- `PUT /api/v1/sessions-temp/{id}`: UPDATE `date`, `duration_minutes` only.
- `GET /api/sessions` (unversioned, shared, line ~47): add `min_date: Optional[str]` / `max_date: Optional[str]` query params alongside existing `min_start_time`/`max_start_time` — both param sets coexist with no conflict, since this is read-only filtering. Change `ORDER BY start_time DESC` → `ORDER BY date DESC, id DESC` (safe post-Step-3, every row has `date`).
- `GET /api/sessions/{id}` and `DELETE /api/sessions/{id}`: unchanged, and stay unchanged for the rest of this plan.
- `backend/tests/test_sessions.py`: new section for `sessions-temp` — assert `POST` leaves `start_time`/`end_time`/`created_at` `null` in the response and sets `date`/`duration_minutes`/`create_time` correctly.

---

## Step 5 — Frontend: migrate writes to `/api/v1/sessions-temp`

- `frontend/src/lib/types.ts`: `Session` type — `start_time`, `end_time`, `created_at` become optional/nullable; add `date: string`, `duration_minutes: number`, `create_time: string` (ISO-8601 datetime string).
- `frontend/src/pages/LogSession.tsx` (line ~81): POST to `/api/v1/sessions-temp` with `{ project_id, date: format(values.date, 'yyyy-MM-dd'), duration_minutes: values.duration }` — remove timestamp computation (lines ~63–78).
- Session edit flow in `frontend/src/pages/Sessions.tsx`: switch its `PUT` call to `/api/v1/sessions-temp/{id}` with `{ date, duration_minutes }`.
  - `formatDuration` (line ~68): use `session.duration_minutes` directly.
  - `formatStartDate` (line ~79): use `session.date` directly.
  - Update delete dialog description (line ~174).
- `frontend/src/components/SessionsChart.tsx`:
  - `CompletedSession`: replace `startTime: Date` with `date: string`.
  - `convertToCompletedSessions` (line ~83): use `session.duration_minutes`; filter on `duration_minutes != null`; store `session.date`.
  - `groupSessionsIntoTimeSegments` (line ~100): parse date as local midnight `new Date(session.date + 'T00:00:00')` to avoid UTC/local mismatch with segment boundaries.
  - `totalDuration` (line ~240): sum `session.duration_minutes` directly.
- `frontend/src/hooks/useSessions.ts`: rename params `minStartTime`/`maxStartTime` → `minDate`/`maxDate` (as `Date` objects); format internally as `yyyy-MM-dd`; send as `min_date`/`max_date` (GET stays at `/api/sessions`).
- Update `SessionsChart.tsx` call site (line ~204) accordingly.
- `create_time` is not currently rendered anywhere in the UI — no component changes needed beyond the type addition.

---

## Step 6 — Backend: remove old `/api/sessions` write handlers and old fields from code

Only once the frontend no longer calls the old write endpoints:

- `backend/app/routers/sessions.py`: delete `create_session` and `update_session` entirely — removes `POST /api/sessions`, `PUT /api/sessions/{id}`. `get_session`, `get_sessions`, `delete_session` stay, with old-field references (`min_start_time`/`max_start_time`, `start_time`/`end_time`/`created_at` in SQL) removed.
- `backend/app/schemas.py` / `backend/app/models.py`: remove the old `SessionCreate`/`SessionUpdate` schemas and `start_time`/`end_time`/`created_at` from `Session` entirely.
- `backend/app/database.py`: `CREATE TABLE` drops `start_time`, `end_time`, `created_at`.

---

## Step 7 — DB: drop old columns

```sql
ALTER TABLE sessions DROP COLUMN start_time;
ALTER TABLE sessions DROP COLUMN end_time;
ALTER TABLE sessions DROP COLUMN created_at;
```

By this point the columns are already nullable, so a plain `DROP COLUMN` (SQLite 3.35+, same requirement as `RETURNING`) works directly — no table rebuild needed here, unlike Step 1. Run on prod DB and verify with `.schema sessions`.

Adding `NOT NULL` constraints to `date`/`duration_minutes`/`create_time` requires table recreation again (SQLite limitation) — optional, since code guarantees non-null values after Steps 2–3 and Step 6 removed the only write path that could leave them null.

---

## Step 8 — Backend + frontend: promote `sessions-temp` logic to its real home, `/api/v1/sessions`

Purely a routing rename — no schema or logic changes, since `sessions-temp` and old `/api/sessions` were already retired/superseded by Steps 6–7.

- In `backend/app/routers/sessions_temp.py`, add a second path decorator to the same handler functions, so both paths route to identical logic during the overlap window:
  ```python
  @router.post("/sessions-temp")
  @router.post("/sessions")
  async def create_session_new(...): ...

  @router.put("/sessions-temp/{session_id}")
  @router.put("/sessions/{session_id}")
  async def update_session_new(...): ...
  ```
  This gives `POST`/`PUT /api/v1/sessions` (new final path) alongside the still-live `/api/v1/sessions-temp` (old temp path) — both work identically.
- Frontend migrates its write calls a second time: `/api/v1/sessions-temp` → `/api/v1/sessions` in `LogSession.tsx` and `Sessions.tsx` (same request/response shapes, only the URL changes).

---

## Step 9 — Backend: remove `sessions-temp` entirely

Once frontend no longer calls `/api/v1/sessions-temp`:

- Remove the `@router.post("/sessions-temp")` / `@router.put("/sessions-temp/{session_id}")` decorators added in Step 4/8, leaving only the `/sessions` decorators.
- Consider renaming `sessions_temp.py` → `sessions_v1.py` or folding it into the main `sessions.py` router at this point, now that "temp" no longer describes it. Not required for correctness, just cleanup.

---

## Key invariant

At no point is data lost. Steps 1–3 are purely additive (new columns, relaxed constraints, backfill) — no existing data is altered destructively. Step 4 introduces the new-fields-only write path as a strict addition, running alongside the existing one. Step 5 shifts frontend traffic to it. Steps 6–7 remove the old contract and old columns once nothing references them. Steps 8–9 are a pure routing rename with no data implications, cleaning up the throwaway `sessions-temp` path once its replacement is live.

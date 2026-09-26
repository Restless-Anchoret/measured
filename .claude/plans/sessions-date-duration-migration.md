# Sessions date+duration+create_time migration plan

## Context

Migrate the `sessions` table:
- `start_time TIMESTAMP` + `end_time TIMESTAMP` → `date TEXT` (YYYY-MM-DD) + `duration_minutes INTEGER`. Precision loss is acceptable.
- `created_at TIMESTAMP` → `create_time BIGINT` (milliseconds since 1970-01-01 UTC epoch). `created_at` is currently written via SQLite's `CURRENT_TIMESTAMP`, which produces a naive `YYYY-MM-DD HH:MM:SS` string — always UTC in practice, but with no timezone marker, and inconsistent historically with a handful of offset-aware rows written by other code paths. An epoch-millisecond integer has no naive/aware distinction to get wrong and sorts/compares correctly as a plain integer.

**API strategy**: no new endpoints and no versioning — the existing `POST`/`PUT /api/sessions` handlers are extended in place to accept *either* the old fields (`start_time`/`end_time`) or the new ones (`date`/`duration_minutes`) in the same request body, enforced by a Pydantic cross-field validator. The router branches on whichever pair was actually sent. Frontend migrates by changing what it sends to the same URLs (Step 5) — no second cutover, no temporary routes to clean up later.

1. The existing `POST`/`PUT /api/sessions` handlers keep accepting `start_time`/`end_time` and derive/write the new columns internally (Step 2 — already done).
2. The same handlers are extended to *also* accept `date`/`duration_minutes` directly, skipping the old fields entirely when present (Step 4).
3. Frontend switches to sending `date`/`duration_minutes` to the same endpoints (Step 5).
4. Once frontend no longer sends the old fields, `start_time`/`end_time` support is dropped from the request/response contract (Step 6), then the columns themselves are dropped from the DB (Step 7).

`GET`/`DELETE` are unaffected by any of this — they stay at the plain `/api/sessions` / `/api/sessions/{id}` paths throughout, since read filtering can support old and new query params on the same handler with no contract conflict, and delete-by-id doesn't care which fields a row has.

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

## Step 4 — Backend: accept `date`/`duration_minutes` directly on the existing endpoints

- `backend/app/schemas.py`:
  ```python
  from pydantic import BaseModel, ConfigDict, model_validator

  class SessionCreate(BaseModel):
      project_id: int
      start_time: Optional[datetime] = None
      end_time: Optional[datetime] = None
      date: Optional[date_type] = None
      duration_minutes: Optional[int] = None

      @model_validator(mode="after")
      def check_fields(self):
          has_new = self.date is not None and self.duration_minutes is not None
          has_old = self.start_time is not None
          if not has_new and not has_old:
              raise ValueError("Provide either (date and duration_minutes) or start_time")
          return self

  class SessionUpdate(BaseModel):
      start_time: Optional[datetime] = None
      end_time: Optional[datetime] = None
      date: Optional[date_type] = None
      duration_minutes: Optional[int] = None

      @model_validator(mode="after")
      def check_fields(self):
          has_new = self.date is not None and self.duration_minutes is not None
          has_old = self.start_time is not None and self.end_time is not None
          if not has_new and not has_old:
              raise ValueError("Provide either (date and duration_minutes) or (start_time and end_time)")
          return self
  ```
  `SessionBase` goes away — `SessionCreate` no longer needs to inherit a required `start_time`. A `model_validator` raising `ValueError` goes through the same Pydantic → `RequestValidationError` path as any other field error, so `main.py`'s existing custom handler already turns this into a 400 with no new code.
- `backend/app/routers/sessions.py:create_session`: branch on which pair was supplied:
  ```python
  if session.date is not None and session.duration_minutes is not None:
      date = session.date.isoformat()
      duration_minutes = session.duration_minutes
      start_time_value = None
      end_time_value = None
  else:
      date = session.start_time.astimezone(AMSTERDAM_TZ).date().isoformat()
      duration_minutes = (
          int((session.end_time - session.start_time).total_seconds() / 60)
          if session.end_time else None
      )
      start_time_value = session.start_time.isoformat()
      end_time_value = session.end_time.isoformat() if session.end_time else None
  ```
  INSERT uses `start_time_value`/`end_time_value` in place of `session.start_time.isoformat()` directly, since `session.start_time` may now be `None`.
- `update_session`: same branching. On the new-style path, `start_time`/`end_time` are explicitly set to `NULL` in the `UPDATE` too — switching a row over to date-based input clears out the now-stale legacy timestamp rather than leaving a contradictory leftover value next to the new `date`.
- `GET /api/sessions` (line ~47): add `min_date: Optional[str]` / `max_date: Optional[str]` query params alongside existing `min_start_time`/`max_start_time` — both param sets coexist with no conflict, since this is read-only filtering. Change `ORDER BY start_time DESC` → `ORDER BY date DESC, id DESC` (safe post-Step-3, every row has `date`).
- `backend/tests/test_sessions.py`: add tests for the new-style `POST`/`PUT` (only `date`/`duration_minutes` sent, `start_time`/`end_time` come back `null`), and a test asserting a request with neither old nor new fields gets a 400.

---

## Step 5 — Frontend: send `date`/`duration_minutes` to the same endpoints

- `frontend/src/lib/types.ts`: `Session` type — `start_time`/`end_time` become optional/nullable; add `date: string`, `duration_minutes: number`.
- `frontend/src/pages/LogSession.tsx` (line ~81): `POST /api/sessions` with `{ project_id, date: format(values.date, 'yyyy-MM-dd'), duration_minutes: values.duration }` — remove timestamp computation (lines ~63–78). Same URL as today, just a different body.
- Session edit flow in `frontend/src/pages/Sessions.tsx`: `PUT /api/sessions/{id}` with `{ date, duration_minutes }` instead of `{ start_time, end_time }`.
  - `formatDuration` (line ~68): use `session.duration_minutes` directly.
  - `formatStartDate` (line ~79): use `session.date` directly.
  - Update delete dialog description (line ~174).
- `frontend/src/components/SessionsChart.tsx`:
  - `CompletedSession`: replace `startTime: Date` with `date: string`.
  - `convertToCompletedSessions` (line ~83): use `session.duration_minutes`; filter on `duration_minutes != null`; store `session.date`.
  - `groupSessionsIntoTimeSegments` (line ~100): parse date as local midnight `new Date(session.date + 'T00:00:00')` to avoid UTC/local mismatch with segment boundaries.
  - `totalDuration` (line ~240): sum `session.duration_minutes` directly.
- `frontend/src/hooks/useSessions.ts`: rename params `minStartTime`/`maxStartTime` → `minDate`/`maxDate` (as `Date` objects); format internally as `yyyy-MM-dd`; send as `min_date`/`max_date`.
- Update `SessionsChart.tsx` call site (line ~204) accordingly.

---

## Step 6 — Backend: drop old-field support from the API contract

Only once the frontend no longer sends `start_time`/`end_time`:

- `backend/app/schemas.py`: remove `start_time`/`end_time`/the validator/old-style branch from `SessionCreate`/`SessionUpdate` — `date`/`duration_minutes` become required, plain fields again. Remove `start_time`/`end_time` from the `Session` response schema.
- `backend/app/routers/sessions.py`: `create_session`/`update_session` drop the old-style branch entirely — always derive from `session.date`/`session.duration_minutes`, and stop including `start_time`/`end_time` in the `INSERT`/`UPDATE` SQL at all (the columns still exist until Step 7, so omitting them just leaves whatever they already were — `NULL` for any row touched since Step 4).
- `backend/app/routers/sessions.py:get_sessions`: remove `min_start_time`/`max_start_time` params and their SQL.
- `backend/app/models.py` is **not** touched here — it still mirrors the actual DB row, which still has `start_time`/`end_time`/`created_at` columns until Step 7 drops them. Trimming it now would be premature; that happens in Step 7 instead.

---

## Step 7 — DB: drop old columns, then catch up `models.py`/`database.py`

```sql
ALTER TABLE sessions DROP COLUMN start_time;
ALTER TABLE sessions DROP COLUMN end_time;
ALTER TABLE sessions DROP COLUMN created_at;
```

The columns are already nullable, so a plain `DROP COLUMN` (SQLite 3.35+, same requirement as `RETURNING`) works directly — no table rebuild needed here, unlike Step 1. Run on prod DB and verify with `.schema sessions`.

Now that the columns are actually gone, update the code that still reads them:
- `backend/app/models.py`: remove `start_time`, `end_time`, `created_at` from the `Session` dataclass and `from_row()` — `row["start_time"]` etc. would `KeyError` once the columns don't exist.
- `backend/app/database.py`: `CREATE TABLE IF NOT EXISTS` drops `start_time`, `end_time`, `created_at` for fresh databases.

Adding `NOT NULL` constraints to `date`/`duration_minutes`/`create_time` requires table recreation again (SQLite limitation) — optional, since code guarantees non-null values after Steps 2–3 and 6 removed the only write path that could leave them null.

---

## Key invariant

At no point is data lost. Steps 1–3 are purely additive (new columns, relaxed constraints, backfill) — no existing data is altered destructively. Step 4 adds a new accepted input shape to the existing endpoints without removing the old one. Step 5 shifts frontend traffic to the new shape. Step 6 removes the old contract once nothing sends it. Step 7 drops the old columns and updates `models.py`/`database.py` to match, once nothing reads them either.

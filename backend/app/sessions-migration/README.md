# Session Migration Tool

This directory contains a Python script for migrating historical session data into the database.

## Files

- `migrate_sessions.py` - Main migration script
- `symbol_mappings.txt` - Maps short symbols to project names
- `sessions_data.txt` - Contains session data with dates and durations
- `README.md` - This file

## Usage

1. **Prepare symbol mappings** (`symbol_mappings.txt`):
   ```
   Ю - Computer games
   ЧХ - YouTube
   ЧТ - Running
   ```

2. **Add session data** (`sessions_data.txt`):
   ```
   14.12 - Ю 4ч45мин ЧХ 25мин ЧТ 15мин
   15.12 - V 2ч С 1ч30мин
   ```

3. **Run the migration script**:
   ```bash
   cd backend/app/sessions-migration
   python migrate_sessions.py
   ```

4. **Review and execute the generated SQL**:
   - Output file: `backend/sql/02_migrate_sessions.sql`
   - Review the SQL statements
   - Execute against your database

## Data Format

### Symbol Mappings Format
```
SYMBOL - PROJECT_NAME
```

Example:
- `Ю - Computer games`
- `ЧХ - YouTube`

### Sessions Data Format
```
DD.MM - SYMBOL1 DURATION SYMBOL2 DURATION ...
```

Duration formats:
- `Xч` = X hours
- `Xмин` = X minutes  
- `XчYмин` = X hours and Y minutes

Example:
```
14.12 - Ю 4ч45мин ЧХ 25мин ЧТ 15мин V 25мин С 1ч20мин
```

### Date Rules

- **December (month 12)** → Year 2025
- **January/February (months 1-2)** → Year 2026

### Time Calculation Rules

- First session starts at **9:00 UTC** by default
- Each session starts when the previous one ends (no gaps)
- If total duration for a day exceeds **15 hours**, the start time is adjusted backwards to ensure all sessions fit within the same date

## Example Workflow

1. Input in `symbol_mappings.txt`:
   ```
   Ю - Computer games
   ЧХ - YouTube
   ```

2. Input in `sessions_data.txt`:
   ```
   14.12 - Ю 4ч45мин ЧХ 25мин
   ```

3. Run migration:
   ```bash
   python migrate_sessions.py
   ```

4. Output in `backend/sql/02_migrate_sessions.sql`:
   ```sql
   INSERT INTO sessions (project_id, start_time, end_time, created_at)
   VALUES (1, '2025-12-14 09:00:00', '2025-12-14 13:45:00', CURRENT_TIMESTAMP);
   
   INSERT INTO sessions (project_id, start_time, end_time, created_at)
   VALUES (2, '2025-12-14 13:45:00', '2025-12-14 14:10:00', CURRENT_TIMESTAMP);
   ```

## Error Handling

The script will:
- Skip lines with invalid format
- Warn about unknown symbols
- Warn about projects not found in the database
- Continue processing even if some lines fail

## Project References

Project names must match those in `backend/sql/01_insert_initial_projects.sql`. Current projects:
- Computer games
- YouTube
- Running
- Fast walking
- Films
- Podcasts
- Vibe coding
- Telegram channel
- Reading fiction
- Reading tech books
- Reading non-fiction
- English
- Diary
- Meatings
- Slow walking
- Growth sessions


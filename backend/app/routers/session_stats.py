from datetime import date
from enum import Enum
from typing import Annotated, Optional

import databases
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_db
from app.schemas import SessionStats, StatsSegment, StatsProjectDuration

router = APIRouter()

# Display order of projects within a stats segment; projects not listed come last (by id).
PROJECT_ID_ORDER: list[int] = [1, 2, 5, 6, 14, 9, 10, 11, 3, 4, 15, 7, 12, 8, 13, 16]

# Guard against requests that would generate an unreasonable number of segments.
MAX_SEGMENTS = 3700


class AggregationBy(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# Whitelisted SQL fragments (never built from user input).
_SEGMENT_STEP = {
    AggregationBy.DAY: "INTERVAL '1 day'",
    AggregationBy.WEEK: "INTERVAL '1 week'",
    AggregationBy.MONTH: "INTERVAL '1 month'",
}


def _first_segment_start_sql(aggregation_by: AggregationBy) -> str:
    if aggregation_by == AggregationBy.WEEK:
        # Postgres date_trunc('week') is Monday-based.
        return "date_trunc('week', CAST(:from_date AS date))::date"
    return "CAST(:from_date AS date)"


@router.get("/sessions/stats", response_model=SessionStats)
async def get_session_stats(
    db: Annotated[databases.Database, Depends(get_db)],
    from_date: date = Query(..., description="Start date (inclusive)"),
    to_date: date = Query(..., description="End date (exclusive)"),
    aggregation_by: AggregationBy = Query(AggregationBy.DAY),
    project_id: Optional[list[int]] = Query(None, description="Filter by one or more project IDs"),
):
    """Session durations summed per project within consecutive time segments.

    Segments are consecutive [start, end) ranges covering [from_date, to_date). For weekly
    aggregation the first segment starts on the Monday of the week containing from_date.
    Sessions are only counted if they fall inside [from_date, to_date). Empty segments are
    returned too.
    """
    if to_date <= from_date:
        raise HTTPException(status_code=400, detail="to_date must be after from_date")
    if (to_date - from_date).days > MAX_SEGMENTS * (1 if aggregation_by == AggregationBy.DAY else 28):
        raise HTTPException(status_code=400, detail="Date range is too large")

    params: dict = {
        "from_date": from_date,
        "to_date": to_date,
        "project_order": PROJECT_ID_ORDER,
    }
    project_filter_sql = ""
    if project_id:
        placeholders = ",".join(f":project_id_{i}" for i in range(len(project_id)))
        project_filter_sql = f"AND s.project_id IN ({placeholders})"
        for i, pid in enumerate(project_id):
            params[f"project_id_{i}"] = pid

    step = _SEGMENT_STEP[aggregation_by]
    query = f"""
        WITH segments AS (
            SELECT
                gs::date AS start_date,
                (gs + {step})::date AS end_date
            FROM generate_series(
                {_first_segment_start_sql(aggregation_by)},
                CAST(:to_date AS date) - 1,
                {step}
            ) AS gs
        )
        SELECT
            seg.start_date,
            seg.end_date,
            s.project_id,
            COALESCE(SUM(s.duration_minutes), 0)::int AS duration_minutes,
            COUNT(s.id)::int AS session_count,
            COALESCE(SUM(SUM(s.duration_minutes)) OVER (PARTITION BY seg.start_date), 0)::int
                AS segment_total_minutes,
            COALESCE(SUM(SUM(s.duration_minutes)) OVER (), 0)::int AS total_minutes,
            SUM(COUNT(s.id)) OVER ()::int AS total_session_count
        FROM segments seg
        LEFT JOIN sessions s
            ON s.date >= seg.start_date
           AND s.date < seg.end_date
           AND s.date >= :from_date
           AND s.date < :to_date
           {project_filter_sql}
        GROUP BY seg.start_date, seg.end_date, s.project_id
        ORDER BY
            seg.start_date,
            array_position(CAST(:project_order AS int[]), s.project_id) NULLS LAST,
            s.project_id
    """
    rows = await db.fetch_all(query, params)

    segments: list[StatsSegment] = []
    for row in rows:
        if not segments or segments[-1].start != row["start_date"]:
            segments.append(StatsSegment(
                start=row["start_date"],
                end=row["end_date"],
                total_minutes=row["segment_total_minutes"],
                projects=[],
            ))
        # A segment with no sessions yields a single row with NULL project_id.
        if row["project_id"] is not None:
            segments[-1].projects.append(StatsProjectDuration(
                project_id=row["project_id"],
                duration_minutes=row["duration_minutes"],
            ))

    first = rows[0] if rows else None
    return SessionStats(
        segments=segments,
        total_minutes=first["total_minutes"] if first else 0,
        session_count=first["total_session_count"] if first else 0,
    )

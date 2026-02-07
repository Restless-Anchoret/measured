#!/usr/bin/env python3
"""
Session Migration Script

Reads symbol-to-project mappings and session data, then generates SQL INSERT statements
for the sessions table.

Usage:
    python migrate_sessions.py

Input files (must be in the same directory):
    - symbol_mappings.txt: Symbol to project name mappings
    - sessions_data.txt: Session data with dates and durations

Output:
    - ../../../sql/02_migrate_sessions.sql: SQL INSERT statements
"""

import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string like '4ч45мин' and return total minutes.
    
    Args:
        duration_str: Duration in format like '4ч45мин', '1ч', '30мин'
        
    Returns:
        Total duration in minutes
    """
    hours = 0
    minutes = 0
    
    # Match hours: Xч
    hour_match = re.search(r'(\d+)ч', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))
    
    # Match minutes: Xмин
    minute_match = re.search(r'(\d+)мин', duration_str)
    if minute_match:
        minutes = int(minute_match.group(1))
    
    return hours * 60 + minutes


def parse_symbol_mappings(filepath: Path) -> Dict[str, str]:
    """
    Parse symbol mappings file.
    
    Format: SYMBOL - PROJECT_NAME
    Example: Ю - Computer games
    
    Returns:
        Dictionary mapping symbols to project names
    """
    mappings = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse format: SYMBOL - PROJECT_NAME
            parts = line.split(' - ', 1)
            if len(parts) != 2:
                print(f"Warning: Skipping invalid line {line_num}: {line}")
                continue
            
            symbol = parts[0].strip()
            project_name = parts[1].strip()
            mappings[symbol] = project_name
    
    return mappings


def load_project_ids_from_sql(sql_filepath: Path) -> Dict[str, int]:
    """
    Load project names from SQL file and assign IDs based on insertion order.
    
    The SQL file contains INSERT statements with project names.
    Project IDs start from 1 and increment based on order in the file.
    
    Returns:
        Dictionary mapping project names to IDs
    """
    project_ids = {}
    current_id = 1
    
    with open(sql_filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Find all project names in VALUES clauses
        # Match pattern: ('Project Name')
        matches = re.findall(r"\('([^']+)'\)", content)
        
        for project_name in matches:
            if project_name not in project_ids:
                project_ids[project_name] = current_id
                current_id += 1
    
    return project_ids


def parse_date(date_str: str) -> datetime:
    """
    Parse date string in DD.MM format and determine the year.
    
    Rules:
    - December (month 12) → 2025
    - January/February (months 1-2) → 2026
    
    Args:
        date_str: Date in DD.MM format
        
    Returns:
        datetime object at 00:00:00 UTC
    """
    day, month = map(int, date_str.split('.'))
    
    # Determine year based on month
    if month == 12:
        year = 2025
    elif month in [1, 2]:
        year = 2026
    else:
        # Default to 2025 for other months (shouldn't happen based on requirements)
        year = 2025
    
    return datetime(year, month, day, 0, 0, 0)


def parse_sessions_line(line: str, symbol_to_project_id: Dict[str, int]) -> Tuple[datetime, List[Tuple[int, int]]]:
    """
    Parse a single line from sessions data file.
    
    Format: DD.MM - SYMBOL1 DURATIONмин SYMBOL2 DURATIONч...
    Example: 14.12 - Ю 4ч45мин ЧХ 25мин ЧТ 15мин
    
    Returns:
        Tuple of (date, list of (project_id, duration_minutes))
    """
    # Split at first dash to separate date from sessions
    parts = line.split(' - ', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid line format: {line}")
    
    date_str = parts[0].strip()
    sessions_str = parts[1].strip()
    
    # Parse the date
    date = parse_date(date_str)
    
    # Parse session entries (symbol + duration pairs)
    sessions = []
    
    # Regex to match: SYMBOL DURATION where DURATION is like 4ч45мин, 1ч, 30мин
    pattern = r'(\S+)\s+(\d+(?:ч)?(?:\d+)?(?:мин)?)'
    matches = re.findall(pattern, sessions_str)
    
    for symbol, duration_str in matches:
        if symbol not in symbol_to_project_id:
            print(f"Warning: Unknown symbol '{symbol}' in line, skipping")
            continue
        
        project_id = symbol_to_project_id[symbol]
        duration_minutes = parse_duration(duration_str)
        
        if duration_minutes > 0:
            sessions.append((project_id, duration_minutes))
    
    return date, sessions


def calculate_session_timestamps(
    base_date: datetime,
    sessions: List[Tuple[int, int]],
    default_start_hour: int = 9
) -> List[Tuple[int, datetime, datetime]]:
    """
    Calculate start and end timestamps for sessions.
    
    Args:
        base_date: The date these sessions belong to
        sessions: List of (project_id, duration_minutes)
        default_start_hour: Default hour to start (9 = 9:00 UTC)
        
    Returns:
        List of (project_id, start_time, end_time)
    """
    if not sessions:
        return []
    
    # Calculate total duration
    total_minutes = sum(duration for _, duration in sessions)
    
    # If total duration exceeds 15 hours, adjust start time backwards
    if total_minutes > 15 * 60:
        # Calculate how much we need to shift back to end before midnight
        start_time = base_date.replace(hour=0, minute=0) + timedelta(hours=24) - timedelta(minutes=total_minutes)
    else:
        start_time = base_date.replace(hour=default_start_hour, minute=0)
    
    # Generate session timestamps
    result = []
    current_time = start_time
    
    for project_id, duration_minutes in sessions:
        end_time = current_time + timedelta(minutes=duration_minutes)
        result.append((project_id, current_time, end_time))
        current_time = end_time
    
    return result


def generate_sql(sessions: List[Tuple[int, datetime, datetime]], output_file: Path):
    """
    Generate SQL INSERT statements for sessions.
    
    Args:
        sessions: List of (project_id, start_time, end_time)
        output_file: Path to output SQL file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Migrated sessions data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Total sessions: {len(sessions)}\n")
        f.write("\n")
        
        for project_id, start_time, end_time in sessions:
            start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
            
            f.write(
                f"INSERT INTO sessions (project_id, start_time, end_time, created_at) "
                f"VALUES ({project_id}, '{start_str}', '{end_str}', CURRENT_TIMESTAMP);\n"
            )
        
        f.write("\n-- Migration complete\n")


def main():
    """Main migration script execution."""
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Define file paths
    symbol_mappings_file = script_dir / "symbol_mappings.txt"
    sessions_data_file = script_dir / "sessions_data.txt"
    sql_projects_file = script_dir / ".." / ".." / "sql" / "01_insert_initial_projects.sql"
    output_sql_file = script_dir / ".." / ".." / "sql" / "02_migrate_sessions.sql"
    
    # Normalize paths
    sql_projects_file = sql_projects_file.resolve()
    output_sql_file = output_sql_file.resolve()
    
    print("Session Migration Script")
    print("=" * 50)
    
    # Step 1: Load project IDs from SQL
    print(f"\n1. Loading project IDs from {sql_projects_file.name}...")
    project_name_to_id = load_project_ids_from_sql(sql_projects_file)
    print(f"   Loaded {len(project_name_to_id)} projects")
    
    # Step 2: Parse symbol mappings
    print(f"\n2. Parsing symbol mappings from {symbol_mappings_file.name}...")
    symbol_to_project_name = parse_symbol_mappings(symbol_mappings_file)
    print(f"   Loaded {len(symbol_to_project_name)} symbol mappings")
    
    # Step 3: Create symbol to project ID mapping
    print("\n3. Creating symbol to project ID mapping...")
    symbol_to_project_id = {}
    for symbol, project_name in symbol_to_project_name.items():
        if project_name in project_name_to_id:
            symbol_to_project_id[symbol] = project_name_to_id[project_name]
        else:
            print(f"   Warning: Project '{project_name}' not found in SQL file")
    print(f"   Mapped {len(symbol_to_project_id)} symbols to project IDs")
    
    # Step 4: Parse sessions data
    print(f"\n4. Parsing sessions from {sessions_data_file.name}...")
    all_sessions = []
    
    with open(sessions_data_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                base_date, sessions = parse_sessions_line(line, symbol_to_project_id)
                timestamped_sessions = calculate_session_timestamps(base_date, sessions)
                all_sessions.extend(timestamped_sessions)
                print(f"   Line {line_num}: {len(sessions)} sessions on {base_date.date()}")
            except Exception as e:
                print(f"   Error on line {line_num}: {e}")
                continue
    
    print(f"\n   Total sessions parsed: {len(all_sessions)}")
    
    # Step 5: Generate SQL
    print(f"\n5. Generating SQL file: {output_sql_file}...")
    generate_sql(all_sessions, output_sql_file)
    print(f"   SQL file generated successfully!")
    
    print("\n" + "=" * 50)
    print("Migration complete!")
    print(f"Output: {output_sql_file}")


if __name__ == "__main__":
    main()


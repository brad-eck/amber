"""Filesystem operations for Amber's on-disk log structure.

Directory layout:
    data/logs/YYYY/MM/YYYY-MM-DD/
        video.mp4
        transcript.txt
        transcript.json
        metadata.json
"""

from __future__ import annotations

import datetime
from pathlib import Path


def ensure_directories(data_path: Path) -> None:
    """Create the top-level data directories if they don't exist."""
    (data_path / "logs").mkdir(parents=True, exist_ok=True)
    (data_path / "summaries" / "weekly").mkdir(parents=True, exist_ok=True)
    (data_path / "summaries" / "monthly").mkdir(parents=True, exist_ok=True)
    (data_path / "summaries" / "yearly").mkdir(parents=True, exist_ok=True)


def entry_dir(data_path: Path, date: datetime.date) -> Path:
    """Return the directory path for a given date's entry.

    Example: data/logs/2026/03/2026-03-24/
    """
    return (
        data_path
        / "logs"
        / f"{date.year:04d}"
        / f"{date.month:02d}"
        / date.isoformat()
    )


def ensure_entry_dir(data_path: Path, date: datetime.date) -> Path:
    """Return the entry directory for a date, creating it if needed."""
    d = entry_dir(data_path, date)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_dates(data_path: Path) -> list[datetime.date]:
    """List all dates that have an entry directory on disk.

    Returns dates in chronological order.
    """
    logs_dir = data_path / "logs"
    if not logs_dir.exists():
        return []

    dates: list[datetime.date] = []
    for year_dir in sorted(logs_dir.iterdir()):
        if not year_dir.is_dir():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir():
                    continue
                try:
                    dates.append(datetime.date.fromisoformat(day_dir.name))
                except ValueError:
                    # Skip directories that don't match YYYY-MM-DD
                    continue
    return dates

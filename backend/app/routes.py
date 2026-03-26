"""API route handlers for Amber."""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from backend.app.models import get_db
from backend.app.storage import ensure_entry_dir
from backend.app.transcribe import process_entry

router = APIRouter(prefix="/entries", tags=["entries"])


def _parse_date(date_str: str) -> datetime.date:
    """Parse a YYYY-MM-DD string into a date, raising 400 on bad format."""
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str!r}. Expected YYYY-MM-DD.")


def _probe_duration(video_path: Path) -> float | None:
    """Use ffprobe to extract duration in seconds. Returns None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except (KeyError, json.JSONDecodeError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _write_metadata(
    entry_dir: Path,
    *,
    duration: float | None,
    file_size_bytes: int,
    original_filename: str,
    created_at: str,
) -> None:
    """Write the metadata.json sidecar file."""
    metadata = {
        "duration": duration,
        "file_size_bytes": file_size_bytes,
        "whisper_model": None,
        "original_filename": original_filename,
        "created_at": created_at,
    }
    (entry_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))


def _start_transcription(
    background_tasks: BackgroundTasks,
    request: Request,
    date: str,
) -> None:
    """Schedule transcription as a background task."""
    data_path: Path = request.app.state.data_path
    db_path: Path = request.app.state.db_path
    cfg = request.app.state.config

    background_tasks.add_task(
        process_entry,
        data_path=data_path,
        db_path=db_path,
        date=date,
        whisper_model=cfg.transcription.whisper_model,
        language=cfg.transcription.language,
    )


@router.post("/{date}/video", status_code=201)
async def upload_video(
    date: str,
    file: UploadFile,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Upload a video file for a given date.

    If an entry already exists for that date, it is replaced.
    Transcription is automatically kicked off in the background.
    """
    entry_date = _parse_date(date)
    data_path: Path = request.app.state.data_path
    db_path: Path = request.app.state.db_path

    day_dir = ensure_entry_dir(data_path, entry_date)
    video_path = day_dir / "video.mp4"

    # Stream the upload to disk
    content = await file.read()
    video_path.write_bytes(content)

    file_size = video_path.stat().st_size
    duration = _probe_duration(video_path)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Relative path from data_path for DB storage
    relative_video = video_path.relative_to(data_path)

    _write_metadata(
        day_dir,
        duration=duration,
        file_size_bytes=file_size,
        original_filename=file.filename or "unknown",
        created_at=now,
    )

    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO entries (date, video_path, duration_seconds, file_size_bytes,
                                 transcription_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                video_path = excluded.video_path,
                duration_seconds = excluded.duration_seconds,
                file_size_bytes = excluded.file_size_bytes,
                transcription_status = 'pending',
                transcript = NULL,
                whisper_model = NULL,
                updated_at = excluded.updated_at
            """,
            (
                entry_date.isoformat(),
                str(relative_video),
                duration,
                file_size,
                now,
                now,
            ),
        )

    # Kick off transcription in the background
    _start_transcription(background_tasks, request, entry_date.isoformat())

    return {
        "date": entry_date.isoformat(),
        "duration_seconds": duration,
        "file_size_bytes": file_size,
        "transcription_status": "pending",
    }


@router.post("/{date}/transcribe", status_code=202)
async def trigger_transcription(
    date: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Manually trigger transcription for an entry.

    Useful for retrying after a failure or re-transcribing with
    updated settings. Returns 202 Accepted immediately; transcription
    runs in the background.
    """
    entry_date = _parse_date(date)
    db_path: Path = request.app.state.db_path

    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT date, transcription_status FROM entries WHERE date = ?",
            (entry_date.isoformat(),),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No entry for {entry_date.isoformat()}")

    if row["transcription_status"] == "processing":
        raise HTTPException(
            status_code=409,
            detail="Transcription is already in progress for this entry.",
        )

    # Reset status to pending before kicking off
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db(db_path) as conn:
        conn.execute(
            "UPDATE entries SET transcription_status = 'pending', updated_at = ? WHERE date = ?",
            (now, entry_date.isoformat()),
        )

    _start_transcription(background_tasks, request, entry_date.isoformat())

    return {
        "date": entry_date.isoformat(),
        "transcription_status": "pending",
        "message": "Transcription started.",
    }


@router.get("")
async def list_entries(request: Request):
    """List all entries."""
    db_path: Path = request.app.state.db_path

    with get_db(db_path) as conn:
        rows = conn.execute(
            """
            SELECT date, transcription_status, duration_seconds, file_size_bytes
            FROM entries
            ORDER BY date DESC
            """
        ).fetchall()

    return [
        {
            "date": row["date"],
            "transcription_status": row["transcription_status"],
            "duration_seconds": row["duration_seconds"],
            "file_size_bytes": row["file_size_bytes"],
        }
        for row in rows
    ]


@router.get("/{date}")
async def get_entry(date: str, request: Request):
    """Get a single entry's metadata, including transcript if available."""
    entry_date = _parse_date(date)
    db_path: Path = request.app.state.db_path
    data_path: Path = request.app.state.data_path

    with get_db(db_path) as conn:
        row = conn.execute(
            """
            SELECT date, video_path, transcript, duration_seconds, file_size_bytes,
                   whisper_model, transcription_status, created_at, updated_at
            FROM entries
            WHERE date = ?
            """,
            (entry_date.isoformat(),),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No entry for {entry_date.isoformat()}")

    result = dict(row)

    # Include structured transcript data if the JSON sidecar exists
    entry_dir = (
        data_path / "logs"
        / f"{entry_date.year:04d}"
        / f"{entry_date.month:02d}"
        / entry_date.isoformat()
    )
    transcript_json_path = entry_dir / "transcript.json"
    if transcript_json_path.is_file():
        try:
            result["transcript_segments"] = json.loads(
                transcript_json_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            result["transcript_segments"] = None
    else:
        result["transcript_segments"] = None

    return result


@router.get("/{date}/video")
async def get_video(date: str, request: Request):
    """Serve the video file for a given date."""
    entry_date = _parse_date(date)
    data_path: Path = request.app.state.data_path
    db_path: Path = request.app.state.db_path

    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT video_path FROM entries WHERE date = ?",
            (entry_date.isoformat(),),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No entry for {entry_date.isoformat()}")

    video_path = data_path / row["video_path"]
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename="video.mp4",
    )

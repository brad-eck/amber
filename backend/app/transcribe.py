"""Transcription pipeline: FFmpeg audio extraction + faster-whisper.

Pipeline for a single entry:
    Video -> FFmpeg extracts audio (16kHz mono WAV)
    -> faster-whisper transcribes
    -> transcript.txt + transcript.json written to entry directory
    -> SQLite entries table + FTS index updated
    -> metadata.json updated with whisper model
    -> temp audio file deleted
"""

from __future__ import annotations

import datetime
import json
import logging
import subprocess
from pathlib import Path

from backend.app.models import get_db

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when the transcription pipeline encounters a fatal error."""


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract audio from a video file as 16kHz mono WAV using FFmpeg.

    Args:
        video_path: Path to the source video file.
        output_path: Where to write the extracted WAV file.

    Raises:
        TranscriptionError: If FFmpeg is not found or the extraction fails.
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",                  # no video
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",         # 16kHz sample rate
        "-ac", "1",             # mono
        "-y",                   # overwrite without prompting
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise TranscriptionError(
            "FFmpeg is not installed or not on PATH. "
            "Install it with: sudo apt install ffmpeg (Linux) or brew install ffmpeg (macOS)"
        )
    except subprocess.TimeoutExpired:
        raise TranscriptionError(
            f"FFmpeg timed out extracting audio from {video_path.name}"
        )

    if result.returncode != 0:
        stderr_tail = result.stderr[-500:] if result.stderr else "(no output)"
        raise TranscriptionError(
            f"FFmpeg failed (exit {result.returncode}): {stderr_tail}"
        )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise TranscriptionError(
            "FFmpeg completed but produced no audio output. "
            "The video may not contain an audio track."
        )


def transcribe_audio(
    audio_path: Path,
    model_name: str = "base",
    language: str = "en",
) -> list[dict]:
    """Transcribe an audio file using faster-whisper.

    Loads the model fresh each call to keep memory usage predictable.

    Args:
        audio_path: Path to a WAV audio file.
        model_name: Whisper model size (tiny, base, small, medium, large-v2).
        language: Language code for transcription.

    Returns:
        List of segment dicts, each containing:
            - start: float (seconds)
            - end: float (seconds)
            - text: str
            - words: list of {start, end, word} dicts (if available)

    Raises:
        TranscriptionError: If faster-whisper is not installed or transcription fails.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise TranscriptionError(
            "faster-whisper is not installed. "
            "Install it with: pip install faster-whisper"
        )

    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as exc:
        raise TranscriptionError(
            f"Failed to load Whisper model {model_name!r}: {exc}"
        )

    try:
        raw_segments, _info = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
        )

        segments = []
        for seg in raw_segments:
            segment_dict: dict = {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            }
            if seg.words:
                segment_dict["words"] = [
                    {
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "word": w.word.strip(),
                    }
                    for w in seg.words
                ]
            else:
                segment_dict["words"] = []

            segments.append(segment_dict)

        return segments

    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Transcription failed: {exc}")


def process_entry(
    data_path: Path,
    db_path: Path,
    date: str,
    whisper_model: str = "base",
    language: str = "en",
) -> None:
    """Run the full transcription pipeline for a single entry.

    This is designed to be called from a background task. It handles its own
    error reporting by updating the DB status on failure.

    Args:
        data_path: Root data directory (contains logs/).
        db_path: Path to amber.db.
        date: ISO-format date string (YYYY-MM-DD).
        whisper_model: Whisper model size to use.
        language: Language code for transcription.
    """
    parsed_date = datetime.date.fromisoformat(date)
    entry_dir = (
        data_path / "logs"
        / f"{parsed_date.year:04d}"
        / f"{parsed_date.month:02d}"
        / date
    )
    video_path = entry_dir / "video.mp4"
    audio_path = entry_dir / "audio_temp.wav"

    logger.info("Starting transcription for %s", date)

    # Mark as processing
    _update_status(db_path, date, "processing")

    try:
        if not video_path.is_file():
            raise TranscriptionError(f"Video file not found: {video_path}")

        # Step 1: Extract audio
        logger.info("Extracting audio from %s", video_path.name)
        extract_audio(video_path, audio_path)

        # Step 2: Transcribe
        logger.info("Running faster-whisper (model=%s, lang=%s)", whisper_model, language)
        segments = transcribe_audio(audio_path, whisper_model, language)

        # Step 3: Write transcript.txt
        plain_text = "\n".join(seg["text"] for seg in segments)
        (entry_dir / "transcript.txt").write_text(plain_text, encoding="utf-8")

        # Step 4: Write transcript.json
        (entry_dir / "transcript.json").write_text(
            json.dumps(segments, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Step 5: Update entries table
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_db(db_path) as conn:
            conn.execute(
                """
                UPDATE entries
                SET transcript = ?,
                    whisper_model = ?,
                    transcription_status = 'done',
                    updated_at = ?
                WHERE date = ?
                """,
                (plain_text, whisper_model, now, date),
            )

            # Step 6: Insert/replace into FTS index
            conn.execute(
                "DELETE FROM transcripts_fts WHERE date = ?",
                (date,),
            )
            conn.execute(
                "INSERT INTO transcripts_fts (date, content) VALUES (?, ?)",
                (date, plain_text),
            )

        # Step 7: Update metadata.json
        _update_metadata(entry_dir, whisper_model)

        logger.info("Transcription complete for %s (%d segments)", date, len(segments))

    except Exception as exc:
        logger.error("Transcription failed for %s: %s", date, exc)
        _update_status(db_path, date, "failed")
        raise

    finally:
        # Step 8/9: Always clean up the temp audio file
        if audio_path.is_file():
            audio_path.unlink()


def _update_status(db_path: Path, date: str, status: str) -> None:
    """Update the transcription_status for an entry."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with get_db(db_path) as conn:
            conn.execute(
                "UPDATE entries SET transcription_status = ?, updated_at = ? WHERE date = ?",
                (status, now, date),
            )
    except Exception:
        logger.exception("Failed to update transcription status to %r for %s", status, date)


def _update_metadata(entry_dir: Path, whisper_model: str) -> None:
    """Update metadata.json with the whisper model used for transcription."""
    metadata_path = entry_dir / "metadata.json"
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}
    else:
        metadata = {}

    metadata["whisper_model"] = whisper_model
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

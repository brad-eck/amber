# Amber

**Open source, self-hostable personal time capsule app.**

## Vision

People living 500+ years from now should be able to have a deep, rich understanding of what daily life was like today — not just historical events, but the texture of ordinary life. The name comes from organisms preserved in amber: ordinary things made extraordinary by time.

The creator's motivation: "I wish something like this existed 200 years ago so we could all have a better connection to our history."

## Core Concept

Daily video logs, similar to what astronauts do in space. Users get in front of a camera and record a 3-5 minute log of what took place that day. One entry per day (by design — reduces decision fatigue, mirrors the astronaut log format).

Over time, AI compresses these into hierarchical summaries: daily -> weekly -> monthly -> yearly. A future viewer could watch a year summary, drill into a month, then a week, then a single day.

## Architecture

- **Local-first, self-hostable.** User owns all data. Think Obsidian's model — we provide the tool, not the storage.
- **Filesystem is the source of truth.** SQLite is an index/cache that can be rebuilt from files.
- **Open source from day one.**

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Python + FastAPI | Best ecosystem for Whisper/AI, minimal boilerplate |
| Frontend | SvelteKit | Small bundles, simple reactivity, Tauri-ready later |
| Database | SQLite (FTS5) | Zero ops, full-text search across transcripts |
| Transcription | faster-whisper (local) | No API costs, no data leaving the machine |
| Video format | H.264/AAC in MP4 | Most universally playable format |
| Config | TOML | Human-readable |

No Docker, no Electron for v1. Clone, `pip install .`, install FFmpeg, run.

## On-Disk Structure

```
amber/                             # Project root (code + data live together)
  data/                            # User data directory (gitignored)
    config.toml
    amber.db                       # SQLite index (rebuildable from files)
    logs/
      2026/
        03/
          2026-03-24/
            video.mp4              # Raw recording
            transcript.txt         # Plain text transcription
            transcript.json        # Word-level timestamps for UI
            metadata.json          # Duration, file size, whisper model, etc.
    summaries/                     # v2: AI-generated hierarchical summaries
      weekly/
        2026-W13.md
      monthly/
        2026-03.md
      yearly/
        2026.md
```

## Transcription Pipeline

```
Video -> FFmpeg extracts audio (16kHz mono WAV) -> faster-whisper -> transcript.txt + transcript.json -> SQLite FTS index -> temp audio deleted
```

Default Whisper model: `base` (good accuracy, fast on CPU). Configurable to `small`/`medium`/`large`.

## SQLite Schema

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    video_path TEXT NOT NULL,
    transcript TEXT,                 -- plain text transcript (also in sidecar file)
    duration_seconds REAL,
    file_size_bytes INTEGER,
    whisper_model TEXT,
    transcription_status TEXT DEFAULT 'pending',  -- pending/processing/done/failed
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Standalone FTS table for full-text search across transcripts.
-- Manually kept in sync with entries table (insert/update/delete).
CREATE VIRTUAL TABLE transcripts_fts USING fts5(
    date,
    content
);

CREATE TABLE summaries (
    id INTEGER PRIMARY KEY,
    period_type TEXT NOT NULL,       -- weekly/monthly/yearly
    period_key TEXT NOT NULL,        -- 2026-W13, 2026-03, 2026
    content TEXT,
    source_entry_ids TEXT,           -- JSON array
    model_used TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(period_type, period_key)
);
```

## Config (config.toml)

```toml
[storage]
data_path = "./data"               # Relative to project root, or absolute path

[transcription]
whisper_model = "base"
language = "en"

[recording]
max_duration_seconds = 300
video_codec = "h264"
container = "mp4"

[server]
host = "127.0.0.1"
port = 8765
```

## MVP Implementation Plan

| Weekend | Milestone |
|---------|-----------|
| 1 | Project scaffolding, folder structure, config, SQLite schema |
| 2 | Video import endpoint, file serving, metadata writing |
| 3 | Transcription pipeline (FFmpeg + faster-whisper + background tasks) |
| 4 | SvelteKit frontend scaffolding, calendar view (read-only) |
| 5 | Video player + transcript display page |
| 6 | In-browser recording (MediaRecorder API) + upload |
| 7 | Full-text search across all transcripts |
| 8 | Polish, error handling, README, first GitHub release |

## v2 Roadmap

1. **AI compression** — weekly/monthly/yearly summaries from transcripts (user-provided API key)
2. **World news context** — headlines stored as `context.json` per day
3. **Tauri desktop wrapper**
4. **"On this day"** — surface a random past entry
5. **Export/backup tooling**

## Key Design Decisions

- **One entry per day** — deliberate constraint, not a limitation. Re-recording replaces that day's entry.
- **Plain text sidecars** — the archive is useful without the app. `transcript.txt` is readable by anything.
- **SQLite is a cache** — delete it and rebuild from the folder structure. Critical for longevity.
- **No desktop packaging for v1** — local web app (Python server + browser) gets 90% of the UX with 30% of the effort.
- **H.264/MP4** — most universally supported. WebM/VP9 is technically superior but less hardware-compatible.
- **Auto-transcription as a preservation hedge** — if the video format becomes unreadable in 100 years, the plain text transcript survives.

## Monetization (Low Priority)

Not the main goal. The mission comes first. Possible paths:
- Open source with optional paid managed hosting (most compatible with preservation mission)
- Non-profit/foundation model (best for 500-year thinking)
- Donations

## Durability Considerations

- Video codecs will die. Transcription to plain text is the long-term hedge.
- Storage costs: ~50-150MB per day at 720p webcam quality, ~18-55GB/year.
- Future: consider integration with institutional archives (Internet Archive, universities) for true long-term preservation.

## Project Structure (Planned)

```
amber/
  backend/
    app/
      main.py          # FastAPI entry point
      storage.py       # Filesystem operations
      transcribe.py    # FFmpeg + faster-whisper
      models.py        # SQLite schema + access
  frontend/
    src/
      routes/
        +page.svelte   # Main calendar view
  data/                # User data (gitignored)
  pyproject.toml
  README.md
```

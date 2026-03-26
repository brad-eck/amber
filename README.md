# Amber

**Open-source, self-hostable personal time capsule.**

Record a short daily video log. Amber transcribes it, indexes it, and preserves it -- building a searchable archive of your ordinary life that grows more valuable with every passing year.

---

## Why

We have better records of medieval kings than we do of our own great-grandparents. The texture of daily life -- what people worried about, laughed at, ate for dinner -- disappears within a generation.

Amber exists to change that. The name comes from tree resin: ordinary insects preserved in amber become extraordinary given enough time. A five-minute video about your Tuesday is mundane today. In fifty years it is a treasure. In five hundred years it is history.

The goal is not to build a social network or a content platform. It is to build a preservation tool that respects your ownership of your own history, runs on your own hardware, and stores data in formats that will outlive the software itself.

## What it does

- **Daily video logs** -- one entry per day, by design. Record 3-5 minutes about your day, like an astronaut log.
- **Automatic transcription** -- local speech-to-text via faster-whisper. No cloud services, no API costs.
- **Full-text search** -- SQLite FTS5 index across all transcripts.
- **Hierarchical summaries** (planned) -- AI-generated weekly, monthly, and yearly summaries. Drill from a year down to a single day.
- **Plain text sidecars** -- every transcript is saved as a `.txt` file alongside the video. The archive is useful without the app.

## Design principles

- **Local-first.** Your data lives on your machine. Amber provides the tool, not the storage.
- **Filesystem is the source of truth.** Videos, transcripts, and metadata are organized in dated directories. You can browse them with a file manager.
- **SQLite is a cache.** Delete the database and rebuild it from the folder structure. Nothing is lost.
- **Plain text for longevity.** Video codecs will die. Transcripts in `.txt` files are readable by anything, forever.
- **No packaging overhead.** No Docker, no Electron. A Python process and a browser.

## Tech stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python + FastAPI | Best ecosystem for Whisper/AI, minimal boilerplate |
| Frontend | SvelteKit | Small bundles, simple reactivity, Tauri-ready later |
| Database | SQLite with FTS5 | Zero ops, full-text search across transcripts |
| Transcription | faster-whisper (local) | No API costs, no data leaving the machine |
| Video format | H.264/AAC in MP4 | Most universally playable format |
| Config | TOML | Human-readable, easy to edit by hand |

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) (for video probing and audio extraction)

## Quick start

```
git clone https://github.com/brad-eck/amber.git
cd amber
pip install .
amber
```

The server starts at `http://127.0.0.1:8765`. A default `data/config.toml` is created on first run.

## Project status

Amber is in early development. This is an MVP.

**What works today:**
- Backend API server (FastAPI)
- Video upload for any date (POST, with re-recording/replacement support)
- Entry listing and retrieval
- Video file serving
- On-disk directory structure with metadata sidecars
- SQLite database with schema for entries, summaries, and full-text search
- TOML-based configuration with sensible defaults

**What is coming:**
- Transcription pipeline (FFmpeg audio extraction + faster-whisper)
- SvelteKit frontend with calendar view and video player
- Full-text search API
- In-browser recording
- AI-generated hierarchical summaries (weekly/monthly/yearly)

## On-disk data layout

```
data/
  config.toml
  amber.db                        # SQLite index (rebuildable)
  logs/
    2026/
      03/
        2026-03-24/
          video.mp4               # Raw recording
          transcript.txt          # Plain text transcription
          transcript.json         # Word-level timestamps
          metadata.json           # Duration, file size, etc.
  summaries/
    weekly/
      2026-W13.md
    monthly/
      2026-03.md
    yearly/
      2026.md
```

## API

All endpoints are prefixed with `/entries`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/entries` | List all entries (newest first) |
| `GET` | `/entries/{date}` | Get metadata for a single entry |
| `GET` | `/entries/{date}/video` | Stream the video file |
| `POST` | `/entries/{date}/video` | Upload or replace a video for a date |

Dates use `YYYY-MM-DD` format. The API returns JSON.

## Configuration

Amber reads `data/config.toml` on startup and creates it with defaults if missing.

```toml
[storage]
data_path = "./data"               # Relative to project root, or absolute

[transcription]
whisper_model = "base"             # base, small, medium, or large
language = "en"

[recording]
max_duration_seconds = 300
video_codec = "h264"
container = "mp4"

[server]
host = "127.0.0.1"
port = 8765
```

## License

[MIT](LICENSE)

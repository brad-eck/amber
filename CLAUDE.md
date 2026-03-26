# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and run

```bash
# Backend
pip install .          # install dependencies
amber                  # start the server (127.0.0.1:8765, auto-reload enabled)

# Frontend (separate terminal)
cd frontend
npm install
npm run dev            # SvelteKit dev server (default http://localhost:5173)
```

Requires Python 3.10+, FFmpeg/ffprobe on PATH, and Node.js 18+.

The frontend dev server proxies `/api` requests to the backend at `http://127.0.0.1:8765`.

## Architecture

Amber is a local-first personal time capsule. The filesystem is the source of truth; SQLite is a rebuildable cache/index.

**Data flow:** Video upload → save to `data/logs/YYYY/MM/YYYY-MM-DD/video.mp4` → write `metadata.json` sidecar → insert/upsert SQLite entry → background task: FFmpeg extracts 16kHz mono WAV → faster-whisper transcribes → write `transcript.txt` + `transcript.json` → update entries table + FTS5 index → delete temp audio.

**Module dependency graph:**
```
main.py ─── config.py        (loads TOML config, creates defaults on first run)
         ├── models.py       (SQLite schema init, get_db() context manager)
         ├── storage.py      (pathlib directory ops, entry path computation)
         └── routes.py       (API endpoints, uses BackgroundTasks for transcription)
                └── transcribe.py  (FFmpeg + faster-whisper pipeline)
```

**Key patterns:**
- App state: config, data_path, and db_path are set on `app.state` during lifespan and accessed via `request.app.state` in routes.
- DB access: always use `with get_db(db_path) as conn:` — auto-commits on success, rolls back on exception.
- FTS5 sync: the `transcripts_fts` virtual table is manually synced (delete + insert) when transcript content changes. It is not an external content table.
- Transcription status lifecycle: `pending` → `processing` → `done` | `failed`.
- All timestamps are UTC ISO format. Date keys are `YYYY-MM-DD` strings.
- Paths in the DB are stored relative to data_path for portability.
- faster-whisper is lazy-imported in transcribe.py so the app starts without it installed.

## API endpoints

All API routes are prefixed with `/api`. The frontend proxies `/api` to the backend in dev mode.

```
GET  /api/health
GET  /api/entries
GET  /api/entries/{date}
GET  /api/entries/{date}/video
POST /api/entries/{date}/video        (file upload, triggers background transcription)
POST /api/entries/{date}/transcribe   (manual retry/re-transcribe)
```

## On-disk data layout

```
data/                              # gitignored, auto-created on first run
  config.toml
  amber.db
  logs/YYYY/MM/YYYY-MM-DD/
    video.mp4, transcript.txt, transcript.json, metadata.json
  summaries/{weekly,monthly,yearly}/
```

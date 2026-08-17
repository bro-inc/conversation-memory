# conversation-memory

Always-on ambient mic transcription with automatic speaker recognition — no manual enrollment.
The first time a voice gives enough clean audio in one session, it's embedded and stored
permanently; every later run matches new voices against that store, tagging transcripts with a
stable (anonymous) speaker id across restarts.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env   # add your DEEPGRAM_API_KEY
python daemon.py
```

First run downloads the SpeechBrain ECAPA-TDNN model (~80MB) to `models/`.

## Inspect the log

```bash
python query.py [n]   # last n transcript segments (default 50), tagged with voiceprint ids
```

## Desktop UI

```bash
python desktop_app.py
```

Opens a native window (via `pywebview`) — no browser tab, just an app window you can leave up.
Same UI as below, just not stuck inside Chrome. Run alongside `daemon.py`.

## Web UI (browser instead of the native window)

```bash
python web_ui.py   # http://localhost:8765
```

Run alongside `daemon.py` (reads the same SQLite file, refreshes every 4s). Shows transcript
segments grouped by hour; click an hour to expand it, click "summarize" to generate a fast
DeepSeek summary for that hour (cached — re-summarize to regenerate). Needs `DEEPSEEK_API_KEY`
in `.env` for the summarize button; browsing transcripts works without it.

See `project.md` for design notes and known v1 limitations.

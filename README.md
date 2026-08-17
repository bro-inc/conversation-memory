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

See `project.md` for design notes and known v1 limitations.

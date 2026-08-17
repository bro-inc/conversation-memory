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

## Run automatically at login (survives closing the laptop / logging back in)

```bash
./scripts/install_launchagent.sh            # daemon only
./scripts/install_launchagent.sh --with-ui  # daemon + desktop window, both at login
```

Installs a macOS LaunchAgent: `daemon.py` starts at login and auto-restarts if it ever
crashes (`launchctl kickstart -k gui/$(id -u)/com.broinc.conversation-memory.daemon` to force
a restart). Logs go to `~/Library/Logs/conversation-memory/`. Undo with
`./scripts/uninstall_launchagent.sh`.

Two things this does **not** cover, worth knowing:
- **Mic permission for a headless launch**: the first time launchd (not you, from a Terminal)
  opens the mic, macOS may silently deny it instead of prompting. If the log shows no
  transcript activity, grant Microphone access to `.venv/bin/python3` in System Settings →
  Privacy & Security → Microphone, then kickstart it.
- **Sleep/wake**: the process itself survives the lid closing (it's just paused, not killed),
  but the CoreAudio input stream and the Deepgram websocket can go stale across a sleep/wake
  cycle without daemon.py noticing and reconnecting — there's no wake-detection/reconnect
  logic yet. If transcripts stop after a sleep cycle, `launchctl kickstart -k ...` is the
  manual fix for now.

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

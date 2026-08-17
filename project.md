# Project: Conversation Memory

## Overview
An always-on background daemon that listens to your Mac's microphone, transcribes speech live via
Deepgram Nova-3 (with diarization), and automatically recognizes recurring voices across sessions —
no manual enrollment step. The first time a voice accumulates enough audio in a session, it's
embedded and stored as a permanent voiceprint; every later session matches new diarized speakers
against that store, so "who was talking" persists across restarts without ever asking the user to
label anyone. Modeled on how BasedHardware/Omi's desktop app does speech profiles and speaker ID
(github.com/BasedHardware/omi, `backend/routers/listen/speakers.py` and `backend/utils/stt/`).

## Tech Stack
- **Python** — background daemon, matches the rest of the personal-project fleet (voice-butler,
  screen-memory)
- **Deepgram Nova-3** (streaming API) — live transcription + diarization (anonymous per-session
  speaker IDs)
- **SpeechBrain ECAPA-TDNN** (or pyannote/embedding) — local, self-hosted speaker-embedding model;
  runs on CPU for short clips, no external embedding service needed
- **sounddevice** — mic capture
- **SQLite** — voiceprint store (persistent speaker embeddings) + transcript log

## Architecture
```
Mic (sounddevice) → Deepgram Nova-3 streaming WS (diarized transcript segments)
                          │
                          ├─ per diarized speaker_id, accumulate audio in a rolling buffer
                          │
                          ▼
                  enough audio accumulated? ──no──▶ keep buffering
                          │ yes
                          ▼
              extract speaker embedding (local ECAPA-TDNN)
                          │
                          ▼
          cosine-match against stored voiceprints (SQLite)
                          │
              ┌───────────┴───────────┐
           match found            no match
              │                       │
      tag segment with          store as new permanent
      existing voiceprint_id    voiceprint immediately
              │                       │
              └───────────┬───────────┘
                           ▼
              transcript log (SQLite), segment tagged
              with stable voiceprint_id across sessions
```

Auto-enroll policy: single-session threshold (no cross-session confirmation) — mirrors Omi's
default. A voice is promoted to a permanent voiceprint as soon as one session gives enough clean
audio for a reliable embedding; exact duration/quality thresholds (min words, dominant-speaker
ratio, VAD gating) to be tuned against Omi's reference values in `backend/utils/speaker_sample.py`
and `backend/utils/stt/speaker_embedding.py`.

No naming/identity UI in v1 — voiceprints are anonymous stable IDs (`speaker_001`, `speaker_002`,
...). Naming them is a later layer, not part of this project's "done."

Scope boundary: mic audio only (no system audio capture), no LLM summarization/action-item
extraction — that's `screen-memory`'s job, not this project's.

## Key Files
- `daemon.py` — main loop: mic capture → Deepgram → per-speaker accumulation → resolution → log
- `deepgram_stream.py` — Nova-3 live connection, groups diarized words into utterance segments
- `audio_ring_buffer.py` — rolling wall-clock-indexed PCM buffer (30s), lets us recover a given
  speaker's actual audio after the fact for embedding
- `embedding.py` — local SpeechBrain ECAPA-TDNN speaker embedding extraction
- `speaker_matcher.py` — cosine-distance match against stored voiceprints, or enroll new
- `db.py` — SQLite: `voiceprints` (persistent, anonymous) + `segments` (transcript log)
- `query.py` — CLI to read back the transcript log
- `web_ui.py` + `static/index.html` — local FastAPI test UI: transcripts grouped by hour,
  live-refreshing, with an on-demand DeepSeek summary per hour (cached in `summaries` table)
- `summarizer.py` — DeepSeek (OpenAI-compatible) client for per-hour summaries

## Known v1 limitations
- Single mic channel: interleaved speakers' audio spans are extracted separately using
  Deepgram's per-word time ranges, but ring-buffer wall-clock alignment is an approximation
  (assumes near-real-time processing lag) — worth revisiting if resolution accuracy suffers.
- `MATCH_THRESHOLD = 0.45` is copied from Omi's pyannote-calibrated value as a starting point,
  not validated against SpeechBrain ECAPA-TDNN — needs real tuning.
- No cleanup/merge path yet for a voiceprint that got split into two (e.g. enrolled once from a
  noisy clip, again later cleanly) — voiceprints only ever get created, never merged.

## How to Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.template .env   # add DEEPGRAM_API_KEY
python daemon.py
python query.py         # inspect the transcript log
```

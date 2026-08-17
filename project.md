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
_To be filled in as we build._

## How to Run
_To be filled in as we build._

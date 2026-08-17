"""Always-on ambient listener.

Mic -> Deepgram Nova-3 (diarized, streaming) -> per-session-speaker audio accumulates in a
ring buffer -> once a session-local speaker has enough audio, extract a voiceprint and
match/enroll it against the persistent store -> transcript log tagged with a stable
voiceprint id that survives restarts.

Run: python daemon.py
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import sounddevice as sd
from dotenv import load_dotenv

import db
import deepgram_stream
import embedding
import speaker_matcher
from audio_ring_buffer import AudioRingBuffer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("daemon")

SAMPLE_RATE = deepgram_stream.SAMPLE_RATE
MIC_BLOCKSIZE = 1600  # samples/callback = 100ms at 16kHz
RING_BUFFER_SECONDS = 30.0
MIN_SPEAKER_AUDIO_SECONDS = 6.0  # accumulate this much of a speaker before trying to identify them
MAX_EMBEDDING_AUDIO_SECONDS = 10.0  # cap how much audio we embed at once (mirrors Omi)


@dataclass
class SpeakerState:
    """Per-session, per-diarized-speaker bookkeeping."""

    spans: List[Tuple[float, float]] = field(default_factory=list)  # wall-clock (start, end)
    duration: float = 0.0
    voiceprint_id: Optional[int] = None
    resolving: bool = False


async def run() -> None:
    db.init_db()
    session_id = str(uuid.uuid4())
    ring_buffer = AudioRingBuffer(RING_BUFFER_SECONDS, SAMPLE_RATE)
    speakers: Dict[int, SpeakerState] = {}
    audio_queue: "asyncio.Queue[bytes]" = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def mic_callback(indata, frames, time_info, status):
        if status:
            logger.warning("Mic status: %s", status)
        loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

    async def on_segments(segments: List[dict]) -> None:
        # Deepgram's word timestamps are relative to stream start, not wall-clock, and we
        # don't track that offset — segments arrive close to real-time (is_final, no
        # interim results), so "now" is a reasonable stand-in for their wall-clock span.
        # This is an approximation worth revisiting if resolution accuracy turns out to
        # suffer from processing lag.
        now = time.time()
        for segment in segments:
            speaker_id = segment["speaker"]
            state = speakers.setdefault(speaker_id, SpeakerState())

            seg_duration = segment["end"] - segment["start"]
            seg_start, seg_end = now - seg_duration, now
            state.spans.append((seg_start, seg_end))
            state.duration += seg_duration

            db.insert_segment(
                session_id, speaker_id, state.voiceprint_id, segment["text"], segment["start"], segment["end"]
            )
            logger.info(
                "[speaker %s%s] %s",
                speaker_id,
                f" -> voiceprint {state.voiceprint_id}" if state.voiceprint_id else "",
                segment["text"],
            )

            if state.voiceprint_id is None and not state.resolving and state.duration >= MIN_SPEAKER_AUDIO_SECONDS:
                state.resolving = True
                asyncio.create_task(_resolve_speaker(session_id, speaker_id, state, ring_buffer))

    connection = await deepgram_stream.connect(on_segments)

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE, blocksize=MIC_BLOCKSIZE, dtype="int16", channels=1, callback=mic_callback
    )
    logger.info("Listening... (session %s)", session_id)
    with stream:
        try:
            while True:
                pcm = await audio_queue.get()
                ring_buffer.write(pcm, time.time())
                await connection.send(pcm)
        except asyncio.CancelledError:
            pass
        finally:
            await connection.finish()


async def _resolve_speaker(
    session_id: str, speaker_id: int, state: SpeakerState, ring_buffer: AudioRingBuffer
) -> None:
    """Pull this speaker's own audio spans out of the ring buffer, embed, match/enroll."""
    try:
        clip = bytearray()
        total = 0.0
        for start, end in reversed(state.spans[-20:]):
            if total >= MAX_EMBEDDING_AUDIO_SECONDS:
                break
            clip[0:0] = ring_buffer.extract(start, end)
            total += end - start

        if not clip:
            logger.warning("Speaker %s: no audio recovered from ring buffer, skipping", speaker_id)
            return

        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(None, embedding.extract_embedding, bytes(clip), SAMPLE_RATE)
        voiceprint_id, is_new = await loop.run_in_executor(None, speaker_matcher.match_or_enroll, vector)

        state.voiceprint_id = voiceprint_id
        db.backfill_voiceprint(session_id, speaker_id, voiceprint_id)
        logger.info(
            "Speaker %s resolved -> voiceprint %s (%s)",
            speaker_id,
            voiceprint_id,
            "new" if is_new else "recognized",
        )
    except Exception:
        logger.exception("Speaker resolution failed for speaker=%s", speaker_id)
    finally:
        state.resolving = False


if __name__ == "__main__":
    asyncio.run(run())

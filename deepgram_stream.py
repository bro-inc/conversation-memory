"""Deepgram Nova-3 live streaming: diarized transcript segments.

Groups Deepgram's per-word speaker tags into utterance-level segments (consecutive words
from the same session-local speaker id) and hands them to a callback as they finalize.
"""
import logging
import os
from typing import Awaitable, Callable, List

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
)

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000

SegmentCallback = Callable[[List[dict]], Awaitable[None]]


async def connect(on_segments: SegmentCallback):
    """Open a Nova-3 live connection with diarization enabled.

    Caller sends audio via `await connection.send(pcm_bytes)` and tears down with
    `await connection.finish()`.
    """
    api_key = os.environ["DEEPGRAM_API_KEY"]
    client = DeepgramClient(api_key, DeepgramClientOptions(options={"keepalive": "true"}))
    connection = client.listen.asyncwebsocket.v("1")

    async def on_transcript(self, result, **kwargs):
        if not result.is_final:
            return
        words = result.channel.alternatives[0].words
        if not words:
            return
        segments = _group_by_speaker(words)
        if segments:
            await on_segments(segments)

    async def on_error(self, error, **kwargs):
        logger.error("Deepgram error: %s", error)

    connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-3",
        language="en-US",
        smart_format=True,
        punctuate=True,
        encoding="linear16",
        sample_rate=SAMPLE_RATE,
        channels=1,
        diarize=True,
        interim_results=False,
    )
    started = await connection.start(options)
    if not started:
        raise RuntimeError("Failed to connect to Deepgram")
    return connection


def _group_by_speaker(words: List) -> List[dict]:
    """Group consecutive words tagged with the same diarized speaker into one segment each."""
    segments: List[dict] = []
    current = None
    for word in words:
        speaker = getattr(word, "speaker", 0)
        text = getattr(word, "punctuated_word", None) or word.word
        if current is None or current["speaker"] != speaker:
            if current is not None:
                segments.append(current)
            current = {"speaker": speaker, "start": word.start, "end": word.end, "words": [text]}
        else:
            current["words"].append(text)
            current["end"] = word.end
    if current is not None:
        segments.append(current)
    for segment in segments:
        segment["text"] = " ".join(segment.pop("words"))
    return segments

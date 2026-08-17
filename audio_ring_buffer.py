"""Rolling buffer of raw mono PCM16 audio, indexed by wall-clock time.

We only learn which time range belongs to which speaker after Deepgram's diarized transcript
comes back — by which point the mic has moved on. This buffer lets us go back and pull "the
audio between these two timestamps" after the fact, which is what speaker-embedding extraction
needs (a real audio clip, not just text).
"""
import threading
from collections import deque
from typing import Deque, Tuple

BYTES_PER_SAMPLE = 2  # int16


class AudioRingBuffer:
    def __init__(self, max_duration_seconds: float, sample_rate: int):
        self.sample_rate = sample_rate
        self.bytes_per_second = sample_rate * BYTES_PER_SAMPLE
        self.max_bytes = int(max_duration_seconds * self.bytes_per_second)
        self._chunks: Deque[Tuple[float, bytes]] = deque()
        self._total_bytes = 0
        self._lock = threading.Lock()

    def write(self, pcm: bytes, timestamp: float) -> None:
        with self._lock:
            self._chunks.append((timestamp, pcm))
            self._total_bytes += len(pcm)
            while self._total_bytes > self.max_bytes and len(self._chunks) > 1:
                _, old = self._chunks.popleft()
                self._total_bytes -= len(old)

    def extract(self, start_time: float, end_time: float) -> bytes:
        """Concatenate every buffered chunk that overlaps [start_time, end_time].

        Chunk-granularity only (no intra-chunk trimming) — fine given mic chunks are
        ~100ms, well under the timing precision this needs.
        """
        with self._lock:
            out = bytearray()
            for ts, pcm in self._chunks:
                chunk_end = ts + len(pcm) / self.bytes_per_second
                if chunk_end < start_time or ts > end_time:
                    continue
                out.extend(pcm)
            return bytes(out)

"""SQLite store: persistent voiceprints + the transcript log.

Two tables:
- voiceprints: one row per recognized voice, forever. Anonymous — no name field by design (v1).
- segments: one row per diarized transcript utterance, tagged with a voiceprint_id once its
  speaker has been resolved (may be NULL for a bit right after a new session-local speaker
  first appears, until enough audio accumulates to embed and match them).
"""
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

DB_PATH = Path(__file__).parent / "conversation_memory.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS voiceprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            embedding BLOB NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            session_speaker_id INTEGER NOT NULL,
            voiceprint_id INTEGER,
            text TEXT NOT NULL,
            start REAL NOT NULL,
            end REAL NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (voiceprint_id) REFERENCES voiceprints (id)
        );
        CREATE INDEX IF NOT EXISTS idx_segments_session ON segments (session_id, session_speaker_id);
        """
    )
    conn.commit()
    conn.close()


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    return embedding.astype(np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


def get_all_voiceprints() -> List[Tuple[int, np.ndarray]]:
    conn = _connect()
    rows = conn.execute("SELECT id, embedding FROM voiceprints").fetchall()
    conn.close()
    return [(row[0], bytes_to_embedding(row[1])) for row in rows]


def create_voiceprint(embedding: np.ndarray) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO voiceprints (embedding, created_at) VALUES (?, ?)",
        (embedding_to_bytes(embedding), time.time()),
    )
    conn.commit()
    voiceprint_id = cur.lastrowid
    conn.close()
    return voiceprint_id


def insert_segment(
    session_id: str,
    session_speaker_id: int,
    voiceprint_id: Optional[int],
    text: str,
    start: float,
    end: float,
) -> int:
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO segments
           (session_id, session_speaker_id, voiceprint_id, text, start, end, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, session_speaker_id, voiceprint_id, text, start, end, time.time()),
    )
    conn.commit()
    segment_id = cur.lastrowid
    conn.close()
    return segment_id


def backfill_voiceprint(session_id: str, session_speaker_id: int, voiceprint_id: int) -> None:
    """Once a session-local speaker resolves to a voiceprint, retroactively tag every
    segment already logged for them this session — they were talking before we had
    enough audio to identify them."""
    conn = _connect()
    conn.execute(
        """UPDATE segments SET voiceprint_id = ?
           WHERE session_id = ? AND session_speaker_id = ? AND voiceprint_id IS NULL""",
        (voiceprint_id, session_id, session_speaker_id),
    )
    conn.commit()
    conn.close()

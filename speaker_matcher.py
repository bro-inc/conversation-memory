"""Match a speaker-cluster's embedding against stored voiceprints, or enroll a new one.

Mirrors Omi's backend/utils/stt/speaker_embedding.py: cosine distance against every stored
voiceprint, single threshold, no cross-session confirmation — the first voice that gives us
enough clean audio in one session gets auto-enrolled immediately, per user's call.
"""
import logging
from typing import Optional, Tuple

import numpy as np
from scipy.spatial.distance import cdist

import db

logger = logging.getLogger(__name__)

# Starting point copied from Omi (calibrated to their pyannote embedding on VoxCeleb1,
# 2.8% EER). We're using a different embedding model (SpeechBrain ECAPA-TDNN) — this is
# a placeholder, not a validated threshold. Tune against real enrollment/false-match data.
MATCH_THRESHOLD = 0.45


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(cdist(a.reshape(1, -1), b.reshape(1, -1), metric="cosine")[0, 0])


def match_or_enroll(embedding: np.ndarray) -> Tuple[int, bool]:
    """Returns (voiceprint_id, is_new)."""
    best_id: Optional[int] = None
    best_distance = float("inf")
    for voiceprint_id, stored in db.get_all_voiceprints():
        distance = _cosine_distance(embedding, stored)
        if distance < best_distance:
            best_id, best_distance = voiceprint_id, distance

    if best_id is not None and best_distance < MATCH_THRESHOLD:
        logger.info("Matched existing voiceprint=%s distance=%.3f", best_id, best_distance)
        return best_id, False

    voiceprint_id = db.create_voiceprint(embedding)
    logger.info(
        "No match (best_distance=%.3f) — enrolled new voiceprint=%s",
        best_distance if best_id is not None else -1.0,
        voiceprint_id,
    )
    return voiceprint_id, True

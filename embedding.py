"""Local speaker-embedding extraction via SpeechBrain's ECAPA-TDNN.

Self-hosted equivalent of Omi's HOSTED_SPEAKER_EMBEDDING_API_URL — runs on CPU for short
clips, no external service to stand up. Returns a 192-dim voiceprint per audio clip.

Model loads lazily (and downloads ~80MB on first use) so importing this module is cheap.
"""
from pathlib import Path

import numpy as np

_classifier = None

MODEL_DIR = Path(__file__).parent / "models" / "spkrec-ecapa-voxceleb"


def _get_classifier():
    global _classifier
    if _classifier is None:
        from speechbrain.inference.speaker import EncoderClassifier

        _classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(MODEL_DIR),
        )
    return _classifier


def extract_embedding(pcm16_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """Mono PCM16 little-endian bytes -> (192,) float32 embedding."""
    import torch

    if sample_rate != 16000:
        raise ValueError(f"expected 16kHz audio, got {sample_rate}")

    classifier = _get_classifier()
    samples = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    signal = torch.from_numpy(samples).unsqueeze(0)
    with torch.no_grad():
        vector = classifier.encode_batch(signal)
    return vector.squeeze().cpu().numpy().astype(np.float32)

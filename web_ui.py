"""Local web UI for testing the daemon: transcripts grouped per hour, with on-demand
per-hour summaries. Runs alongside daemon.py (reads the same SQLite file) — this process
never writes segments, only summaries.

Run: python web_ui.py   then open http://localhost:8765
"""
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
import summarizer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("web_ui")

app = FastAPI()
db.init_db()


def _label(voiceprint_id, session_speaker_id) -> str:
    return f"Voice {voiceprint_id}" if voiceprint_id else f"Unresolved speaker {session_speaker_id}"


@app.get("/api/hours")
def api_hours():
    buckets = db.get_hour_buckets()
    for bucket in buckets:
        bucket["has_summary"] = db.get_summary(bucket["hour_key"]) is not None
    return buckets


@app.get("/api/hours/{hour_key}/segments")
def api_segments(hour_key: str):
    segments = db.get_segments_for_hour(hour_key)
    for segment in segments:
        segment["label"] = _label(segment["voiceprint_id"], segment["session_speaker_id"])
    return segments


@app.get("/api/hours/{hour_key}/summary")
def api_get_summary(hour_key: str):
    return {"summary": db.get_summary(hour_key)}


@app.post("/api/hours/{hour_key}/summary")
def api_generate_summary(hour_key: str):
    segments = db.get_segments_for_hour(hour_key)
    if not segments:
        raise HTTPException(status_code=404, detail="No transcript for this hour")

    lines = [f"{_label(s['voiceprint_id'], s['session_speaker_id'])}: {s['text']}" for s in segments]
    transcript_text = "\n".join(lines)

    try:
        summary = summarizer.summarize(transcript_text)
    except Exception as error:
        logger.exception("Summarization failed for hour=%s", hour_key)
        raise HTTPException(status_code=502, detail=f"Summarization failed: {error}") from error

    db.save_summary(hour_key, summary)
    return {"summary": summary}


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)

"""Quick CLI to inspect the transcript log.

Usage: python query.py [n]   (default n=50, most recent segments)
"""
import sys

import db


def main() -> None:
    db.init_db()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    conn = db._connect()
    rows = conn.execute(
        "SELECT created_at, voiceprint_id, session_speaker_id, text FROM segments ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    for created_at, voiceprint_id, session_speaker_id, text in reversed(rows):
        label = f"voiceprint {voiceprint_id}" if voiceprint_id else f"speaker {session_speaker_id} (unresolved)"
        print(f"[{label}] {text}")


if __name__ == "__main__":
    main()

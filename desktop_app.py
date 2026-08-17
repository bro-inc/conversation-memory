"""Native desktop window wrapping the web UI — no browser tab, no chrome/tabs, just a window.

Runs the FastAPI server (web_ui.py) in a background thread and opens it in a pywebview
window pointed at localhost. Same backend, same static/index.html — this is purely a
presentation wrapper.

Run: python desktop_app.py
"""
import logging
import threading

import uvicorn
import webview
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("desktop_app")

HOST = "127.0.0.1"
PORT = 8765


def _run_server() -> None:
    import web_ui  # imported here so its module-level db.init_db() runs in this thread's context

    uvicorn.run(web_ui.app, host=HOST, port=PORT, log_level="warning")


def main() -> None:
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    logger.info("Opening desktop window on http://%s:%s", HOST, PORT)
    webview.create_window("conversation-memory", f"http://{HOST}:{PORT}", width=520, height=760, min_size=(380, 480))
    webview.start()


if __name__ == "__main__":
    main()

from __future__ import annotations

import socket
import sys
import threading
import time

import uvicorn
import webview

from backend.server import app, manager
from backend.runtime import require_ffmpeg


HOST = "127.0.0.1"
PORT = 8765


def run_server(server: uvicorn.Server) -> None:
    server.run()


def wait_until_ready(timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.25):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("El servidor local no pudo iniciarse.")


def main() -> None:
    try:
        ffmpeg = require_ffmpeg()
    except RuntimeError as exc:
        if "--check-ffmpeg" in sys.argv:
            raise SystemExit(2) from exc
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(exc), "YouTube Video Downloader", 0x10)
        raise SystemExit(2) from exc
    if "--check-ffmpeg" in sys.argv:
        raise SystemExit(0 if ffmpeg.is_file() else 2)

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    thread.start()
    wait_until_ready()
    webview.create_window(
        "YouTube Video Downloader",
        f"http://{HOST}:{PORT}",
        width=1040,
        height=790,
        min_size=(760, 620),
        background_color="#0b0d12",
    )
    try:
        webview.start()
    finally:
        manager.cancel_all()
        server.should_exit = True
        thread.join(timeout=3)


if __name__ == "__main__":
    main()

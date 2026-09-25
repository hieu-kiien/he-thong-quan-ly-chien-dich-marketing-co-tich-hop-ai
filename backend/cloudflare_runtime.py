"""Small private control server for bootstrapping and snapshotting the SQLite API."""

import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path("/app/data/marketing_campaigns.db")
MAX_DATABASE_BYTES = 64 * 1024 * 1024
api_process = None
api_ready = threading.Event()
api_lock = threading.Lock()


def start_api(restore_bytes):
    global api_process
    with api_lock:
        if api_process is not None and api_process.poll() is None:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if restore_bytes:
            if not restore_bytes.startswith(b"SQLite format 3\x00"):
                raise ValueError("Bản sao database không đúng định dạng SQLite")
            if len(restore_bytes) > MAX_DATABASE_BYTES:
                raise ValueError("Bản sao database vượt quá giới hạn 64 MiB")
            temporary_path = DB_PATH.with_suffix(".restore")
            temporary_path.write_bytes(restore_bytes)
            os.replace(temporary_path, DB_PATH)
        elif not DB_PATH.exists():
            subprocess.run(
                [sys.executable, "seed/seed_data.py"],
                cwd=APP_DIR,
                check=True,
            )

        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=APP_DIR,
        )

    for _ in range(120):
        if api_process.poll() is not None:
            raise RuntimeError("FastAPI đã dừng trong lúc khởi động")
        try:
            with urlopen("http://127.0.0.1:8000/health", timeout=1) as response:
                if response.status == 200:
                    api_ready.set()
                    return
        except (OSError, URLError):
            time.sleep(0.25)

    raise TimeoutError("FastAPI không sẵn sàng sau 30 giây")


def make_snapshot():
    if not api_ready.is_set():
        raise RuntimeError("FastAPI chưa được khởi tạo")

    file_descriptor, temporary_name = tempfile.mkstemp(prefix="marketflow-", suffix=".sqlite", dir=DB_PATH.parent)
    os.close(file_descriptor)
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as source:
            with sqlite3.connect(temporary_name) as destination:
                source.backup(destination)
        snapshot = Path(temporary_name).read_bytes()
        if len(snapshot) > MAX_DATABASE_BYTES:
            raise ValueError("Database snapshot exceeds 64 MiB")
        return snapshot
    finally:
        Path(temporary_name).unlink(missing_ok=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format_string, *args):
        print(f"[runtime] {format_string % args}", flush=True)

    def send_bytes(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self.send_bytes(200, b"pong", "text/plain")
            return
        if self.path == "/snapshot":
            try:
                self.send_bytes(200, make_snapshot(), "application/vnd.sqlite3")
            except Exception:
                print("[runtime] Could not create database snapshot", flush=True)
                self.send_bytes(503, b'{"detail":"Database snapshot unavailable"}')
            return
        self.send_bytes(404, b'{"detail":"Not found"}')

    def do_POST(self):
        if self.path != "/bootstrap":
            self.send_bytes(404, b'{"detail":"Not found"}')
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > MAX_DATABASE_BYTES:
            self.send_bytes(413, b'{"detail":"Database snapshot exceeds 64 MiB"}')
            return
        restore_bytes = self.rfile.read(content_length) if content_length else None
        try:
            start_api(restore_bytes)
            self.send_bytes(200, b'{"status":"ready"}')
        except Exception:
            print("[runtime] Could not bootstrap FastAPI", flush=True)
            self.send_bytes(500, b'{"detail":"FastAPI bootstrap failed"}')


if __name__ == "__main__":
    print("[runtime] Internal control server listening on port 8001", flush=True)
    HTTPServer(("0.0.0.0", 8001), Handler).serve_forever()

import http.server
import logging
import os
import threading

import config

log = logging.getLogger(__name__)


class _Handler(http.server.BaseHTTPRequestHandler):
    def _path(self):
        safe = os.path.normpath(self.path.lstrip("/"))
        return os.path.join(config.storage_path(), safe)

    def do_GET(self):
        p = self._path()
        if not os.path.isfile(p):
            self.send_response(404)
            self.end_headers()
            return
        data = open(p, "rb").read()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        p = self._path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        length = int(self.headers.get("Content-Length", 0))
        data   = self.rfile.read(length)
        with open(p, "wb") as f:
            f.write(data)
        self.send_response(200)
        self.end_headers()
        log.debug("FileServer PUT %s (%d bytes)", self.path, length)

    def log_message(self, fmt, *args):
        log.debug("FileServer %s", fmt % args)


def init():
    os.makedirs(config.storage_path(), exist_ok=True)
    port   = config.file_server_port()
    server = http.server.HTTPServer(("0.0.0.0", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="fileserver")
    t.start()
    log.info("File server on port %d serving %s", port, config.storage_path())


def data_key(data_id: int, version: int) -> str:
    return f"{data_id:011d}-{version:05d}"


def object_url(key: str) -> str:
    location = config.secure_server_location()
    port     = config.file_server_port()
    return f"http://{location}:{port}/{key}"


def object_size(key: str) -> int:
    path = os.path.join(config.storage_path(), os.path.normpath(key))
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def write_object(key: str, data: bytes):
    """Write a blob directly to the file-server storage so the 3DS can GET it."""
    path = os.path.join(config.storage_path(), os.path.normpath(key))
    os.makedirs(os.path.dirname(path) or config.storage_path(), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    log.debug("Stored object %s (%d bytes)", key, len(data))

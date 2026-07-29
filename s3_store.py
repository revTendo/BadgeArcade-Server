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

    def do_HEAD(self):

        p = self._path()
        if not os.path.isfile(p):
            log.info("[FILE] HEAD %s -> 404", self.path)
            self.send_response(404)
            self.end_headers()
            return
        size = os.path.getsize(p)
        log.info("[FILE] HEAD %s -> 200 (%d bytes)", self.path, size)
        self.send_response(200)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

    def do_GET(self):
        p = self._path()
        if not os.path.isfile(p):
            log.info("[FILE] GET %s -> 404 (not found at %s)", self.path, p)
            self.send_response(404)
            self.end_headers()
            return
        log.info("[FILE] GET %s -> 200", self.path)
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
        log.info("[FILE] PUT %s (%d bytes)", self.path, length)

    def do_POST(self):
        log.info("[FILE] POST %s ctype=%s len=%s", self.path,
                 self.headers.get("Content-Type","")[:40], self.headers.get("Content-Length"))

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        ctype  = self.headers.get("Content-Type", "")

        key, file_data = self._parse_multipart(body, ctype)
        if key is None:

            key = os.path.normpath(self.path.lstrip("/"))
        if file_data is None:
            file_data = b""

        dest = os.path.join(config.storage_path(), os.path.normpath(key))
        os.makedirs(os.path.dirname(dest) or config.storage_path(), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(file_data)
        log.info("[FILE] POST stored key=%s (%d bytes)", key, len(file_data))

        self.send_response(204)
        self.end_headers()

    def _parse_multipart(self, body: bytes, content_type: str):

        if "boundary=" not in content_type:
            return None, None
        boundary = content_type.split("boundary=", 1)[1].strip().strip('"')
        delim = ("--" + boundary).encode()
        key = None
        file_data = None
        for part in body.split(delim):
            if not part or part in (b"--\r\n", b"--", b"\r\n"):
                continue
            if b"\r\n\r\n" not in part:
                continue
            headers_blob, content = part.split(b"\r\n\r\n", 1)

            if content.endswith(b"\r\n"):
                content = content[:-2]
            hdrs = headers_blob.decode("latin-1", "replace").lower()

            name = None
            for token in hdrs.split(";"):
                token = token.strip()
                if token.startswith("name="):
                    name = token[5:].strip().strip('"')
                    break
            if name == "key":
                key = content.decode("latin-1", "replace").strip()
            elif name == "file" or "filename=" in hdrs:
                file_data = content
        return key, file_data

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
    location = config.file_server_host()
    port     = config.file_server_port()
    return f"http://{location}:{port}/{key}"

def object_size(key: str) -> int:
    path = os.path.join(config.storage_path(), os.path.normpath(key))
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def write_object(key: str, data: bytes):

    path = os.path.join(config.storage_path(), os.path.normpath(key))
    os.makedirs(os.path.dirname(path) or config.storage_path(), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    log.debug("Stored object %s (%d bytes)", key, len(data))

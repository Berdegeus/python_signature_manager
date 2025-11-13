import http.server
import os
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, List

BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
ROUTER_PORT = int(os.environ.get("ROUTER_PORT", "80"))
BACKEND_TIMEOUT = float(os.environ.get("BACKEND_TIMEOUT", "10"))
DISCOVERY_INTERVAL = float(os.environ.get("BACKEND_DISCOVERY_INTERVAL", "2"))
HEALTH_PATH = os.environ.get("BACKEND_HEALTH_PATH", "/health")
PORT_SPEC = (
    os.environ.get("BACKEND_PORTS")
    or os.environ.get("BACKEND_PORT_POOL")
    or os.environ.get("BACKEND_PORT")
    or "8000-8100"
)

CSHARP_HOST = os.environ.get("CSHARP_BACKEND_HOST", BACKEND_HOST)
CSHARP_TIMEOUT = float(os.environ.get("CSHARP_BACKEND_TIMEOUT", str(BACKEND_TIMEOUT)))
CSHARP_HEALTH_PATH = os.environ.get("CSHARP_BACKEND_HEALTH_PATH", HEALTH_PATH)
CSHARP_PREFIX = os.environ.get("CSHARP_PREFIX", "/csharp")
CSHARP_PORT_SPEC = (
    os.environ.get("CSHARP_BACKEND_PORTS")
    or os.environ.get("CSHARP_BACKEND_PORT_POOL")
    or os.environ.get("CSHARP_BACKEND_PORT")
    or "7000-7100"
)


def parse_port_candidates(raw: str) -> List[int]:
    ports: List[int] = []
    seen: set[int] = set()

    for chunk in (piece.strip() for piece in raw.split(",") if piece.strip()):
        if "-" in chunk:
            start_str, end_str = chunk.split("-", 1)
            start = _coerce_port(start_str)
            end = _coerce_port(end_str)
            if start > end:
                raise ValueError(f"invalid port range: {chunk}")
            for port in range(start, end + 1):
                if port not in seen:
                    ports.append(port)
                    seen.add(port)
            continue

        port = _coerce_port(chunk)
        if port not in seen:
            ports.append(port)
            seen.add(port)

    return ports


def _coerce_port(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid port number: {raw}") from exc
    if value <= 0 or value > 65535:
        raise ValueError(f"invalid port number: {raw}")
    return value


class BackendPool:
    def __init__(
        self,
        host: str,
        candidates: List[int],
        health_path: str,
        timeout: float,
        probe: Callable[[str, int, str, float], bool],
    ) -> None:
        if not candidates:
            raise ValueError("at least one backend port is required")
        self.host = host
        self.candidates = candidates
        self.health_path = health_path
        self.timeout = timeout
        self._probe = probe
        self._lock = threading.Lock()
        self._healthy: list[int] = []
        self._cursor = 0

    def refresh(self) -> None:
        healthy: list[int] = []
        for port in self.candidates:
            if self._probe(self.host, port, self.health_path, self.timeout):
                healthy.append(port)

        with self._lock:
            self._healthy = healthy
            if self._healthy:
                self._cursor %= len(self._healthy)
            else:
                self._cursor = 0

    def next_backend(self) -> int | None:
        with self._lock:
            if not self._healthy:
                return None
            port = self._healthy[self._cursor]
            self._cursor = (self._cursor + 1) % len(self._healthy)
            return port

    def mark_unhealthy(self, port: int) -> None:
        with self._lock:
            if port not in self._healthy:
                return
            idx = self._healthy.index(port)
            self._healthy.pop(idx)
            if self._cursor > idx:
                self._cursor -= 1
            if self._cursor >= len(self._healthy):
                self._cursor = 0

    def snapshot(self) -> list[int]:
        with self._lock:
            return list(self._healthy)


def probe_backend(host: str, port: int, health_path: str, timeout: float) -> bool:
    target = f"http://{host}:{port}{health_path}"
    req = urllib.request.Request(target, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.getcode() < 500
    except Exception:
        return False


CANDIDATE_PORTS = parse_port_candidates(PORT_SPEC)
POOL = BackendPool(BACKEND_HOST, CANDIDATE_PORTS, HEALTH_PATH, BACKEND_TIMEOUT, probe_backend)

CSHARP_CANDIDATES = parse_port_candidates(CSHARP_PORT_SPEC) if CSHARP_PREFIX else []
CSHARP_POOL = (
    BackendPool(CSHARP_HOST, CSHARP_CANDIDATES, CSHARP_HEALTH_PATH, CSHARP_TIMEOUT, probe_backend)
    if CSHARP_PREFIX and CSHARP_CANDIDATES
    else None
)

ROUTING_RULES: list[tuple[str, BackendPool]] = []

if CSHARP_POOL is not None:
    rule_prefix = CSHARP_PREFIX.rstrip("/")
    if not rule_prefix:
        rule_prefix = "/csharp"
    if rule_prefix != "/":
        ROUTING_RULES.append((rule_prefix, CSHARP_POOL))

ROUTING_RULES.append(("", POOL))

POOLS_TO_MONITOR: list[tuple[str, BackendPool]] = [("default", POOL)]
if CSHARP_POOL is not None:
    POOLS_TO_MONITOR.append(("csharp", CSHARP_POOL))


class Proxy(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.proxy()

    def do_GET(self):
        self.proxy()

    def do_POST(self):
        self.proxy(with_body=True)

    def do_PUT(self):
        self.proxy(with_body=True)

    def do_PATCH(self):
        self.proxy(with_body=True)

    def do_DELETE(self):
        self.proxy()

    def do_OPTIONS(self):
        self.proxy()

    def log_message(self, format, *args):
        return

    def proxy(self, with_body: bool = False) -> None:
        parsed_path = urllib.parse.urlsplit(self.path)
        incoming_path = parsed_path.path or "/"
        query = parsed_path.query
        pool, outgoing_path = choose_route(incoming_path)
        tried: set[int] = set()
        while True:
            port = pool.next_backend()
            if port is None or port in tried:
                self._respond_unavailable()
                return

            tried.add(port)
            if self._forward_request(pool, port, outgoing_path, query, with_body):
                return
            pool.mark_unhealthy(port)

    def _forward_request(
        self,
        pool: BackendPool,
        port: int,
        path: str,
        query: str,
        with_body: bool,
    ) -> bool:
        qs = f"?{query}" if query else ""
        target = f"http://{pool.host}:{port}{path}{qs}"

        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in {"host", "content-length", "accept-encoding"}
        }

        data = None
        if with_body:
            length = int(self.headers.get("Content-Length", "0"))
            data = self.rfile.read(length) if length > 0 else None

        req = urllib.request.Request(target, data=data, method=self.command, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=BACKEND_TIMEOUT) as resp:
                self._relay_response(resp.getcode(), resp.getheaders(), resp.read())
                return True
        except urllib.error.HTTPError as err:
            self._relay_response(err.code, err.headers.items(), err.read())
            return True
        except Exception:
            return False

    def _relay_response(self, status: int, headers, body: bytes) -> None:
        self.send_response(status)
        for key, value in headers:
            if key.lower() in {
                "transfer-encoding",
                "content-encoding",
                "connection",
                "keep-alive",
                "proxy-authenticate",
                "proxy-authorization",
                "te",
                "trailers",
                "upgrade",
            }:
                continue
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _respond_unavailable(self) -> None:
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":"no backend available"}')


def start_discovery_loop() -> None:
    def loop() -> None:
        while True:
            for name, pool in POOLS_TO_MONITOR:
                try:
                    pool.refresh()
                    healthy = pool.snapshot()
                    print(f"[router] {name} healthy backends: {[f'{pool.host}:{p}' for p in healthy]}")
                except Exception as exc:
                    print(f"[router] discovery error ({name}): {exc}")
            time.sleep(max(1.0, DISCOVERY_INTERVAL))

    for _, pool in POOLS_TO_MONITOR:
        pool.refresh()
    threading.Thread(target=loop, daemon=True).start()


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    start_discovery_loop()
    with ThreadingTCPServer(("0.0.0.0", ROUTER_PORT), Proxy) as httpd:
        targets = [f"{name}:{pool.host}:{','.join(map(str, pool.candidates))}" for name, pool in POOLS_TO_MONITOR]
        print(f"[router] listening on :{ROUTER_PORT} (targets {targets})")
        httpd.serve_forever()
def choose_route(path: str) -> tuple[BackendPool, str]:
    normalized = path or "/"
    for prefix, pool in ROUTING_RULES:
        if not prefix:
            return pool, normalized
        if normalized == prefix or normalized.startswith(prefix + "/"):
            stripped = normalized[len(prefix) :] or "/"
            if not stripped.startswith("/"):
                stripped = "/" + stripped
            return pool, stripped
    return POOL, normalized

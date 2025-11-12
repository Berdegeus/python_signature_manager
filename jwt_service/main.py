from __future__ import annotations

import contextlib
import signal
import sys
from typing import Iterator

from .config import load_config
from .server import create_server


def _wait_for_interrupt() -> Iterator[None]:  # pragma: no cover - cli helper
    stop = False

    def _handler(signum, frame):  # noqa: ARG001
        nonlocal stop
        stop = True

    old_sigint = signal.getsignal(signal.SIGINT)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)
    try:
        while not stop:
            signal.pause()
            yield
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)


def main() -> None:
    config = load_config()
    server = create_server(config)
    print(f"[jwt-service] listening on {config.host}:{config.port}")
    with contextlib.closing(server):
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    print("[jwt-service] shutting down")


if __name__ == "__main__":  # pragma: no cover - cli entry point
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"[jwt-service] fatal error: {exc}", file=sys.stderr)
        sys.exit(1)

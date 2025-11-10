from __future__ import annotations

import errno
from typing import Iterable

from .config import Config
from .adapters.uow import SqlUnitOfWork
from .app.server import run_server
from .app.handlers import build_handler
from .ports.clock import RealClock


def _run_with_port_pool(handler, host: str, ports: Iterable[int]) -> None:
    ports_to_try: list[int] = list(ports)
    if not ports_to_try:
        raise ValueError("At least one port must be specified")

    last_error: OSError | None = None
    for port in ports_to_try:
        try:
            run_server(handler, port, host=host)
            return
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                print(f"[server] {host}:{port} already in use, trying next candidate...")
                last_error = exc
                continue
            raise

    raise RuntimeError("No available ports to bind") from last_error


def main() -> None:
    cfg = Config()
    conn_factory = cfg.get_connection_factory()
    repo_factory = cfg.get_repo_factory()

    def uow_factory():
        return SqlUnitOfWork(conn_factory, repo_factory)

    handler = build_handler(uow_factory, cfg.jwt_secret, RealClock())
    _run_with_port_pool(handler, cfg.host, cfg.port_candidates)


if __name__ == "__main__":
    main()

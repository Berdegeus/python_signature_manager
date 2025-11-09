from __future__ import annotations

from libs.python.data_access import SqlUnitOfWork
from libs.python.http_core import run_server
from .config import Config
from .app.handlers import build_handler
from .ports.clock import RealClock


def main() -> None:
    cfg = Config()
    conn_factory = cfg.get_connection_factory()
    repo_factory = cfg.get_repo_factory()

    def uow_factory():
        return SqlUnitOfWork(conn_factory, repo_factory)

    handler = build_handler(uow_factory, cfg.jwt_secret, RealClock())
    run_server(handler, cfg.port)


if __name__ == "__main__":
    main()


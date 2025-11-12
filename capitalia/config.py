import os
import pathlib
from typing import Callable, Any, Dict, List


def _load_dotenv_if_present() -> None:
    # Optional, no dependency: load simple KEY=VALUE lines
    env_path = pathlib.Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv_if_present()


class Config:
    def __init__(self) -> None:
        self.db_kind: str = os.environ.get('DB_KIND', 'sqlite').lower()
        self.sqlite_path: str = os.environ.get('SQLITE_PATH', 'capitalia.db')
        self.mysql: Dict[str, str] = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'capitalia_user'),
            'password': os.environ.get('MYSQL_PASSWORD', 'changeme'),
            'db': os.environ.get('MYSQL_DB', 'capitalia'),
            'port': int(os.environ.get('MYSQL_PORT', '3306')),
            'charset': 'utf8mb4',
        }
        self.jwt_secret: str = os.environ.get('JWT_SECRET', 'change-me')
        self.jwt_service_url: str = os.environ.get('JWT_SERVICE_URL', 'http://127.0.0.1:8200')
        self.jwt_service_timeout: float = float(os.environ.get('JWT_SERVICE_TIMEOUT', '5'))
        port_pool_raw = os.environ.get('PORT_POOL')
        raw_port = os.environ.get('PORT', '8000-8100')
        self.port_candidates: List[int] = self._parse_port_candidates(port_pool_raw or raw_port)
        if not port_pool_raw and 0 not in self.port_candidates:
            self.port_candidates.append(0)
        if not self.port_candidates:
            raise ValueError('No valid ports configured via PORT or PORT_POOL')
        self.port: int = self.port_candidates[0]
        self.host: str = os.environ.get('HOST', '0.0.0.0')

    def get_strategy(self) -> str:
        if self.db_kind not in ('sqlite', 'mysql'):
            raise ValueError('DB_KIND must be sqlite or mysql')
        return self.db_kind

    def get_connection_factory(self) -> Callable[[], Any]:
        kind = self.get_strategy()
        if kind == 'sqlite':
            import sqlite3

            path = self.sqlite_path

            def factory() -> sqlite3.Connection:
                conn = sqlite3.connect(path)
                conn.execute('PRAGMA foreign_keys = ON')
                return conn

            return factory
        else:
            import pymysql

            def factory() -> Any:
                return pymysql.connect(
                    host=self.mysql['host'],
                    user=self.mysql['user'],
                    password=self.mysql['password'],
                    database=self.mysql['db'],
                    port=self.mysql['port'],
                    charset=self.mysql['charset'],
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                )

            return factory

    def get_repo_factory(self) -> Callable[[Any], Any]:
        kind = self.get_strategy()
        if kind == 'sqlite':
            from .adapters.sqlite_repo import SqliteUserRepository

            def repo_factory(conn: Any) -> Any:
                return SqliteUserRepository(conn)

            return repo_factory

        else:
            from .adapters.mysql_repo import MySQLUserRepository

            def repo_factory(conn: Any) -> Any:
                return MySQLUserRepository(conn)

            return repo_factory

    @staticmethod
    def _parse_port_candidates(raw: str) -> List[int]:
        ports: List[int] = []
        seen: set[int] = set()

        for chunk in (piece.strip() for piece in raw.split(',') if piece.strip()):
            if chunk.lower() == 'auto':
                value = 0
                Config._append_port_if_new(value, ports, seen)
                continue

            if '-' in chunk:
                start_str, end_str = chunk.split('-', 1)
                start = Config._coerce_port(start_str)
                end = Config._coerce_port(end_str)
                if start > end:
                    raise ValueError(f'Invalid port range {chunk!r}')
                for value in range(start, end + 1):
                    Config._append_port_if_new(value, ports, seen)
                continue

            value = Config._coerce_port(chunk)
            Config._append_port_if_new(value, ports, seen)

        return ports

    @staticmethod
    def _coerce_port(raw: str) -> int:
        value = int(raw)
        if value < 0 or value > 65535:
            raise ValueError(f'Invalid port number: {value}')
        return value

    @staticmethod
    def _append_port_if_new(value: int, ports: List[int], seen: set[int]) -> None:
        if value not in seen:
            ports.append(value)
            seen.add(value)

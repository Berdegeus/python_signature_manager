from __future__ import annotations

import pytest

from router.router import BackendPool, parse_port_candidates


def test_parse_port_candidates_accepts_ranges_and_deduplicates() -> None:
    ports = parse_port_candidates("8080,8082-8084,8083")
    assert ports == [8080, 8082, 8083, 8084]


def test_parse_port_candidates_rejects_invalid_ports() -> None:
    with pytest.raises(ValueError):
        parse_port_candidates("0,8080")


def test_backend_pool_refresh_and_round_robin() -> None:
    status = {9000: True, 9001: False, 9002: True}

    def probe(host: str, port: int, health: str, timeout: float) -> bool:
        return status.get(port, False)

    pool = BackendPool("localhost", [9000, 9001, 9002], "/health", 0.1, probe)
    pool.refresh()

    assert pool.snapshot() == [9000, 9002]
    assert pool.next_backend() == 9000
    assert pool.next_backend() == 9002
    assert pool.next_backend() == 9000

    pool.mark_unhealthy(9000)
    assert pool.snapshot() == [9002]
    assert pool.next_backend() == 9002

    pool.mark_unhealthy(9002)
    assert pool.next_backend() is None

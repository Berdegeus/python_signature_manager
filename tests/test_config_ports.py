from __future__ import annotations

import pytest

from capitalia.config import Config


def _clear_port_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("PORT", "PORT_POOL", "HOST"):
        monkeypatch.delenv(key, raising=False)


def test_default_port_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    cfg = Config()
    assert cfg.port_candidates[0] == 8000
    assert cfg.port_candidates[-1] == 0
    assert len(cfg.port_candidates) == 102  # 8000-8100 + auto fallback
    assert cfg.port == 8000
    assert cfg.host == "0.0.0.0"


def test_port_range_from_port_var(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    monkeypatch.setenv("PORT", "9000, 9005-9006")
    cfg = Config()
    assert cfg.port_candidates == [9000, 9005, 9006, 0]
    assert cfg.port == 9000


def test_port_pool_overrides_port(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("PORT_POOL", "9100-9101,auto")
    cfg = Config()
    assert cfg.port_candidates == [9100, 9101, 0]
    assert cfg.port == 9100


def test_port_pool_disables_default_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    monkeypatch.setenv("PORT_POOL", "9200")
    cfg = Config()
    assert cfg.port_candidates == [9200]


def test_auto_in_port_prevents_extra_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    monkeypatch.setenv("PORT", "auto, 9300")
    cfg = Config()
    assert cfg.port_candidates == [0, 9300]


def test_invalid_port_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_port_env(monkeypatch)
    monkeypatch.setenv("PORT", "-1")
    with pytest.raises(ValueError):
        Config()

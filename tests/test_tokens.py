from __future__ import annotations

from bulutklinik import InMemoryTokenStore


def test_seed_set_and_clear() -> None:
    store = InMemoryTokenStore("a", "r")
    assert store.get_access_token() == "a"
    assert store.get_refresh_token() == "r"

    store.set_tokens("a2", "r2")
    assert store.get_access_token() == "a2"
    assert store.get_refresh_token() == "r2"

    store.clear()
    assert store.get_access_token() is None
    assert store.get_refresh_token() is None


def test_defaults_to_none() -> None:
    store = InMemoryTokenStore()
    assert store.get_access_token() is None
    assert store.get_refresh_token() is None

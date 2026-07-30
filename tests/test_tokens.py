from __future__ import annotations

from bulutklinik import InMemoryTokenStore, TokenStore


def test_seed_set_and_clear() -> None:
    store = InMemoryTokenStore("a")
    assert store.get_token() == "a"

    store.set_token("b")
    assert store.get_token() == "b"

    store.clear()
    assert store.get_token() is None


def test_defaults_to_none() -> None:
    assert InMemoryTokenStore().get_token() is None


def test_explicit_none_unsets() -> None:
    store = InMemoryTokenStore("a")
    store.set_token(None)
    assert store.get_token() is None


def test_in_memory_store_satisfies_the_protocol() -> None:
    assert isinstance(InMemoryTokenStore("a"), TokenStore)

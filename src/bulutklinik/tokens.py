from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """Pluggable source for the partner token.

    The token is read on **every** request, so pointing this at a file, cache,
    database or secret manager lets a long-running process pick up a newly issued
    token without being rebuilt.
    """

    def get_token(self) -> str | None: ...

    def set_token(self, token: str | None) -> None: ...

    def clear(self) -> None: ...


class InMemoryTokenStore:
    """In-memory token store (default). The token lives for the lifetime of the
    object."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def get_token(self) -> str | None:
        return self._token

    def set_token(self, token: str | None) -> None:
        self._token = token

    def clear(self) -> None:
        self._token = None

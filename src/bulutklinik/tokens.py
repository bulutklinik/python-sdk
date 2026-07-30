from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """Pluggable source for the partner access token.

    The token is read on **every** request, so pointing this at a file, cache,
    database or secret manager lets a long-running process pick up a newly issued
    token without being rebuilt.
    """

    def get_token(self) -> str | None: ...

    def set_token(self, token: str | None) -> None: ...

    def clear(self) -> None: ...


@runtime_checkable
class RefreshTokenStore(TokenStore, Protocol):
    """Optional extension: a store that also persists the refresh token.

    Implementing this is not required — a :class:`TokenStore` written against
    spec 1.0.x keeps working. When the injected store does not implement it the
    SDK holds the refresh token in memory for the client's lifetime, so a process
    restart needs ``auth.connect`` rather than ``auth.refresh``.
    """

    def get_refresh_token(self) -> str | None: ...

    def set_refresh_token(self, token: str | None) -> None: ...


class InMemoryTokenStore:
    """In-memory token store (default). Tokens live for the lifetime of the object."""

    def __init__(self, token: str | None = None, refresh_token: str | None = None) -> None:
        self._token = token
        self._refresh_token = refresh_token

    def get_token(self) -> str | None:
        return self._token

    def set_token(self, token: str | None) -> None:
        self._token = token

    def get_refresh_token(self) -> str | None:
        return self._refresh_token

    def set_refresh_token(self, token: str | None) -> None:
        self._refresh_token = token

    def clear(self) -> None:
        self._token = None
        self._refresh_token = None

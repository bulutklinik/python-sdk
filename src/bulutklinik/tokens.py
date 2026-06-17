from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    """Pluggable token persistence. The default is in-memory; provide your own to
    persist tokens to a file, cache, database or session."""

    def get_access_token(self) -> str | None: ...

    def get_refresh_token(self) -> str | None: ...

    def set_tokens(self, access_token: str, refresh_token: str | None) -> None: ...

    def clear(self) -> None: ...


class InMemoryTokenStore:
    """In-memory token store (default). Tokens live for the lifetime of the object."""

    def __init__(self, access_token: str | None = None, refresh_token: str | None = None) -> None:
        self._access = access_token
        self._refresh = refresh_token

    def get_access_token(self) -> str | None:
        return self._access

    def get_refresh_token(self) -> str | None:
        return self._refresh

    def set_tokens(self, access_token: str, refresh_token: str | None) -> None:
        self._access = access_token
        self._refresh = refresh_token

    def clear(self) -> None:
        self._access = None
        self._refresh = None

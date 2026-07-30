"""Transport core. Pure helpers are shared; the sync and async clients differ
only in how they perform I/O and the refresh call.

On a ``401`` / ``resultType 4`` the transport refreshes once and retries the
original request (DESIGN.md §5.4). The error surfaces only when there is no
refresh token or the refresh itself fails.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ._spec import RequestSpec
from .errors import ApiError, AuthenticationError, TransportError, create_api_error
from .tokens import RefreshTokenStore, TokenStore

_NO_TOKEN = (
    "No access token available. Call auth.connect, or construct the client with partner_token."
)


def _build_headers(spec: RequestSpec, lang: str, token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json", "lang": lang}
    if spec.auth == "partner" and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _json_body(spec: RequestSpec) -> dict[str, Any] | None:
    return spec.body if (spec.body is not None and spec.method != "GET") else None


def _parse_envelope(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except ValueError:
        return {"errorMessage": text}
    return decoded if isinstance(decoded, dict) else {"data": decoded}


def _is_success(status: int, envelope: dict[str, Any]) -> bool:
    return 200 <= status < 300 and envelope.get("resultType") == 0


def _is_expired(status: int, envelope: dict[str, Any]) -> bool:
    return status == 401 or envelope.get("resultType") == 4


def _require_token(spec: RequestSpec, token: str | None) -> str | None:
    """Fail before dispatch when a partner call has no credential — sending it
    anyway would only come back as an opaque 401."""
    if spec.auth == "partner" and not token:
        raise AuthenticationError(_NO_TOKEN, http_status=0, method=spec.method, path=spec.path)
    return token


def _tokens_from(envelope: dict[str, Any]) -> tuple[str, str | None] | None:
    data = envelope.get("data")
    if not isinstance(data, dict):
        return None
    access = data.get("access_token")
    if not isinstance(access, str) or not access:
        return None
    refresh = data.get("refresh_token")
    return access, refresh if isinstance(refresh, str) else None


def _to_error(
    spec: RequestSpec, status: int, envelope: dict[str, Any], retry_after_header: str | None
) -> ApiError:
    retry_after = (
        int(retry_after_header) if retry_after_header and retry_after_header.isdigit() else None
    )
    message = envelope.get("errorMessage")
    if not isinstance(message, str) or not message:
        message = f"Bulutklinik API request failed: {spec.method} {spec.path} (HTTP {status})"
    result_type = envelope.get("resultType")
    error_type = envelope.get("errorType")
    return create_api_error(
        message,
        http_status=status,
        result_type=result_type if isinstance(result_type, int) else None,
        error_type=error_type if isinstance(error_type, (str, int)) else None,
        data=envelope.get("data"),
        method=spec.method,
        path=spec.path,
        retry_after=retry_after,
    )


class _TokenMixin:
    """Token bookkeeping shared by the sync and async transports."""

    token_store: TokenStore
    client_id: str | None
    client_secret: str | None
    _fallback_refresh: str | None

    def set_tokens(self, access: str, refresh: str | None) -> None:
        self.token_store.set_token(access)
        if isinstance(self.token_store, RefreshTokenStore):
            self.token_store.set_refresh_token(refresh)
        else:
            self._fallback_refresh = refresh

    def get_refresh_token(self) -> str | None:
        if isinstance(self.token_store, RefreshTokenStore):
            return self.token_store.get_refresh_token()
        return self._fallback_refresh

    def clear_tokens(self) -> None:
        self._fallback_refresh = None
        self.token_store.clear()

    def _can_refresh(self) -> str | None:
        token = self.get_refresh_token()
        if not token or not self.client_id or not self.client_secret:
            return None
        return token


class HttpClient(_TokenMixin):
    """Synchronous transport: unwraps the envelope, maps errors, refreshes once."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        client_id: str | None,
        client_secret: str | None,
        token_store: TokenStore,
        client: httpx.Client,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_store = token_store
        self._fallback_refresh: str | None = None
        self._client = client

    def send(self, spec: RequestSpec, *, _is_retry: bool = False) -> Any:
        status, envelope, retry_after = self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        if (
            spec.auth == "partner"
            and _is_expired(status, envelope)
            and not _is_retry
            and self._try_refresh()
        ):
            return self.send(spec, _is_retry=True)
        if envelope.get("resultType") == 2:
            self.clear_tokens()
        raise _to_error(spec, status, envelope, retry_after)

    def refresh(self) -> None:
        if not self._try_refresh():
            raise AuthenticationError(
                "Token refresh failed", http_status=401, method="POST", path="/general/refreshApi"
            )

    def close(self) -> None:
        self._client.close()

    def _dispatch(self, spec: RequestSpec) -> tuple[int, dict[str, Any], str | None]:
        token = _require_token(spec, self.token_store.get_token())
        headers = _build_headers(spec, self.lang, token)
        try:
            response = self._client.request(
                spec.method, self.base_url + spec.path, headers=headers, json=_json_body(spec)
            )
        except httpx.HTTPError as exc:
            raise TransportError(f"Network error on {spec.method} {spec.path}: {exc}") from exc
        return (
            response.status_code,
            _parse_envelope(response.text),
            response.headers.get("retry-after"),
        )

    def _try_refresh(self) -> bool:
        from . import _spec

        refresh_token = self._can_refresh()
        if refresh_token is None:
            return False
        assert self.client_id is not None and self.client_secret is not None
        try:
            status, envelope, _ = self._dispatch(
                _spec.refresh(refresh_token, self.client_id, self.client_secret)
            )
        except TransportError:
            return False
        tokens = _tokens_from(envelope) if _is_success(status, envelope) else None
        if tokens is None:
            self.clear_tokens()
            return False
        self.set_tokens(tokens[0], tokens[1] or refresh_token)
        return True


class AsyncHttpClient(_TokenMixin):
    """Asynchronous transport — same behavior as :class:`HttpClient`."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        client_id: str | None,
        client_secret: str | None,
        token_store: TokenStore,
        client: httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_store = token_store
        self._fallback_refresh: str | None = None
        self._client = client

    async def send(self, spec: RequestSpec, *, _is_retry: bool = False) -> Any:
        status, envelope, retry_after = await self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        if (
            spec.auth == "partner"
            and _is_expired(status, envelope)
            and not _is_retry
            and await self._try_refresh()
        ):
            return await self.send(spec, _is_retry=True)
        if envelope.get("resultType") == 2:
            self.clear_tokens()
        raise _to_error(spec, status, envelope, retry_after)

    async def refresh(self) -> None:
        if not await self._try_refresh():
            raise AuthenticationError(
                "Token refresh failed", http_status=401, method="POST", path="/general/refreshApi"
            )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _dispatch(self, spec: RequestSpec) -> tuple[int, dict[str, Any], str | None]:
        token = _require_token(spec, self.token_store.get_token())
        headers = _build_headers(spec, self.lang, token)
        try:
            response = await self._client.request(
                spec.method, self.base_url + spec.path, headers=headers, json=_json_body(spec)
            )
        except httpx.HTTPError as exc:
            raise TransportError(f"Network error on {spec.method} {spec.path}: {exc}") from exc
        return (
            response.status_code,
            _parse_envelope(response.text),
            response.headers.get("retry-after"),
        )

    async def _try_refresh(self) -> bool:
        from . import _spec

        refresh_token = self._can_refresh()
        if refresh_token is None:
            return False
        assert self.client_id is not None and self.client_secret is not None
        try:
            status, envelope, _ = await self._dispatch(
                _spec.refresh(refresh_token, self.client_id, self.client_secret)
            )
        except TransportError:
            return False
        tokens = _tokens_from(envelope) if _is_success(status, envelope) else None
        if tokens is None:
            self.clear_tokens()
            return False
        self.set_tokens(tokens[0], tokens[1] or refresh_token)
        return True

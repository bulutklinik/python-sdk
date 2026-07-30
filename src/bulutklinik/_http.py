"""Transport core. Pure helpers are shared; the sync and async clients differ
only in how they perform I/O.

There is no silent refresh: a partner token is issued out of band and cannot be
renewed from here, so an expired one (``401`` / ``resultType 4``) surfaces as an
``AuthenticationError`` instead of being retried.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ._spec import RequestSpec
from .errors import ApiError, AuthenticationError, TransportError, create_api_error
from .tokens import TokenStore


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


def _require_token(spec: RequestSpec, token: str | None) -> str | None:
    """Fail before dispatch when a partner call has no credential — sending it
    anyway would only come back as an opaque 401."""
    if spec.auth == "partner" and not token:
        raise AuthenticationError(
            "No partner token configured.", http_status=0, method=spec.method, path=spec.path
        )
    return token


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


class HttpClient:
    """Synchronous transport: unwraps the envelope and maps errors."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        token_store: TokenStore,
        client: httpx.Client,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.token_store = token_store
        self._client = client

    def send(self, spec: RequestSpec) -> Any:
        status, envelope, retry_after = self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        # A revoked token is worth forgetting; an expired one is not, since the
        # caller may want to inspect it while installing a replacement.
        if envelope.get("resultType") == 2:
            self.token_store.clear()
        raise _to_error(spec, status, envelope, retry_after)

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


class AsyncHttpClient:
    """Asynchronous transport — same behavior as :class:`HttpClient`."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        token_store: TokenStore,
        client: httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.token_store = token_store
        self._client = client

    async def send(self, spec: RequestSpec) -> Any:
        status, envelope, retry_after = await self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        if envelope.get("resultType") == 2:
            self.token_store.clear()
        raise _to_error(spec, status, envelope, retry_after)

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

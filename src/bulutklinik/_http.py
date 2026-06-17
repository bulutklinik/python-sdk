"""Transport core. Pure helpers are shared; the sync and async clients differ
only in how they perform I/O and the refresh call."""

from __future__ import annotations

import json
from typing import Any

import httpx

from ._spec import RequestSpec
from .errors import ApiError, AuthenticationError, TransportError, create_api_error
from .tokens import TokenStore


def _build_headers(
    spec: RequestSpec, lang: str, access_token: str | None, partner_token: str | None
) -> dict[str, str]:
    headers = {"Accept": "application/json", "lang": lang}
    if spec.auth == "bearer" and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif spec.auth == "partner" and partner_token:
        headers["Authorization"] = f"Bearer {partner_token}"
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
    """Synchronous transport: unwraps the envelope, maps errors, and silently
    refreshes + retries once on a 401 / ``resultType 4``."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        client_id: str | None,
        client_secret: str | None,
        partner_token: str | None,
        token_store: TokenStore,
        client: httpx.Client,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.client_id = client_id
        self.client_secret = client_secret
        self.partner_token = partner_token
        self.token_store = token_store
        self._client = client

    def send(self, spec: RequestSpec, *, _is_retry: bool = False) -> Any:
        status, envelope, retry_after = self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        if (
            spec.auth == "bearer"
            and _is_expired(status, envelope)
            and not _is_retry
            and self._try_refresh()
        ):
            return self.send(spec, _is_retry=True)
        if envelope.get("resultType") == 2:
            self.token_store.clear()
        raise _to_error(spec, status, envelope, retry_after)

    def refresh(self) -> None:
        if not self._try_refresh():
            raise AuthenticationError("Token refresh failed", http_status=401)

    def close(self) -> None:
        self._client.close()

    def _dispatch(self, spec: RequestSpec) -> tuple[int, dict[str, Any], str | None]:
        headers = _build_headers(
            spec, self.lang, self.token_store.get_access_token(), self.partner_token
        )
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
        refresh_token = self.token_store.get_refresh_token()
        if not refresh_token or not self.client_id or not self.client_secret:
            return False
        spec = RequestSpec(
            "POST",
            "/general/refreshApi",
            "public",
            {
                "refreshToken": refresh_token,
                "clientId": self.client_id,
                "clientSecretKey": self.client_secret,
            },
        )
        try:
            status, envelope, _ = self._dispatch(spec)
        except TransportError:
            return False
        data = envelope.get("data")
        if (
            not _is_success(status, envelope)
            or not isinstance(data, dict)
            or not isinstance(data.get("access_token"), str)
        ):
            self.token_store.clear()
            return False
        new_refresh = (
            data["refresh_token"] if isinstance(data.get("refresh_token"), str) else refresh_token
        )
        self.token_store.set_tokens(data["access_token"], new_refresh)
        return True


class AsyncHttpClient:
    """Asynchronous transport — same behavior as :class:`HttpClient`."""

    def __init__(
        self,
        *,
        base_url: str,
        lang: str,
        client_id: str | None,
        client_secret: str | None,
        partner_token: str | None,
        token_store: TokenStore,
        client: httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url
        self.lang = lang
        self.client_id = client_id
        self.client_secret = client_secret
        self.partner_token = partner_token
        self.token_store = token_store
        self._client = client

    async def send(self, spec: RequestSpec, *, _is_retry: bool = False) -> Any:
        status, envelope, retry_after = await self._dispatch(spec)
        if _is_success(status, envelope):
            return envelope.get("data")
        if (
            spec.auth == "bearer"
            and _is_expired(status, envelope)
            and not _is_retry
            and await self._try_refresh()
        ):
            return await self.send(spec, _is_retry=True)
        if envelope.get("resultType") == 2:
            self.token_store.clear()
        raise _to_error(spec, status, envelope, retry_after)

    async def refresh(self) -> None:
        if not await self._try_refresh():
            raise AuthenticationError("Token refresh failed", http_status=401)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _dispatch(self, spec: RequestSpec) -> tuple[int, dict[str, Any], str | None]:
        headers = _build_headers(
            spec, self.lang, self.token_store.get_access_token(), self.partner_token
        )
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
        refresh_token = self.token_store.get_refresh_token()
        if not refresh_token or not self.client_id or not self.client_secret:
            return False
        spec = RequestSpec(
            "POST",
            "/general/refreshApi",
            "public",
            {
                "refreshToken": refresh_token,
                "clientId": self.client_id,
                "clientSecretKey": self.client_secret,
            },
        )
        try:
            status, envelope, _ = await self._dispatch(spec)
        except TransportError:
            return False
        data = envelope.get("data")
        if (
            not _is_success(status, envelope)
            or not isinstance(data, dict)
            or not isinstance(data.get("access_token"), str)
        ):
            self.token_store.clear()
            return False
        new_refresh = (
            data["refresh_token"] if isinstance(data.get("refresh_token"), str) else refresh_token
        )
        self.token_store.set_tokens(data["access_token"], new_refresh)
        return True

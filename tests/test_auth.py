from __future__ import annotations

from typing import Any

import httpx
import pytest

from bulutklinik import AuthenticationError, BulutklinikClient, InMemoryTokenStore
from helpers import Responder, body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"

TOKENS = {"access_token": "AT", "refresh_token": "RT"}
REF = {"identityNumber": "12345678901"}


def client_with(
    responder: Responder, **kwargs: Any
) -> tuple[BulutklinikClient, list[httpx.Request]]:
    transport, requests = recording_transport(responder)
    kwargs.setdefault("client_id", "cid")
    kwargs.setdefault("client_secret", "csecret")
    return BulutklinikClient(environment="test", transport=transport, **kwargs), requests


def test_connect_posts_portal_credentials_and_stores_both_tokens() -> None:
    client, requests = client_with(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": TOKENS})
    )

    result = client.auth.connect("svc@app.bulutklinik", "hunter2")

    assert result.two_factor_required is False
    assert str(requests[0].url) == f"{BASE}/general/connectApi"
    # The login call is public — it is what produces the credential.
    assert "Authorization" not in requests[0].headers
    assert body_of(requests[0]) == {
        "apiClientId": "cid",
        "apiSecretKey": "csecret",
        "apiUserName": "svc@app.bulutklinik",
        "apiUserPassword": "hunter2",
        "loginMode": "email",
    }
    assert client.token_store.get_token() == "AT"


def test_connect_surfaces_two_factor_challenge_as_a_result() -> None:
    client, _ = client_with(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"response": "BLOB"}})
    )

    result = client.auth.connect("svc", "p")

    assert result.two_factor_required is True
    assert result.two_factor_response == "BLOB"
    assert client.token_store.get_token() is None


def test_connect_requires_client_credentials() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": TOKENS})
    )
    client = BulutklinikClient(environment="test", transport=transport)

    with pytest.raises(ValueError, match="client_id and client_secret are required"):
        client.auth.connect("svc", "p")


def test_refreshes_once_then_retries_with_the_new_token() -> None:
    state = {"data_calls": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/refreshApi"):
            return httpx.Response(
                200, json={"resultType": 0, "data": {"access_token": "AT2", "refresh_token": "RT2"}}
            )
        state["data_calls"] += 1
        if state["data_calls"] == 1:
            return httpx.Response(401, json={"resultType": 4})
        return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})

    store = InMemoryTokenStore("AT", "RT")
    client, requests = client_with(responder, token_store=store)

    assert client.measures.last(REF) == {"ok": True}
    assert store.get_token() == "AT2"
    assert store.get_refresh_token() == "RT2"
    assert body_of(requests[1]) == {
        "refreshToken": "RT",
        "clientId": "cid",
        "clientSecretKey": "csecret",
    }
    assert requests[-1].headers["Authorization"] == "Bearer AT2"


def test_retries_at_most_once_and_clears_on_failed_refresh() -> None:
    state = {"refreshes": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/refreshApi"):
            state["refreshes"] += 1
            return httpx.Response(401, json={"resultType": 1})
        return httpx.Response(401, json={"resultType": 4})

    store = InMemoryTokenStore("AT", "RT")
    client, _ = client_with(responder, token_store=store)

    with pytest.raises(AuthenticationError):
        client.measures.last(REF)
    assert state["refreshes"] == 1
    assert store.get_token() is None


def test_no_refresh_attempt_without_a_refresh_token() -> None:
    state = {"refreshes": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/refreshApi"):
            state["refreshes"] += 1
        return httpx.Response(401, json={"resultType": 4})

    client, _ = client_with(responder, client_id=None, client_secret=None, partner_token="AT")

    with pytest.raises(AuthenticationError, match="could not be refreshed"):
        client.doctors.branches()
    assert state["refreshes"] == 0


def test_store_without_refresh_support_still_refreshes_in_memory() -> None:
    """A store written against spec 1.0.x — access token only — keeps working."""

    class LegacyStore:
        def __init__(self) -> None:
            self.token: str | None = None

        def get_token(self) -> str | None:
            return self.token

        def set_token(self, token: str | None) -> None:
            self.token = token

        def clear(self) -> None:
            self.token = None

    state = {"data_calls": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/connectApi"):
            return httpx.Response(200, json={"resultType": 0, "data": TOKENS})
        if req.url.path.endswith("/general/refreshApi"):
            return httpx.Response(200, json={"resultType": 0, "data": {"access_token": "AT2"}})
        state["data_calls"] += 1
        if state["data_calls"] == 1:
            return httpx.Response(401, json={"resultType": 4})
        return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})

    legacy = LegacyStore()
    client, _ = client_with(responder, token_store=legacy)

    client.auth.connect("svc", "p")
    assert client.measures.last(REF) == {"ok": True}
    assert legacy.token == "AT2"


def test_disconnect_sends_an_empty_body_and_clears_the_store() -> None:
    store = InMemoryTokenStore("AT", "RT")
    client, requests = client_with(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": None}), token_store=store
    )

    client.auth.disconnect()

    assert str(requests[0].url) == f"{BASE}/general/disconnectApi"
    assert requests[0].headers["Authorization"] == "Bearer AT"
    # The device-cleanup fields are deliberately omitted: the server's `device`
    # mapping has no default branch.
    assert body_of(requests[0]) == {}
    assert store.get_token() is None
    assert store.get_refresh_token() is None

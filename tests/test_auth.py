from __future__ import annotations

import httpx
import pytest

from bulutklinik import ApiError, BulutklinikClient, InMemoryTokenStore
from helpers import body_of, recording_transport


def test_connect_stores_tokens_and_fills_credentials() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200,
            json={
                "resultType": 0,
                "data": {"access_token": "t", "refresh_token": "r", "password_policy": {}},
            },
        )
    )
    store = InMemoryTokenStore()
    client = BulutklinikClient(
        environment="test", client_id="c", client_secret="s", transport=transport, token_store=store
    )

    result = client.auth.connect("u", "p", "email")

    assert result.two_factor_required is False
    assert store.get_access_token() == "t"
    assert store.get_refresh_token() == "r"
    body = body_of(requests[0])
    assert body["apiClientId"] == "c"
    assert body["apiSecretKey"] == "s"
    assert body["loginMode"] == "email"


def test_connect_two_factor_challenge() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"response": "BLOB"}})
    )
    client = BulutklinikClient(
        environment="test", client_id="c", client_secret="s", transport=transport
    )

    result = client.auth.connect("u", "p", "email")

    assert result.two_factor_required is True
    assert result.two_factor_response == "BLOB"


def test_disconnect_clears_store_on_error() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(500, json={"resultType": 1, "errorMessage": "fail"})
    )
    store = InMemoryTokenStore("a", "r")
    client = BulutklinikClient(environment="test", transport=transport, token_store=store)

    with pytest.raises(ApiError):
        client.auth.disconnect()
    assert store.get_access_token() is None

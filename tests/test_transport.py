from __future__ import annotations

from typing import Any

import httpx
import pytest

from bulutklinik import (
    AuthenticationError,
    AuthorizationError,
    BulutklinikClient,
    InMemoryTokenStore,
    NotFoundError,
    RateLimitError,
    TransportError,
    ValidationError,
)
from helpers import Responder, body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"

REF = {"identityNumber": "12345678901"}


def _ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})


def client_with(
    responder: Responder, **kwargs: Any
) -> tuple[BulutklinikClient, list[httpx.Request]]:
    transport, requests = recording_transport(responder)
    kwargs.setdefault("partner_token", "PT")
    return BulutklinikClient(environment="test", transport=transport, **kwargs), requests


def test_unwraps_data_and_sends_partner_token_and_lang() -> None:
    client, requests = client_with(
        lambda req: httpx.Response(
            200, json={"resultType": 0, "data": {"foundDoctorsCount": 0, "foundDoctors": []}}
        )
    )

    res = client.doctors.search({"withFreeText": "kardiyoloji"}, 1, ["slot"])

    assert res == {"foundDoctorsCount": 0, "foundDoctors": []}
    assert str(requests[0].url) == f"{BASE}/outher/search"
    assert requests[0].headers["Authorization"] == "Bearer PT"
    assert requests[0].headers["lang"] == "tr"
    assert body_of(requests[0]) == {
        "searchParams": {"withFreeText": "kardiyoloji"},
        "orderParams": ["slot"],
        "currentPage": 1,
    }


def test_api_version_v4_changes_only_the_base_url() -> None:
    transport, requests = recording_transport(_ok)
    client = BulutklinikClient(
        environment="test", api_version="v4", partner_token="PT", transport=transport
    )

    client.doctors.branches()

    assert str(requests[0].url) == "https://apitest.bulutklinik.com/api/v4/outher/branches"


def test_missing_token_fails_before_dispatch() -> None:
    dispatched = {"n": 0}

    def responder(_: httpx.Request) -> httpx.Response:
        dispatched["n"] += 1
        return _ok(_)

    transport, _requests = recording_transport(responder)
    client = BulutklinikClient(environment="test", transport=transport)

    with pytest.raises(AuthenticationError):
        client.doctors.branches()
    assert dispatched["n"] == 0


def test_partner_token_and_token_store_together_is_rejected() -> None:
    with pytest.raises(ValueError, match="not both"):
        BulutklinikClient(partner_token="PT", token_store=InMemoryTokenStore("OTHER"))


def test_token_is_read_from_the_store_on_every_call() -> None:
    store = InMemoryTokenStore("first")
    transport, requests = recording_transport(_ok)
    client = BulutklinikClient(environment="test", transport=transport, token_store=store)

    client.doctors.branches()
    store.set_token("second")
    client.doctors.branches()

    assert [r.headers["Authorization"] for r in requests] == ["Bearer first", "Bearer second"]


def test_request_escape_hatch_defaults_to_partner() -> None:
    client, requests = client_with(_ok)

    res = client.request("GET", "/outher/customEndpoint")

    assert res == {"ok": True}
    assert str(requests[0].url) == f"{BASE}/outher/customEndpoint"
    assert requests[0].headers["Authorization"] == "Bearer PT"


def test_request_escape_hatch_public_post_body() -> None:
    client, requests = client_with(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"id": 7}})
    )

    res = client.request("POST", "/general/somePublicEndpoint", auth="public", body={"foo": "bar"})

    assert res == {"id": 7}
    assert "Authorization" not in requests[0].headers
    assert body_of(requests[0]) == {"foo": "bar"}


def test_maps_422_to_validation_error() -> None:
    client, _ = client_with(
        lambda req: httpx.Response(
            422, json={"resultType": 1, "errorType": "validation", "errorMessage": "bad"}
        )
    )
    with pytest.raises(ValidationError):
        client.doctors.branches()


def test_maps_403_to_authorization_error() -> None:
    client, _ = client_with(lambda req: httpx.Response(403, json={"resultType": 1}))
    with pytest.raises(AuthorizationError):
        client.doctors.branches()


def test_maps_404_and_429() -> None:
    client, _ = client_with(lambda req: httpx.Response(404, json={"resultType": 1}))
    with pytest.raises(NotFoundError):
        client.doctors.branches()

    rate, _ = client_with(
        lambda req: httpx.Response(429, json={"resultType": 1}, headers={"retry-after": "30"})
    )
    with pytest.raises(RateLimitError) as excinfo:
        rate.doctors.branches()
    assert excinfo.value.retry_after == 30


def test_numeric_error_type_does_not_crash() -> None:
    client, _ = client_with(
        lambda req: httpx.Response(
            404, json={"resultType": 1, "errorType": 1, "errorMessage": "Bilinmeyen bir hata."}
        )
    )
    with pytest.raises(NotFoundError):
        client.doctors.branches()


def test_expired_token_is_surfaced_without_retrying() -> None:
    attempts = {"n": 0}

    def responder(_: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(401, json={"resultType": 4, "errorMessage": "You must log in."})

    store = InMemoryTokenStore("expired")
    client, _ = client_with(responder, partner_token=None, token_store=store)

    with pytest.raises(AuthenticationError, match="cannot refresh it"):
        client.measures.last(REF)

    assert attempts["n"] == 1
    # An expired token is kept: the caller may want to inspect it while
    # installing the replacement. Only a revoked one is cleared.
    assert store.get_token() == "expired"


def test_logout_clears_the_store() -> None:
    store = InMemoryTokenStore("revoked")
    client, _ = client_with(
        lambda req: httpx.Response(200, json={"resultType": 2, "errorMessage": "logged out"}),
        partner_token=None,
        token_store=store,
    )

    with pytest.raises(AuthenticationError):
        client.measures.last(REF)
    assert store.get_token() is None


def test_network_failure_is_wrapped() -> None:
    def boom(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client, _ = client_with(boom)
    with pytest.raises(TransportError):
        client.doctors.branches()

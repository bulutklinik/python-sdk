from __future__ import annotations

import httpx
import pytest

from bulutklinik import (
    AuthenticationError,
    BulutklinikClient,
    InMemoryTokenStore,
    NotFoundError,
    RateLimitError,
    TransportError,
    ValidationError,
)
from helpers import body_of, recording_transport


def test_unwraps_data_and_sends_headers() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"searchedDoctors": []}})
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    )

    res = client.doctors.quick_search("kardiyo")

    assert res == {"searchedDoctors": []}
    req = requests[0]
    assert str(req.url) == "https://apitest.bulutklinik.com/api/v3/patients/quickSearch"
    assert req.headers["Authorization"] == "Bearer abc"
    assert req.headers["lang"] == "tr"
    assert body_of(req) == {"searchText": "kardiyo", "listType": None, "location": None}


def test_maps_422_to_validation() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(422, json={"resultType": 1, "errorType": "validation"})
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("a")
    )
    with pytest.raises(ValidationError):
        client.doctors.branches()


def test_maps_numeric_error_type_404() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(
            404, json={"resultType": 1, "errorType": 1, "errorMessage": "Bilinmeyen"}
        )
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("a")
    )
    with pytest.raises(NotFoundError):
        client.doctors.quick_search("kardiyo")


def test_maps_429_with_retry_after() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(429, headers={"Retry-After": "30"}, json={"resultType": 1})
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("a")
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.doctors.branches()
    assert exc_info.value.retry_after == 30


def test_refreshes_once_then_retries() -> None:
    state = {"data_calls": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/refreshApi"):
            return httpx.Response(
                200,
                json={"resultType": 0, "data": {"access_token": "new", "refresh_token": "newr"}},
            )
        state["data_calls"] += 1
        if state["data_calls"] == 1:
            return httpx.Response(401, json={"resultType": 4})
        return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})

    transport, requests = recording_transport(responder)
    store = InMemoryTokenStore("old", "r")
    client = BulutklinikClient(
        environment="test", client_id="c", client_secret="s", transport=transport, token_store=store
    )

    res = client.measures.last()

    assert res == {"ok": True}
    assert store.get_access_token() == "new"
    assert requests[-1].headers["Authorization"] == "Bearer new"


def test_logout_clears_store() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 2, "errorMessage": "logged out"})
    )
    store = InMemoryTokenStore("a", "r")
    client = BulutklinikClient(environment="test", transport=transport, token_store=store)

    with pytest.raises(AuthenticationError):
        client.measures.last()
    assert store.get_access_token() is None


def test_wraps_network_errors() -> None:
    def responder(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport, _ = recording_transport(responder)
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("a")
    )
    with pytest.raises(TransportError):
        client.doctors.branches()


def test_measure_path_and_partner_token() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": None})
    )
    client = BulutklinikClient(
        environment="test",
        partner_token="PT",
        transport=transport,
        token_store=InMemoryTokenStore("a"),
    )

    client.measures.list("glucose", 1, 0)
    assert (
        str(requests[0].url)
        == "https://apitest.bulutklinik.com/api/v3/patients/userMeasuresList/glucose/1/0"
    )

    client.measures.partner_health_information(
        phone_number="5551112233",
        data=[{"type": "pulse", "date_time": "2026-06-17 09:00", "pulse": 72}],
    )
    assert requests[-1].headers["Authorization"] == "Bearer PT"

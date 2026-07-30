from __future__ import annotations

import httpx
import pytest

from bulutklinik import (
    AsyncBulutklinikClient,
    AuthenticationError,
    InMemoryTokenStore,
    NotFoundError,
)
from helpers import body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"

REF = {"identityNumber": "12345678901"}


def _ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})


async def test_async_unwraps_and_sends_headers() -> None:
    transport, requests = recording_transport(_ok)
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, partner_token="PT"
    ) as client:
        res = await client.measures.last(REF)

    assert res == {"ok": True}
    assert requests[0].headers["Authorization"] == "Bearer PT"
    assert str(requests[0].url) == f"{BASE}/outher/lastMeasures"


async def test_async_expired_token_without_a_refresh_token_is_not_retried() -> None:
    attempts = {"n": 0}

    def responder(_: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(401, json={"resultType": 4})

    transport, _requests = recording_transport(responder)
    store = InMemoryTokenStore("expired")  # access token only — nothing to refresh with
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=store
    ) as client:
        with pytest.raises(AuthenticationError, match="could not be refreshed"):
            await client.measures.last(REF)

    assert attempts["n"] == 1
    assert store.get_token() == "expired"


async def test_async_refreshes_once_then_retries() -> None:
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

    transport, _requests = recording_transport(responder)
    store = InMemoryTokenStore("AT", "RT")
    async with AsyncBulutklinikClient(
        environment="test",
        transport=transport,
        token_store=store,
        client_id="cid",
        client_secret="csecret",
    ) as client:
        assert await client.measures.last(REF) == {"ok": True}

    assert store.get_token() == "AT2"


async def test_async_auth_connect_stores_tokens() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200, json={"resultType": 0, "data": {"access_token": "AT", "refresh_token": "RT"}}
        )
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, client_id="cid", client_secret="csecret"
    ) as client:
        result = await client.auth.connect("svc", "p")
        assert result.two_factor_required is False
        assert client.token_store.get_token() == "AT"

    assert str(requests[0].url) == f"{BASE}/general/connectApi"


async def test_async_request_escape_hatch_defaults_to_partner() -> None:
    transport, requests = recording_transport(_ok)
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, partner_token="PT"
    ) as client:
        res = await client.request("GET", "/outher/customEndpoint")

    assert res == {"ok": True}
    req = requests[0]
    assert str(req.url) == f"{BASE}/outher/customEndpoint"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer PT"


async def test_async_request_escape_hatch_public_post_body() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"id": 7}})
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, partner_token="PT"
    ) as client:
        res = await client.request(
            "POST", "/general/somePublicEndpoint", auth="public", body={"foo": "bar"}
        )

    assert res == {"id": 7}
    req = requests[0]
    assert req.method == "POST"
    assert "Authorization" not in req.headers
    assert body_of(req) == {"foo": "bar"}


async def test_async_error_mapping() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(404, json={"resultType": 1, "errorType": 1})
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, partner_token="PT"
    ) as client:
        with pytest.raises(NotFoundError):
            await client.doctors.branches()


async def test_async_surface_matches_the_sync_one() -> None:
    """The async mirror must not drift: same groups, same method names, same paths."""
    transport, requests = recording_transport(_ok)
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, partner_token="PT"
    ) as client:
        await client.doctors.locations()
        await client.slots.schedule(7, schedule_date="2026-08-01")
        await client.appointments.check_doctor(2, 0)
        await client.laboratory.catalog()
        await client.diets.list(REF)
        await client.measures.graph(REF, "weight", 3)

    assert [str(r.url) for r in requests] == [
        f"{BASE}/outher/locations",
        f"{BASE}/outher/doctorSlots",
        f"{BASE}/outher/checkDoctor",
        f"{BASE}/outher/laboratoryCatalog",
        f"{BASE}/outher/dietLists",
        f"{BASE}/outher/measuresGraph/weight/3",
    ]

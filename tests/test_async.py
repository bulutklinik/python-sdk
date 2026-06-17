from __future__ import annotations

import httpx
import pytest

from bulutklinik import AsyncBulutklinikClient, InMemoryTokenStore, NotFoundError
from helpers import recording_transport


async def test_async_unwraps_and_sends_headers() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        res = await client.measures.last()

    assert res == {"ok": True}
    assert requests[0].headers["Authorization"] == "Bearer abc"


async def test_async_refresh_and_retry() -> None:
    state = {"n": 0}

    def responder(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/general/refreshApi"):
            return httpx.Response(
                200, json={"resultType": 0, "data": {"access_token": "new", "refresh_token": "r2"}}
            )
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(401, json={"resultType": 4})
        return httpx.Response(200, json={"resultType": 0, "data": {"ok": True}})

    transport, _ = recording_transport(responder)
    store = InMemoryTokenStore("old", "r")
    async with AsyncBulutklinikClient(
        environment="test", client_id="c", client_secret="s", transport=transport, token_store=store
    ) as client:
        res = await client.measures.last()

    assert res == {"ok": True}
    assert store.get_access_token() == "new"


async def test_async_error_mapping() -> None:
    transport, _ = recording_transport(
        lambda req: httpx.Response(404, json={"resultType": 1, "errorType": 1})
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("a")
    ) as client:
        with pytest.raises(NotFoundError):
            await client.doctors.quick_search("x")

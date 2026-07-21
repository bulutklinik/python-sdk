from __future__ import annotations

import httpx

from bulutklinik import AsyncBulutklinikClient, BulutklinikClient, InMemoryTokenStore
from helpers import body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"


def _ok(data: object) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    return recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": data})
    )


def _sync_client(transport: httpx.MockTransport) -> BulutklinikClient:
    return BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    )


# --- laboratory (sync) ---


def test_lab_results_omits_page_segment_when_none() -> None:
    transport, requests = _ok({"foundTestsCount": 0, "foundTests": []})
    client = _sync_client(transport)

    client.laboratory.results()

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/userLabTestList"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"


def test_lab_results_includes_page_segment() -> None:
    transport, requests = _ok({"foundTestsCount": 0, "foundTests": []})
    client = _sync_client(transport)

    client.laboratory.results(3)

    assert str(requests[0].url) == f"{BASE}/patients/userLabTestList/3"
    assert requests[0].method == "GET"


def test_lab_result_detail_interpolates_string_id_verbatim() -> None:
    transport, requests = _ok({"id": "4821-lab", "test_name": "Hemogram"})
    client = _sync_client(transport)

    client.laboratory.result_detail("4821-lab")

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/userLabTestDetail/4821-lab"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"


def test_lab_catalog() -> None:
    transport, requests = _ok({"test_groups": []})
    client = _sync_client(transport)

    client.laboratory.catalog()

    assert str(requests[0].url) == f"{BASE}/patients/allLaboratoryTests"
    assert requests[0].method == "GET"


def test_lab_catalog_detail() -> None:
    transport, requests = _ok({"id": 7, "name": "Grup"})
    client = _sync_client(transport)

    client.laboratory.catalog_detail(7)

    assert str(requests[0].url) == f"{BASE}/patients/laboratoryTestDetail/7"
    assert requests[0].method == "GET"


def test_lab_order_posts_required_body() -> None:
    transport, requests = _ok({"preOrderId": 99})
    client = _sync_client(transport)

    res = client.laboratory.order(12, 34, 56)

    assert res == {"preOrderId": 99}
    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/addNewLaboratoryTest"
    assert req.method == "POST"
    assert req.headers["Authorization"] == "Bearer abc"
    assert body_of(req) == {"testId": 12, "addressId": 34, "laboratoryId": 56}


# --- diets (sync) ---


def test_diet_list_omits_page_segment_when_none() -> None:
    transport, requests = _ok({"foundDietsCount": 0, "foundDiets": []})
    client = _sync_client(transport)

    client.diets.list()

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/dietLists"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"


def test_diet_list_includes_page_segment() -> None:
    transport, requests = _ok({"foundDietsCount": 0, "foundDiets": []})
    client = _sync_client(transport)

    client.diets.list(2)

    assert str(requests[0].url) == f"{BASE}/patients/dietLists/2"
    assert requests[0].method == "GET"


def test_diet_detail() -> None:
    transport, requests = _ok([{"time": "Sabah", "meals": []}])
    client = _sync_client(transport)

    client.diets.detail(55)

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/diet/55"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"


# --- laboratory (async) ---


async def test_async_lab_results_omits_page_segment_when_none() -> None:
    transport, requests = _ok({"foundTestsCount": 0, "foundTests": []})
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        await client.laboratory.results()

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/userLabTestList"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"


async def test_async_lab_results_includes_page_segment() -> None:
    transport, requests = _ok({"foundTestsCount": 0, "foundTests": []})
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        await client.laboratory.results(4)

    assert str(requests[0].url) == f"{BASE}/patients/userLabTestList/4"


async def test_async_lab_result_detail_string_id() -> None:
    transport, requests = _ok({"id": "4821-lab"})
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        await client.laboratory.result_detail("4821-lab")

    assert str(requests[0].url) == f"{BASE}/patients/userLabTestDetail/4821-lab"


async def test_async_lab_order_posts_required_body() -> None:
    transport, requests = _ok({"preOrderId": 1})
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        res = await client.laboratory.order(12, 34, 56)

    assert res == {"preOrderId": 1}
    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/addNewLaboratoryTest"
    assert req.method == "POST"
    assert req.headers["Authorization"] == "Bearer abc"
    assert body_of(req) == {"testId": 12, "addressId": 34, "laboratoryId": 56}


# --- diets (async) ---


async def test_async_diet_list_includes_page_segment() -> None:
    transport, requests = _ok({"foundDietsCount": 0, "foundDiets": []})
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        await client.diets.list(2)

    assert str(requests[0].url) == f"{BASE}/patients/dietLists/2"
    assert requests[0].method == "GET"


async def test_async_diet_detail() -> None:
    transport, requests = _ok([{"time": "Sabah", "meals": []}])
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        await client.diets.detail(55)

    req = requests[0]
    assert str(req.url) == f"{BASE}/patients/diet/55"
    assert req.method == "GET"
    assert req.headers["Authorization"] == "Bearer abc"

from __future__ import annotations

import httpx

from bulutklinik import AsyncBulutklinikClient, BulutklinikClient, InMemoryTokenStore
from helpers import body_of, recording_transport


def test_skin_analyze_posts_images_with_bearer() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200,
            json={
                "resultType": 0,
                "data": {"status": [{"id": 1, "label": "nevus", "case_detail": "blob"}]},
            },
        )
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    )

    res = client.skin.analyze([{"image": "BASE64", "branch_id": 42}])

    assert res == {"status": [{"id": 1, "label": "nevus", "case_detail": "blob"}]}
    req = requests[0]
    assert str(req.url) == "https://apitest.bulutklinik.com/api/v3/patients/imageCheck"
    assert req.method == "POST"
    assert req.headers["Authorization"] == "Bearer abc"
    assert body_of(req) == {"images": [{"image": "BASE64", "branch_id": 42}]}


def test_meals_analyze_maps_snake_case_body_with_optionals() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200, json={"resultType": 0, "data": {"status": {"comment": "{}"}}}
        )
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    )

    client.meals.analyze("BASE64", "custom", "lunch", portion_grams=300, note="az yağlı")

    req = requests[0]
    assert str(req.url) == "https://apitest.bulutklinik.com/api/v3/patients/imageAnalyzeMeal"
    assert req.method == "POST"
    assert req.headers["Authorization"] == "Bearer abc"
    assert body_of(req) == {
        "image": "BASE64",
        "portion_size": "custom",
        "meal_type": "lunch",
        "portion_grams": 300,
        "note": "az yağlı",
    }


def test_meals_analyze_omits_optionals_when_not_provided() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200, json={"resultType": 0, "data": {"status": {"comment": "{}"}}}
        )
    )
    client = BulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    )

    client.meals.analyze("BASE64", "medium", "snack")

    assert body_of(requests[0]) == {
        "image": "BASE64",
        "portion_size": "medium",
        "meal_type": "snack",
    }


async def test_async_skin_analyze_posts_images() -> None:
    transport, requests = recording_transport(
        lambda req: httpx.Response(
            200, json={"resultType": 0, "data": {"status": [{"id": 1, "label": "nevus"}]}}
        )
    )
    async with AsyncBulutklinikClient(
        environment="test", transport=transport, token_store=InMemoryTokenStore("abc")
    ) as client:
        res = await client.skin.analyze([{"image": "BASE64"}])

    assert res == {"status": [{"id": 1, "label": "nevus"}]}
    req = requests[0]
    assert str(req.url) == "https://apitest.bulutklinik.com/api/v3/patients/imageCheck"
    assert body_of(req) == {"images": [{"image": "BASE64"}]}

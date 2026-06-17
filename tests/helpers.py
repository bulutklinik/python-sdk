from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

Responder = Callable[[httpx.Request], httpx.Response]


def recording_transport(responder: Responder) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """A MockTransport that records every request and delegates to `responder`."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return responder(request)

    return httpx.MockTransport(handler), requests


def body_of(request: httpx.Request) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(request.content)
    return data

from __future__ import annotations

from types import TracebackType

import httpx

from . import aresources, resources
from ._http import AsyncHttpClient, HttpClient
from .config import Environment, resolve_base_url
from .tokens import InMemoryTokenStore, TokenStore


class BulutklinikClient:
    """Synchronous Bulutklinik API client. Construct once and reuse; service
    groups are exposed as attributes. Usable as a context manager.

    Example::

        with BulutklinikClient(environment="test", client_id="…", client_secret="…") as client:
            client.auth.connect("patient@example.com", "•••", "email")
            result = client.doctors.quick_search("kardiyo")
    """

    def __init__(
        self,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        base_url: str | None = None,
        lang: str = "tr",
        client_id: str | None = None,
        client_secret: str | None = None,
        partner_token: str | None = None,
        token_store: TokenStore | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        store: TokenStore = token_store or InMemoryTokenStore()
        client = httpx.Client(timeout=timeout, transport=transport)
        self._http = HttpClient(
            base_url=resolve_base_url(environment, base_url),
            lang=lang,
            client_id=client_id,
            client_secret=client_secret,
            partner_token=partner_token,
            token_store=store,
            client=client,
        )
        self.token_store = store
        self.auth = resources.AuthResource(self._http)
        self.doctors = resources.DoctorsResource(self._http)
        self.slots = resources.SlotsResource(self._http)
        self.appointments = resources.AppointmentsResource(self._http)
        self.payments = resources.PaymentsResource(self._http)
        self.measures = resources.MeasuresResource(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> BulutklinikClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncBulutklinikClient:
    """Asynchronous Bulutklinik API client. Usable as an async context manager."""

    def __init__(
        self,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        base_url: str | None = None,
        lang: str = "tr",
        client_id: str | None = None,
        client_secret: str | None = None,
        partner_token: str | None = None,
        token_store: TokenStore | None = None,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        store: TokenStore = token_store or InMemoryTokenStore()
        client = httpx.AsyncClient(timeout=timeout, transport=transport)
        self._http = AsyncHttpClient(
            base_url=resolve_base_url(environment, base_url),
            lang=lang,
            client_id=client_id,
            client_secret=client_secret,
            partner_token=partner_token,
            token_store=store,
            client=client,
        )
        self.token_store = store
        self.auth = aresources.AsyncAuthResource(self._http)
        self.doctors = aresources.AsyncDoctorsResource(self._http)
        self.slots = aresources.AsyncSlotsResource(self._http)
        self.appointments = aresources.AsyncAppointmentsResource(self._http)
        self.payments = aresources.AsyncPaymentsResource(self._http)
        self.measures = aresources.AsyncMeasuresResource(self._http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncBulutklinikClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

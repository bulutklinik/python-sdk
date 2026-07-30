from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx

from . import aresources, resources
from ._http import AsyncHttpClient, HttpClient
from ._spec import AuthMode, RequestSpec
from .config import ApiVersion, Environment, resolve_base_url
from .tokens import InMemoryTokenStore, TokenStore

_BOTH_CREDENTIALS = (
    "Pass either partner_token or token_store, not both. Seed your own store "
    "with the token if you need custom persistence."
)


def _resolve_store(partner_token: str | None, token_store: TokenStore | None) -> TokenStore:
    # Either the literal or the store is the source of truth for the credential.
    # Guessing which one the caller meant is how credential bugs get shipped.
    if partner_token is not None and token_store is not None:
        raise ValueError(_BOTH_CREDENTIALS)
    return token_store if token_store is not None else InMemoryTokenStore(partner_token)


class BulutklinikClient:
    """Synchronous Bulutklinik partner API client. Construct once and reuse;
    service groups are exposed as attributes. Usable as a context manager.

    Every call runs on the company-scoped ``/outher`` surface with the partner
    token issued for your integration: you act on the patients of **your own
    company**, and the patient is named inline on each request — there is no
    login and no session.

    Example::

        with BulutklinikClient(environment="test", partner_token="…") as client:
            branches = client.doctors.branches()
            latest = client.measures.last({"identityNumber": "12345678901"})
    """

    def __init__(
        self,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        api_version: ApiVersion | str = ApiVersion.V3,
        base_url: str | None = None,
        lang: str = "tr",
        partner_token: str | None = None,
        token_store: TokenStore | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        store = _resolve_store(partner_token, token_store)
        client = httpx.Client(timeout=timeout, transport=transport)
        self._http = HttpClient(
            base_url=resolve_base_url(environment, base_url, api_version),
            lang=lang,
            token_store=store,
            client=client,
        )
        #: Write a newly issued partner token here to rotate the credential
        #: without rebuilding the client.
        self.token_store = store
        self.doctors = resources.DoctorsResource(self._http)
        self.slots = resources.SlotsResource(self._http)
        self.appointments = resources.AppointmentsResource(self._http)
        self.measures = resources.MeasuresResource(self._http)
        self.laboratory = resources.LaboratoryResource(self._http)
        self.diets = resources.DietsResource(self._http)

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: AuthMode = "partner",
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Escape hatch: call any Bulutklinik API endpoint that does not yet have
        a typed resource method.

        The request still goes through the shared transport, so default headers,
        the chosen ``auth`` mode (``"partner"`` by default), envelope unwrapping
        and the typed error hierarchy all apply. Returns the unwrapped ``data``
        payload. Prefer a typed resource method when one exists.

        :param method: HTTP method (``"GET"`` / ``"POST"`` / ``"PUT"`` / ``"DELETE"``).
        :param path: Path relative to the configured base URL, e.g. ``"/outher/branches"``.
        :param auth: Auth mode — ``"partner"`` (default) / ``"public"``.
        :param body: Optional JSON payload (a dict); omitted on ``GET``.

        Example::

            branches = client.request("GET", "/outher/branches")
            # "public" reaches unauthenticated endpoints outside the partner surface
            config = client.request("GET", "/general/getConfig", auth="public")
        """
        return self._http.send(RequestSpec(method, path, auth, body))

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
    """Asynchronous Bulutklinik partner API client. Usable as an async context
    manager. Same surface and semantics as :class:`BulutklinikClient`."""

    def __init__(
        self,
        *,
        environment: Environment | str = Environment.PRODUCTION,
        api_version: ApiVersion | str = ApiVersion.V3,
        base_url: str | None = None,
        lang: str = "tr",
        partner_token: str | None = None,
        token_store: TokenStore | None = None,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        store = _resolve_store(partner_token, token_store)
        client = httpx.AsyncClient(timeout=timeout, transport=transport)
        self._http = AsyncHttpClient(
            base_url=resolve_base_url(environment, base_url, api_version),
            lang=lang,
            token_store=store,
            client=client,
        )
        self.token_store = store
        self.doctors = aresources.AsyncDoctorsResource(self._http)
        self.slots = aresources.AsyncSlotsResource(self._http)
        self.appointments = aresources.AsyncAppointmentsResource(self._http)
        self.measures = aresources.AsyncMeasuresResource(self._http)
        self.laboratory = aresources.AsyncLaboratoryResource(self._http)
        self.diets = aresources.AsyncDietsResource(self._http)

    async def request(
        self,
        method: str,
        path: str,
        *,
        auth: AuthMode = "partner",
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Escape hatch — see :meth:`BulutklinikClient.request`.

        Example::

            branches = await client.request("GET", "/outher/branches")
        """
        return await self._http.send(RequestSpec(method, path, auth, body))

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

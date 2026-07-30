from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    PRODUCTION = "production"
    TEST = "test"
    LOCAL = "local"


class ApiVersion(str, Enum):
    """API version segment. The ``/outher`` surface is route-for-route identical
    on both, so switching is configuration rather than a code change."""

    V3 = "v3"
    V4 = "v4"


#: API roots per environment. The base URL is ``<root>/<api_version>``.
API_ROOTS: dict[Environment, str] = {
    Environment.PRODUCTION: "https://api.bulutklinik.com/api",
    Environment.TEST: "https://apitest.bulutklinik.com/api",
    Environment.LOCAL: "https://api-bulutklinik.test/api",
}


def resolve_base_url(
    environment: Environment | str,
    base_url: str | None,
    api_version: ApiVersion | str = ApiVersion.V3,
) -> str:
    if base_url is not None:
        return base_url.rstrip("/")
    env = Environment(environment) if isinstance(environment, str) else environment
    version = ApiVersion(api_version) if isinstance(api_version, str) else api_version
    return f"{API_ROOTS[env].rstrip('/')}/{version.value}"

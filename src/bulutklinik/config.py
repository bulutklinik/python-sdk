from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    PRODUCTION = "production"
    TEST = "test"
    LOCAL = "local"


_BASE_URLS: dict[Environment, str] = {
    Environment.PRODUCTION: "https://api.bulutklinik.com/api/v3",
    Environment.TEST: "https://apitest.bulutklinik.com/api/v3",
    Environment.LOCAL: "https://api-bulutklinik.test/api/v3",
}


def resolve_base_url(environment: Environment | str, base_url: str | None) -> str:
    if base_url is not None:
        return base_url.rstrip("/")
    env = Environment(environment) if isinstance(environment, str) else environment
    return _BASE_URLS[env].rstrip("/")

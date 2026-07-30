from __future__ import annotations

from typing import Any


class BulutklinikError(Exception):
    """Base class for every error raised by the SDK."""


class TransportError(BulutklinikError):
    """Network failure, timeout, DNS or TLS error — no usable HTTP response."""


class ApiError(BulutklinikError):
    """An HTTP response was received but the call was not successful."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int,
        result_type: int | None = None,
        error_type: str | int | None = None,
        data: Any = None,
        method: str | None = None,
        path: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.result_type = result_type
        self.error_type = error_type
        self.data = data
        self.method = method
        self.path = path
        self.retry_after = retry_after


class ValidationError(ApiError):
    """422, or an envelope with a string error_type of "validation"."""


class AuthenticationError(ApiError):
    """401, a revoked token (result_type 2), or an expired one (result_type 4)."""


class AuthorizationError(ApiError):
    """403 — the token authenticated but is not permitted. Either it lacks the
    ``apiouther`` scope or it resolves to a user with no company. The company
    boundary comes from the token, never from request input, so retrying with
    different body parameters will not help."""


class NotFoundError(ApiError):
    """404."""


class RateLimitError(ApiError):
    """429 — throttled. The seconds-to-wait are on ``retry_after`` when present."""


def create_api_error(
    message: str,
    *,
    http_status: int,
    result_type: int | None,
    error_type: str | int | None,
    data: Any,
    method: str,
    path: str,
    retry_after: int | None,
) -> ApiError:
    """Map an API failure to the most specific error type."""
    kwargs: dict[str, Any] = {
        "http_status": http_status,
        "result_type": result_type,
        "error_type": error_type,
        "data": data,
        "method": method,
        "path": path,
        "retry_after": retry_after,
    }

    if result_type == 2:
        return AuthenticationError(message, **kwargs)
    # `result_type 4` used to trigger a silent refresh. On the partner surface
    # there is nothing to refresh, so say what the caller actually has to do.
    if result_type == 4:
        return AuthenticationError(
            f"{message} The partner token is expired or invalid — install a newly "
            "issued token; the SDK cannot refresh it.",
            **kwargs,
        )
    if (isinstance(error_type, str) and error_type.lower() == "validation") or http_status == 422:
        return ValidationError(message, **kwargs)

    mapping: dict[int, type[ApiError]] = {
        401: AuthenticationError,
        403: AuthorizationError,
        404: NotFoundError,
        429: RateLimitError,
    }
    return mapping.get(http_status, ApiError)(message, **kwargs)

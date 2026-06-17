from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginResult:
    """Result of ``auth.connect``. When ``two_factor_required`` is True, pass
    ``two_factor_response`` (with the SMS code) to ``connect_with_two_factor``."""

    two_factor_required: bool
    two_factor_response: str | None = None

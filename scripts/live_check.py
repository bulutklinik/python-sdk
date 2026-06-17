"""Live smoke test against the Bulutklinik test environment (apitest).

Read-only flow; each step is independent. Credentials default to the repo's
Postman collection (test account). Run: python scripts/live_check.py
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from bulutklinik import ApiError, BulutklinikClient


def main() -> None:
    client = BulutklinikClient(
        environment="test",
        client_id=os.environ.get("BK_CLIENT_ID", "96b630b3-f62a-4e67-b33c-b58802dca5af"),
        client_secret=os.environ.get(
            "BK_CLIENT_SECRET", "KPgmEavOSomEl8mQu1ZZMoyZaVXBSuuKxrrzMAkX"
        ),
    )
    results: list[tuple[str, bool]] = []

    def step(name: str, fn: Callable[[], Any]) -> Any:
        try:
            value = fn()
            print(f"OK  {name}")
            results.append((name, True))
            return value
        except Exception as exc:  # noqa: BLE001 - smoke test reports every failure
            detail = ""
            if isinstance(exc, ApiError):
                detail = (
                    f" [http={exc.http_status} resultType={exc.result_type}"
                    f" errorType={exc.error_type}]"
                )
            print(f"ERR {name}: {type(exc).__name__} - {exc}{detail}")
            results.append((name, False))
            return None

    login = step(
        "auth.connect",
        lambda: client.auth.connect(
            os.environ.get("BK_USERNAME", "hackathon@bulutklinik.test"),
            os.environ.get("BK_PASSWORD", "Hackathon2026"),
            "email",
        ),
    )
    stored = client.token_store.get_access_token() is not None
    two_factor = getattr(login, "two_factor_required", None)
    print(f"    twoFactorRequired={two_factor} accessTokenStored={stored}")

    branches = step("doctors.branches", client.doctors.branches)
    print(f"    branches={len(branches) if isinstance(branches, list) else 'n/a'}")

    locations = step("doctors.locations", client.doctors.locations)
    print(f"    locations={len(locations) if isinstance(locations, list) else 'n/a'}")

    step("doctors.quickSearch", lambda: client.doctors.quick_search("kardiyo", "interview"))

    found = step(
        "doctors.search",
        lambda: client.doctors.search(
            search_params={"withFreeText": "kardiyoloji"},
            order_params=["slot"],
            other_params=["isInterviewable"],
            current_page=1,
            per_page_limit=10,
        ),
    )
    count = found.get("foundDoctorsCount") if isinstance(found, dict) else "n/a"
    print(f"    foundDoctorsCount={count}")

    doctor_id = int(os.environ.get("BK_DOCTOR_ID", "8282"))
    detail = step("doctors.detail", lambda: client.doctors.detail(doctor_id))
    print(f"    detailKeys={len(detail) if isinstance(detail, dict) else 'n/a'}")

    slots = step("slots.schedule", lambda: client.slots.schedule(doctor_id, "interview"))
    print(f"    slotDays={len(slots) if isinstance(slots, dict) else 'n/a'}")

    last = step("measures.last", client.measures.last)
    print(f"    measuresLastKeys={len(last) if isinstance(last, dict) else 'n/a'}")

    step("auth.disconnect", client.auth.disconnect)
    client.close()

    passed = sum(1 for _, ok in results if ok)
    print(f"\nSUMMARY: {passed}/{len(results)} steps OK")
    for name, ok in results:
        print(f"  {'OK ' if ok else 'ERR'} {name}")


if __name__ == "__main__":
    main()

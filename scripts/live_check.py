"""Live smoke test against the Bulutklinik test environment (apitest).

Read-only flow; each step is independent. Needs a partner token issued for a test
company with the `apiouther` scope:

    BK_PARTNER_TOKEN=... python scripts/live_check.py

Unlike the patient surface there is no shared test credential — the token is
per-integration. Steps that touch a patient need one that exists inside the
token's own company; set BK_PATIENT_TCKN or BK_PATIENT_PHONE to run them.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

from bulutklinik import ApiError, BulutklinikClient


def main() -> None:
    partner_token = os.environ.get("BK_PARTNER_TOKEN")
    if not partner_token:
        print("BK_PARTNER_TOKEN is required.", file=sys.stderr)
        raise SystemExit(2)

    client = BulutklinikClient(
        environment="test",
        api_version=os.environ.get("BK_API_VERSION", "v3"),
        partner_token=partner_token,
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

    # --- Scope-only steps: prove the token and base URL without any patient.
    branches = step("doctors.branches", client.doctors.branches)
    print(f"    branches={len(branches) if isinstance(branches, list) else 'n/a'}")

    locations = step("doctors.locations", client.doctors.locations)
    print(f"    locations={len(locations) if isinstance(locations, list) else 'n/a'}")

    catalog = step("laboratory.catalog", client.laboratory.catalog)
    print(f"    catalog={len(catalog) if isinstance(catalog, list) else 'n/a'}")

    found = step(
        "doctors.search",
        lambda: client.doctors.search(
            search_params={"withFreeText": "kardiyoloji"},
            current_page=1,
            order_params=["slot"],
        ),
    )
    count = found.get("foundDoctorsCount") if isinstance(found, dict) else "n/a"
    print(f"    foundDoctorsCount={count}")

    doctor_id = int(os.environ.get("BK_DOCTOR_ID", "8282"))
    detail = step("doctors.detail", lambda: client.doctors.detail(doctor_id))
    print(f"    detailKeys={len(detail) if isinstance(detail, dict) else 'n/a'}")

    step("appointments.checkDoctor", lambda: client.appointments.check_doctor(doctor_id, 0))

    slots = step("slots.schedule", lambda: client.slots.schedule(doctor_id))
    print(f"    slotDays={len(slots) if isinstance(slots, dict) else 'n/a'}")

    # --- Patient-scoped steps. A TCKN that works on the patient surface will not
    #     necessarily resolve here: the patient must exist in the token's company.
    patient: dict[str, str] | None = None
    if tckn := os.environ.get("BK_PATIENT_TCKN"):
        patient = {"identityNumber": tckn}
    elif phone := os.environ.get("BK_PATIENT_PHONE"):
        patient = {"phoneNumber": phone}

    if patient is not None:
        last = step("measures.last", lambda: client.measures.last(patient))
        print(f"    measuresLastKeys={len(last) if isinstance(last, dict) else 'n/a'}")

        step("diets.list", lambda: client.diets.list(patient))
        step("laboratory.results", lambda: client.laboratory.results(patient))
    else:
        print("--  skipped patient-scoped steps (set BK_PATIENT_TCKN or BK_PATIENT_PHONE)")

    client.close()

    passed = sum(1 for _, ok in results if ok)
    print(f"\nSUMMARY: {passed}/{len(results)} steps OK")
    for name, ok in results:
        print(f"  {'OK ' if ok else 'ERR'} {name}")


if __name__ == "__main__":
    main()

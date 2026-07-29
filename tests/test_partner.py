from __future__ import annotations

import httpx
import pytest

from bulutklinik import AsyncBulutklinikClient, BulutklinikClient, InMemoryTokenStore
from helpers import body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"


def _ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"resultType": 0, "data": None})


def partner_client() -> tuple[BulutklinikClient, list[httpx.Request]]:
    """A client with BOTH a patient access token and a partner token configured.
    Partner calls must ignore the patient one."""
    transport, requests = recording_transport(_ok)
    client = BulutklinikClient(
        environment="test",
        partner_token="PT",
        transport=transport,
        token_store=InMemoryTokenStore("PATIENT"),
    )
    return client, requests


def test_sends_partner_token_never_patient_token() -> None:
    client, requests = partner_client()

    client.partner.doctors.branches()
    client.partner.measures.last({"identityNumber": "12345678901"})

    assert [r.headers.get("authorization") for r in requests] == ["Bearer PT", "Bearer PT"]


def test_patient_surface_still_uses_patient_token() -> None:
    client, requests = partner_client()

    client.doctors.branches()

    assert requests[0].headers.get("authorization") == "Bearer PATIENT"
    assert str(requests[0].url) == f"{BASE}/patients/allBranches"


def test_discovery_paths() -> None:
    client, requests = partner_client()

    client.partner.doctors.locations()
    client.partner.doctors.detail(42)
    client.partner.laboratory.catalog()
    client.partner.laboratory.catalog_detail(18246)
    client.partner.slots.schedule(7, schedule_date="2026-08-01")

    assert [str(r.url) for r in requests] == [
        f"{BASE}/outher/locations",
        f"{BASE}/outher/doctorInfos/42",
        f"{BASE}/outher/laboratoryCatalog",
        f"{BASE}/outher/laboratoryCatalog/18246",
        f"{BASE}/outher/doctorSlots",
    ]


def test_patient_reference_travels_in_the_body_not_the_path() -> None:
    client, requests = partner_client()
    patient = {"identityNumber": "12345678901"}

    client.partner.diets.list(patient, 2)
    client.partner.measures.list(patient, "glucose", 1, 0)
    client.partner.laboratory.results(patient)

    # The identity number must never leak into a URL — it would land in access
    # logs, proxy logs and error breadcrumbs.
    for request in requests:
        assert "12345678901" not in str(request.url)

    assert str(requests[0].url) == f"{BASE}/outher/dietLists"
    assert body_of(requests[0]) == {"patient": patient, "currentPage": 2}

    assert str(requests[1].url) == f"{BASE}/outher/measuresList/glucose"
    assert body_of(requests[1]) == {"patient": patient, "currentPage": 1, "glucoseType": 0}


def test_lab_result_id_round_trips_with_its_suffix() -> None:
    client, requests = partner_client()
    patient = {"identityNumber": "12345678901"}

    client.partner.laboratory.result_detail(patient, "1234-lab")
    assert body_of(requests[0])["testId"] == "1234-lab"

    client.partner.laboratory.result_detail(patient, 1234)
    assert body_of(requests[1])["testId"] == "1234"


def test_measure_write_verbs_and_paths() -> None:
    client, requests = partner_client()
    write_patient = {"name": "Ada", "surname": "Lovelace", "phoneNumber": "+905551112233"}
    ref = {"identityNumber": "12345678901"}

    client.partner.measures.add_list(
        write_patient, [{"type": "pulse", "date_time": "2026-06-17 09:00", "pulse": 72}]
    )
    client.partner.measures.add(
        write_patient,
        "tension",
        {"date_time": "2026-06-17 09:00", "hypertension": 120, "hypotension": 80},
    )
    client.partner.measures.update(
        ref,
        "tension",
        9,
        {"date_time": "2026-06-17 10:00", "hypertension": 125, "hypotension": 85},
    )
    client.partner.measures.delete(ref, "tension", 9)

    assert [(r.method, str(r.url)) for r in requests] == [
        ("POST", f"{BASE}/outher/measures"),
        ("POST", f"{BASE}/outher/measure/tension"),
        ("PUT", f"{BASE}/outher/measure/tension"),
        ("DELETE", f"{BASE}/outher/measure/tension"),
    ]

    # Measure fields are flattened alongside `patient`, matching the server shape.
    assert body_of(requests[1]) == {
        "patient": write_patient,
        "date_time": "2026-06-17 09:00",
        "hypertension": 120,
        "hypotension": 80,
    }
    assert body_of(requests[3]) == {"patient": ref, "id": 9}


def test_appointment_lifecycle() -> None:
    client, requests = partner_client()
    user = {"name": "Ada", "surname": "Lovelace", "phoneNumber": "+905551112233"}

    client.partner.appointments.reserve(1, 2, user)
    client.partner.appointments.create("h", 5)
    client.partner.appointments.list("+905551112233")
    client.partner.appointments.cancel_without_slot({"hash": "h", "outherProcessId": 5})

    assert [(r.method, str(r.url)) for r in requests] == [
        ("POST", f"{BASE}/outher/reservation"),
        ("POST", f"{BASE}/outher/appointment"),
        ("POST", f"{BASE}/outher/appointments"),
        ("DELETE", f"{BASE}/outher/appointmentWithoutSlot"),
    ]
    assert body_of(requests[0]) == {"slotId": 1, "doctorId": 2, "user": user}


@pytest.mark.asyncio
async def test_async_partner_surface_matches_sync() -> None:
    """The async mirror must produce byte-identical requests — both surfaces call
    the same `_spec` builders, and this guards that they stay wired that way."""
    transport, requests = recording_transport(_ok)
    client = AsyncBulutklinikClient(
        environment="test",
        partner_token="PT",
        transport=transport,
        token_store=InMemoryTokenStore("PATIENT"),
    )
    patient = {"identityNumber": "12345678901"}

    await client.partner.doctors.locations()
    await client.partner.measures.list(patient, "glucose", 1, 0)
    await client.partner.laboratory.result_detail(patient, "1234-lab")
    await client.aclose()

    assert [r.headers.get("authorization") for r in requests] == ["Bearer PT"] * 3
    assert str(requests[0].url) == f"{BASE}/outher/locations"
    assert str(requests[1].url) == f"{BASE}/outher/measuresList/glucose"
    assert body_of(requests[1]) == {"patient": patient, "currentPage": 1, "glucoseType": 0}
    assert body_of(requests[2])["testId"] == "1234-lab"

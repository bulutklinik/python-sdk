from __future__ import annotations

import httpx

from bulutklinik import BulutklinikClient
from helpers import body_of, recording_transport

BASE = "https://apitest.bulutklinik.com/api/v3"

REF = {"identityNumber": "12345678901"}
WRITE_PATIENT = {"name": "Ada", "surname": "Lovelace", "phoneNumber": "+905551112233"}


def partner_client() -> tuple[BulutklinikClient, list[httpx.Request]]:
    transport, requests = recording_transport(
        lambda req: httpx.Response(200, json={"resultType": 0, "data": None})
    )
    return BulutklinikClient(environment="test", partner_token="PT", transport=transport), requests


def test_discovery_paths() -> None:
    client, requests = partner_client()

    client.doctors.branches()
    client.doctors.locations()
    client.doctors.detail(42)
    client.laboratory.catalog()
    client.laboratory.catalog_detail(18246)
    client.slots.schedule(7, schedule_date="2026-08-01")

    assert [str(r.url) for r in requests] == [
        f"{BASE}/outher/branches",
        f"{BASE}/outher/locations",
        f"{BASE}/outher/doctorInfos/42",
        f"{BASE}/outher/laboratoryCatalog",
        f"{BASE}/outher/laboratoryCatalog/18246",
        f"{BASE}/outher/doctorSlots",
    ]


def test_patient_reference_travels_in_the_body_not_the_url() -> None:
    client, requests = partner_client()

    client.diets.list(REF, 2)
    client.measures.list(REF, "glucose", 1, 0)
    client.laboratory.results(REF)

    # The identity number must never leak into a URL — it would land in access
    # logs, proxy logs and error breadcrumbs.
    for request in requests:
        assert "12345678901" not in str(request.url)

    assert str(requests[0].url) == f"{BASE}/outher/dietLists"
    assert body_of(requests[0]) == {"patient": REF, "currentPage": 2}

    assert str(requests[1].url) == f"{BASE}/outher/measuresList/glucose"
    assert body_of(requests[1]) == {"patient": REF, "currentPage": 1, "glucoseType": 0}

    assert str(requests[2].url) == f"{BASE}/outher/laboratoryResults"


def test_measures_graph_path() -> None:
    client, requests = partner_client()

    client.measures.graph({"phoneNumber": "+905551112233"}, "weight", 3)

    assert str(requests[0].url) == f"{BASE}/outher/measuresGraph/weight/3"


def test_lab_result_id_round_trips_verbatim() -> None:
    client, requests = partner_client()

    client.laboratory.result_detail(REF, "1234-lab")
    client.laboratory.result_detail(REF, 1234)

    assert body_of(requests[0])["testId"] == "1234-lab"
    assert body_of(requests[1])["testId"] == "1234"


def test_measure_write_verbs_and_paths() -> None:
    client, requests = partner_client()

    client.measures.add_list(
        WRITE_PATIENT, [{"type": "pulse", "date_time": "2026-06-17 09:00", "pulse": 72}]
    )
    client.measures.add(
        WRITE_PATIENT,
        "tension",
        {"date_time": "2026-06-17 09:00", "hypertension": 120, "hypotension": 80},
    )
    client.measures.update(
        REF, "tension", 9, {"date_time": "2026-06-17 10:00", "hypertension": 125}
    )
    client.measures.delete(REF, "tension", 9)

    assert [(r.method, str(r.url)) for r in requests] == [
        ("POST", f"{BASE}/outher/measures"),
        ("POST", f"{BASE}/outher/measure/tension"),
        ("PUT", f"{BASE}/outher/measure/tension"),
        ("DELETE", f"{BASE}/outher/measure/tension"),
    ]

    # Measure fields are flattened alongside `patient`, matching the server shape.
    assert body_of(requests[1]) == {
        "patient": WRITE_PATIENT,
        "date_time": "2026-06-17 09:00",
        "hypertension": 120,
        "hypotension": 80,
    }
    assert body_of(requests[3]) == {"patient": REF, "id": 9}


def test_appointment_lifecycle() -> None:
    client, requests = partner_client()

    client.appointments.check_doctor(2, 0)
    client.appointments.reserve(1, 2, WRITE_PATIENT, without_agreement=True)
    client.appointments.create("h", 5)
    client.appointments.list("+905551112233")
    client.appointments.cancel_without_slot({"hash": "h", "outherProcessId": 5})

    assert [(r.method, str(r.url)) for r in requests] == [
        ("POST", f"{BASE}/outher/checkDoctor"),
        ("POST", f"{BASE}/outher/reservationWithoutAgreement"),
        ("POST", f"{BASE}/outher/appointment"),
        ("POST", f"{BASE}/outher/appointments"),
        ("DELETE", f"{BASE}/outher/appointmentWithoutSlot"),
    ]
    assert body_of(requests[1]) == {"slotId": 1, "doctorId": 2, "user": WRITE_PATIENT}


def test_reserve_defaults_to_the_hand_off_flow() -> None:
    client, requests = partner_client()

    client.appointments.reserve(1, 2, WRITE_PATIENT)
    client.appointments.instant_reserve(WRITE_PATIENT)
    client.appointments.create_without_slot(
        2, "2026-08-01 09:00", "2026-08-01 09:30", WRITE_PATIENT
    )

    assert [str(r.url) for r in requests] == [
        f"{BASE}/outher/reservation",
        f"{BASE}/outher/instantReservation",
        f"{BASE}/outher/appointmentWithoutSlot",
    ]
    assert body_of(requests[1]) == {"user": WRITE_PATIENT}


def test_legacy_teusan_contract_stays_flat() -> None:
    client, requests = partner_client()

    client.measures.health_information(
        identity="12345678901",
        phone_number="+905551112233",
        data=[{"type": "pulse", "date_time": "2026-06-17 09:00", "pulse": 72}],
    )

    assert str(requests[0].url) == f"{BASE}/outher/healthInformation"
    # No `patient` wrapper here — this endpoint predates that contract.
    assert body_of(requests[0]) == {
        "identity": "12345678901",
        "phoneNumber": "+905551112233",
        "data": [{"type": "pulse", "date_time": "2026-06-17 09:00", "pulse": 72}],
    }

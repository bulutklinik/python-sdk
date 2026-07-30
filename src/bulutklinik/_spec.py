"""Single source of truth for the wire contract: one builder per endpoint.

Both the sync and async resources call these builders, so request shapes never
drift between the two surfaces.

Every builder sends ``auth="partner"``: the partner token issued for your
integration. The patient is named inline per request and the server resolves it
strictly inside your own company.

``patient`` shapes:
    read  -> {"identityNumber": str | None, "phoneNumber": str | None}
    write -> {"name": str, "surname": str, "phoneNumber": str,
              "identityNumber"/"email"/"birthdate"/"nationality": optional}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

#: ``partner`` sends the configured token; ``public`` sends no ``Authorization``
#: header. Every endpoint below is ``partner`` — ``public`` is only reachable
#: through the escape hatch (``client.request``).
AuthMode = Literal["partner", "public"]


@dataclass(frozen=True)
class RequestSpec:
    method: str
    path: str
    auth: AuthMode
    body: dict[str, Any] | None = None


# --- doctors ---


def doctor_search(
    search_params: dict[str, Any], current_page: int, order_params: list[str] | None
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/search",
        "partner",
        {
            "searchParams": search_params,
            "orderParams": order_params or [],
            "currentPage": current_page,
        },
    )


def branches() -> RequestSpec:
    return RequestSpec("GET", "/outher/branches", "partner")


def doctor_detail(doctor_id: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/outher/doctorInfos/{doctor_id}", "partner")


def locations() -> RequestSpec:
    return RequestSpec("GET", "/outher/locations", "partner")


# --- slots ---


def slot_schedule(
    doctor_id: int | str,
    schedule_date: str | None,
    schedule_step: int | None,
    schedule_page: int | None,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/doctorSlots",
        "partner",
        {
            "doctorId": doctor_id,
            "scheduleDate": schedule_date,
            "scheduleStep": schedule_step,
            "schedulePage": schedule_page,
        },
    )


# --- appointments ---


def reserve(
    slot_id: int | str, doctor_id: int | str, user: dict[str, Any], without_agreement: bool
) -> RequestSpec:
    path = "/outher/reservationWithoutAgreement" if without_agreement else "/outher/reservation"
    return RequestSpec(
        "POST", path, "partner", {"slotId": slot_id, "doctorId": doctor_id, "user": user}
    )


def instant_reserve(user: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/instantReservation", "partner", {"user": user})


def create_appointment(hash_: str, outher_process_id: int | str) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/appointment",
        "partner",
        {"hash": hash_, "outherProcessId": outher_process_id},
    )


def appointment_without_slot(
    doctor_id: int | str,
    start_date: str,
    finish_date: str,
    user: dict[str, Any],
    is_outher_doctor: int | None,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/appointmentWithoutSlot",
        "partner",
        {
            "doctorId": doctor_id,
            "startDate": start_date,
            "finishDate": finish_date,
            "isOutherDoctor": is_outher_doctor,
            "user": user,
        },
    )


def cancel_without_slot(lookup: dict[str, Any]) -> RequestSpec:
    return RequestSpec("DELETE", "/outher/appointmentWithoutSlot", "partner", dict(lookup))


def appointment_list(phone_number: str, page: int | str | None, type_: str | None) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/appointments",
        "partner",
        {"phoneNumber": phone_number, "page": page, "type": type_},
    )


def appointment_info(lookup: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/appointmentInfo", "partner", dict(lookup))


def check_doctor(doctor_id: int | str, is_outher_doctor: int) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/checkDoctor",
        "partner",
        {"doctorId": doctor_id, "isOutherDoctor": is_outher_doctor},
    )


# --- diets ---


def diet_list(patient: dict[str, Any], page: int | str | None) -> RequestSpec:
    return RequestSpec(
        "POST", "/outher/dietLists", "partner", {"patient": patient, "currentPage": page}
    )


def diet_detail(patient: dict[str, Any], list_id: int | str) -> RequestSpec:
    return RequestSpec("POST", "/outher/diet", "partner", {"patient": patient, "listId": list_id})


# --- laboratory ---


def lab_catalog() -> RequestSpec:
    return RequestSpec("GET", "/outher/laboratoryCatalog", "partner")


def lab_catalog_detail(test_id: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/outher/laboratoryCatalog/{test_id}", "partner")


def lab_results(patient: dict[str, Any], page: int | str | None) -> RequestSpec:
    return RequestSpec(
        "POST", "/outher/laboratoryResults", "partner", {"patient": patient, "currentPage": page}
    )


def lab_result_detail(patient: dict[str, Any], test_id: int | str) -> RequestSpec:
    # Sent as a string on purpose: ids from the list endpoint may carry a "-lab"
    # suffix marking a TmcLab order group, and it must survive round-tripping.
    return RequestSpec(
        "POST", "/outher/laboratoryResult", "partner", {"patient": patient, "testId": str(test_id)}
    )


# --- measures ---


def last_measures(patient: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/lastMeasures", "partner", {"patient": patient})


def measures_list(
    patient: dict[str, Any], type_: str, page: int | str | None, glucose_type: int | None
) -> RequestSpec:
    return RequestSpec(
        "POST",
        f"/outher/measuresList/{type_}",
        "partner",
        {"patient": patient, "currentPage": page, "glucoseType": glucose_type},
    )


def measures_graph(
    patient: dict[str, Any],
    type_: str,
    period: int,
    page: int | str | None,
    glucose_type: int | None,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        f"/outher/measuresGraph/{type_}/{period}",
        "partner",
        {"patient": patient, "currentPage": page, "glucoseType": glucose_type},
    )


def add_measures(patient: dict[str, Any], data: list[dict[str, Any]]) -> RequestSpec:
    return RequestSpec("POST", "/outher/measures", "partner", {"patient": patient, "data": data})


def add_measure(patient: dict[str, Any], type_: str, fields: dict[str, Any]) -> RequestSpec:
    return RequestSpec(
        "POST", f"/outher/measure/{type_}", "partner", {"patient": patient, **fields}
    )


def update_measure(
    patient: dict[str, Any], type_: str, measure_id: int | str, fields: dict[str, Any]
) -> RequestSpec:
    return RequestSpec(
        "PUT",
        f"/outher/measure/{type_}",
        "partner",
        {"patient": patient, "id": measure_id, **fields},
    )


def delete_measure(patient: dict[str, Any], type_: str, measure_id: int | str) -> RequestSpec:
    return RequestSpec(
        "DELETE", f"/outher/measure/{type_}", "partner", {"patient": patient, "id": measure_id}
    )


def health_information(
    identity: str | None, phone_number: str | None, data: list[dict[str, Any]]
) -> RequestSpec:
    # Legacy `teusan` contract: flat, no `patient` wrapper. Kept verbatim.
    return RequestSpec(
        "POST",
        "/outher/healthInformation",
        "partner",
        {"identity": identity, "phoneNumber": phone_number, "data": data},
    )

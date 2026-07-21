"""Single source of truth for the wire contract: one builder per endpoint.

Both the sync and async resources call these builders, so request shapes never
drift between the two surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AuthMode = Literal["public", "bearer", "partner"]


@dataclass(frozen=True)
class RequestSpec:
    method: str
    path: str
    auth: AuthMode
    body: dict[str, Any] | None = None


# --- doctors ---


def branches() -> RequestSpec:
    return RequestSpec("GET", "/patients/allBranches", "bearer")


def locations() -> RequestSpec:
    return RequestSpec("GET", "/patients/allLocations", "bearer")


def quick_search(search_text: str, list_type: str | None, location: str | None) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/quickSearch",
        "bearer",
        {"searchText": search_text, "listType": list_type, "location": location},
    )


def doctor_search(
    search_params: dict[str, Any],
    order_params: list[str],
    other_params: list[str],
    current_page: int,
    per_page_limit: int,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/filteredSearch",
        "bearer",
        {
            "searchParams": search_params,
            "orderParams": order_params,
            "otherParams": other_params,
            "currentPage": current_page,
            "perPageLimit": per_page_limit,
        },
    )


def doctor_detail(doctor_id: int | str, corporate: int | str | None) -> RequestSpec:
    path = (
        f"/patients/doctorDetail/{doctor_id}/{corporate}"
        if corporate is not None
        else f"/patients/doctorDetail/{doctor_id}"
    )
    return RequestSpec("GET", path, "bearer")


# --- slots ---


def schedule(
    doctor_id: int | str,
    list_type: str,
    schedule_date: str | None,
    schedule_step: int | str,
    schedule_page: int | str,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/doctorScheduler",
        "bearer",
        {
            "doctorId": doctor_id,
            "scheduleDate": schedule_date,
            "scheduleStep": schedule_step,
            "schedulePage": schedule_page,
            "listType": list_type,
        },
    )


# --- appointments ---


def reserve_interview(
    doctor_id: int | str, appointment_date: str, appointment_type: str
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/addInterviewDateReservation",
        "bearer",
        {
            "doctorId": doctor_id,
            "appointmentDate": appointment_date,
            "appointmentType": appointment_type,
        },
    )


def add_physical(doctor_id: int | str, appointment_date: str) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/addNewAppointment",
        "bearer",
        {"doctorId": doctor_id, "appointmentDate": appointment_date},
    )


def cancel_appointment(event_id: int | str) -> RequestSpec:
    return RequestSpec("DELETE", f"/patients/deleteUserAppointment/{event_id}", "bearer")


# --- payments ---


def check_discount_code(
    check_type: str,
    discount_code: str,
    doctor_id: int | str | None,
    order_id: int | str | None,
    special_service_id: int | str | None,
    program_slug: str | None,
) -> RequestSpec:
    body: dict[str, Any] = {"checkType": check_type, "discountCode": discount_code}
    if doctor_id is not None:
        body["doctorId"] = doctor_id
    if order_id is not None:
        body["orderId"] = order_id
    if special_service_id is not None:
        body["specialServiceId"] = special_service_id
    if program_slug is not None:
        body["programSlug"] = program_slug
    return RequestSpec("POST", "/patients/checkDiscountCode", "bearer", body)


def get_cards() -> RequestSpec:
    return RequestSpec("GET", "/payments/getCards", "bearer")


def save_card(
    card_holder: str,
    card_number: str,
    card_exp_month: str,
    card_exp_year: str,
    card_cvv: str,
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/payments/saveCard",
        "bearer",
        {
            "cardHolder": card_holder,
            "cardNumber": card_number,
            "cardExpMonth": card_exp_month,
            "cardExpYear": card_exp_year,
            "cardCvv": card_cvv,
        },
    )


def pay(
    doctor_id: int | str,
    appointment_date: str,
    is_3d: bool,
    terms_accept: bool,
    appointment_type: str,
    card_info: dict[str, str] | None,
    card_id: int | str | None,
    save_card: int,
    discount_code: str,
    case_detail: str | None,
) -> RequestSpec:
    body: dict[str, Any] = {
        "doctorId": doctor_id,
        "appointmentDate": appointment_date,
        "appointmentType": appointment_type,
        "is3D": is_3d,
        "termsAccept": terms_accept,
        "saveCard": save_card,
        "discountCode": discount_code,
    }
    if card_id is not None:
        body["cardId"] = card_id
    if card_info is not None:
        body["cardInfo"] = card_info
    if case_detail is not None:
        body["caseDetail"] = case_detail
    return RequestSpec("POST", "/payments/interviewPayment", "bearer", body)


def delete_card(card_id: int | str) -> RequestSpec:
    return RequestSpec("DELETE", f"/payments/deleteCard/{card_id}", "bearer")


# --- measures ---


def add_measures(records: list[dict[str, Any]]) -> RequestSpec:
    return RequestSpec("POST", "/patients/addNewUserMeasures", "bearer", {"data": records})


def add_measure(measure_type: str, fields: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", f"/patients/addNewUserMeasures/{measure_type}", "bearer", fields)


def update_measure(measure_type: str, fields: dict[str, Any]) -> RequestSpec:
    return RequestSpec("PUT", f"/patients/updateUserMeasures/{measure_type}", "bearer", fields)


def delete_measure(measure_type: str, measure_id: int | str) -> RequestSpec:
    return RequestSpec(
        "DELETE", f"/patients/deleteUserMeasures/{measure_type}", "bearer", {"id": measure_id}
    )


def measures_last() -> RequestSpec:
    return RequestSpec("GET", "/patients/measuresList", "bearer")


def measures_list(measure_type: str, page: int | str, glucose_type: int | None) -> RequestSpec:
    path = (
        f"/patients/userMeasuresList/{measure_type}/{page}/{glucose_type}"
        if glucose_type is not None
        else f"/patients/userMeasuresList/{measure_type}/{page}"
    )
    return RequestSpec("GET", path, "bearer")


def measures_graph(
    measure_type: str, period: int, page: int | str, glucose_type: int | None
) -> RequestSpec:
    path = (
        f"/patients/userMeasuresGraph/{measure_type}/{period}/{page}/{glucose_type}"
        if glucose_type is not None
        else f"/patients/userMeasuresGraph/{measure_type}/{period}/{page}"
    )
    return RequestSpec("GET", path, "bearer")


def partner_health_information(
    identity: str | None, phone_number: str | None, data: list[dict[str, Any]]
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/healthInformation",
        "partner",
        {"identity": identity, "phoneNumber": phone_number, "data": data},
    )


# --- skin ---


def image_check(images: list[dict[str, Any]]) -> RequestSpec:
    return RequestSpec("POST", "/patients/imageCheck", "bearer", {"images": images})


# --- meals ---


def analyze_meal(
    image: str,
    portion_size: str,
    meal_type: str,
    portion_grams: int | str | None,
    note: str | None,
) -> RequestSpec:
    body: dict[str, Any] = {
        "image": image,
        "portion_size": portion_size,
        "meal_type": meal_type,
    }
    if portion_grams is not None:
        body["portion_grams"] = portion_grams
    if note is not None:
        body["note"] = note
    return RequestSpec("POST", "/patients/imageAnalyzeMeal", "bearer", body)


# --- laboratory ---


def lab_results(page: int | str | None) -> RequestSpec:
    path = f"/patients/userLabTestList/{page}" if page is not None else "/patients/userLabTestList"
    return RequestSpec("GET", path, "bearer")


def lab_result_detail(test_id: str) -> RequestSpec:
    return RequestSpec("GET", f"/patients/userLabTestDetail/{test_id}", "bearer")


def lab_catalog() -> RequestSpec:
    return RequestSpec("GET", "/patients/allLaboratoryTests", "bearer")


def lab_catalog_detail(id_: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/patients/laboratoryTestDetail/{id_}", "bearer")


def add_laboratory_test(
    test_id: int | str, address_id: int | str, laboratory_id: int | str
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/patients/addNewLaboratoryTest",
        "bearer",
        {"testId": test_id, "addressId": address_id, "laboratoryId": laboratory_id},
    )


# --- diets ---


def diet_list(page: int | str | None) -> RequestSpec:
    path = f"/patients/dietLists/{page}" if page is not None else "/patients/dietLists"
    return RequestSpec("GET", path, "bearer")


def diet_detail(list_id: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/patients/diet/{list_id}", "bearer")

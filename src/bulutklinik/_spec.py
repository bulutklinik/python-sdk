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


# --- auth (registration/password steps that don't mint tokens) ---


def confirm_registration_email(
    verification_code: str, response: str, user_agreements: list[Any] | None
) -> RequestSpec:
    body: dict[str, Any] = {"verificationCode": verification_code, "response": response}
    if user_agreements is not None:
        body["userAgreements"] = user_agreements
    return RequestSpec("POST", "/patients/emailConfirmationRegister", "public", body)


def verify_registration_social(
    name: str,
    surname: str,
    phone_number: str,
    password: str,
    social_type: str,
    key: str,
    email: str | None,
    accept_user_agreement: int,
    user_agreements: list[Any] | None,
) -> RequestSpec:
    body: dict[str, Any] = {
        "name": name,
        "surname": surname,
        "phoneNumber": phone_number,
        "password": password,
        "passwordAgain": password,
        "socialType": social_type,
        "key": key,
        "acceptUserAgreement": accept_user_agreement,
    }
    if email is not None:
        body["email"] = email
    if user_agreements is not None:
        body["userAgreements"] = user_agreements
    return RequestSpec("POST", "/patients/verifyAddingNewPatientSocial", "public", body)


def register_social(
    sms_verification_code: str, response: str, user_agreements: list[Any] | None
) -> RequestSpec:
    body: dict[str, Any] = {"smsVerificationCode": sms_verification_code, "response": response}
    if user_agreements is not None:
        body["userAgreements"] = user_agreements
    return RequestSpec("POST", "/patients/addNewPatientWithSocial", "public", body)


def forgot_password(
    phone_number: str,
    birthdate: str | None,
    recaptcha_v2: str | None,
    captcha: str | None,
) -> RequestSpec:
    body: dict[str, Any] = {"phoneNumber": phone_number}
    if birthdate is not None:
        body["birthdate"] = birthdate
    if recaptcha_v2 is not None:
        body["g-recaptcha-response-v2"] = recaptcha_v2
    if captcha is not None:
        body["captcha"] = captcha
    return RequestSpec("POST", "/patients/forgotPassword", "public", body)


def reset_password(sms_confirm_code: str, response: str, password: str) -> RequestSpec:
    return RequestSpec(
        "PUT",
        "/patients/forgotPassword",
        "public",
        {
            "smsConfirmCode": sms_confirm_code,
            "response": response,
            "password": password,
            "passwordAgain": password,
        },
    )


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


def user_appointments(page: int | str | None) -> RequestSpec:
    path = (
        f"/patients/userAppointments/{page}" if page is not None else "/patients/userAppointments"
    )
    return RequestSpec("GET", path, "bearer")


def user_reservations() -> RequestSpec:
    return RequestSpec("GET", "/patients/userReservations", "bearer")


# --- addresses ---


def address_list() -> RequestSpec:
    return RequestSpec("GET", "/patients/userAddress", "bearer")


def address_add(
    title: str,
    city_id: int | str,
    district_id: int | str,
    address: str,
    location_lat: str,
    location_lng: str,
    description: str | None,
    is_default: int | None,
) -> RequestSpec:
    body: dict[str, Any] = {
        "title": title,
        "cityId": city_id,
        "districtId": district_id,
        "address": address,
        "locationLat": location_lat,
        "locationLng": location_lng,
    }
    if description is not None:
        body["description"] = description
    if is_default is not None:
        body["isDefault"] = is_default
    return RequestSpec("POST", "/patients/userAddress", "bearer", body)


def address_update(
    address_id: int | str,
    *,
    title: str | None = None,
    description: str | None = None,
    city_id: int | str | None = None,
    district_id: int | str | None = None,
    address: str | None = None,
    location_lat: str | None = None,
    location_lng: str | None = None,
    is_default: int | None = None,
) -> RequestSpec:
    body: dict[str, Any] = {"id": address_id}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if city_id is not None:
        body["cityId"] = city_id
    if district_id is not None:
        body["districtId"] = district_id
    if address is not None:
        body["address"] = address
    if location_lat is not None:
        body["locationLat"] = location_lat
    if location_lng is not None:
        body["locationLng"] = location_lng
    if is_default is not None:
        body["isDefault"] = is_default
    return RequestSpec("PUT", "/patients/userAddress", "bearer", body)


def address_delete(address_id: int | str) -> RequestSpec:
    return RequestSpec("DELETE", "/patients/userAddress", "bearer", {"id": address_id})


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


# --- partner (/outher — company-scoped surface) ---
#
# Every builder below sends ``auth="partner"``: the configured partner token, not
# the patient access token. The patient is named inline per request, and the
# server resolves it strictly inside the partner's own company.
#
# ``patient`` shapes:
#   read  -> {"identityNumber": str | None, "phoneNumber": str | None}
#   write -> {"name": str, "surname": str, "phoneNumber": str,
#             "identityNumber"/"email"/"birthdate"/"nationality": optional}


def partner_doctor_search(
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


def partner_branches() -> RequestSpec:
    return RequestSpec("GET", "/outher/branches", "partner")


def partner_doctor_detail(doctor_id: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/outher/doctorInfos/{doctor_id}", "partner")


def partner_locations() -> RequestSpec:
    return RequestSpec("GET", "/outher/locations", "partner")


def partner_slot_schedule(
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


def partner_reserve(
    slot_id: int | str, doctor_id: int | str, user: dict[str, Any], without_agreement: bool
) -> RequestSpec:
    path = "/outher/reservationWithoutAgreement" if without_agreement else "/outher/reservation"
    return RequestSpec(
        "POST", path, "partner", {"slotId": slot_id, "doctorId": doctor_id, "user": user}
    )


def partner_instant_reserve(user: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/instantReservation", "partner", {"user": user})


def partner_create_appointment(hash_: str, outher_process_id: int | str) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/appointment",
        "partner",
        {"hash": hash_, "outherProcessId": outher_process_id},
    )


def partner_appointment_without_slot(
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


def partner_cancel_without_slot(lookup: dict[str, Any]) -> RequestSpec:
    return RequestSpec("DELETE", "/outher/appointmentWithoutSlot", "partner", dict(lookup))


def partner_appointment_list(
    phone_number: str, page: int | str | None, type_: str | None
) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/appointments",
        "partner",
        {"phoneNumber": phone_number, "page": page, "type": type_},
    )


def partner_appointment_info(lookup: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/appointmentInfo", "partner", dict(lookup))


def partner_check_doctor(doctor_id: int | str, is_outher_doctor: int) -> RequestSpec:
    return RequestSpec(
        "POST",
        "/outher/checkDoctor",
        "partner",
        {"doctorId": doctor_id, "isOutherDoctor": is_outher_doctor},
    )


def partner_diet_list(patient: dict[str, Any], page: int | str | None) -> RequestSpec:
    return RequestSpec(
        "POST", "/outher/dietLists", "partner", {"patient": patient, "currentPage": page}
    )


def partner_diet_detail(patient: dict[str, Any], list_id: int | str) -> RequestSpec:
    return RequestSpec("POST", "/outher/diet", "partner", {"patient": patient, "listId": list_id})


def partner_lab_catalog() -> RequestSpec:
    return RequestSpec("GET", "/outher/laboratoryCatalog", "partner")


def partner_lab_catalog_detail(test_id: int | str) -> RequestSpec:
    return RequestSpec("GET", f"/outher/laboratoryCatalog/{test_id}", "partner")


def partner_lab_results(patient: dict[str, Any], page: int | str | None) -> RequestSpec:
    return RequestSpec(
        "POST", "/outher/laboratoryResults", "partner", {"patient": patient, "currentPage": page}
    )


def partner_lab_result_detail(patient: dict[str, Any], test_id: int | str) -> RequestSpec:
    # Sent as a string on purpose: ids from the list endpoint may carry a "-lab"
    # suffix marking a TmcLab order group, and it must survive round-tripping.
    return RequestSpec(
        "POST", "/outher/laboratoryResult", "partner", {"patient": patient, "testId": str(test_id)}
    )


def partner_last_measures(patient: dict[str, Any]) -> RequestSpec:
    return RequestSpec("POST", "/outher/lastMeasures", "partner", {"patient": patient})


def partner_measures_list(
    patient: dict[str, Any], type_: str, page: int | str | None, glucose_type: int | None
) -> RequestSpec:
    return RequestSpec(
        "POST",
        f"/outher/measuresList/{type_}",
        "partner",
        {"patient": patient, "currentPage": page, "glucoseType": glucose_type},
    )


def partner_measures_graph(
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


def partner_add_measures(patient: dict[str, Any], data: list[dict[str, Any]]) -> RequestSpec:
    return RequestSpec(
        "POST", "/outher/measures", "partner", {"patient": patient, "data": data}
    )


def partner_add_measure(
    patient: dict[str, Any], type_: str, fields: dict[str, Any]
) -> RequestSpec:
    return RequestSpec(
        "POST", f"/outher/measure/{type_}", "partner", {"patient": patient, **fields}
    )


def partner_update_measure(
    patient: dict[str, Any], type_: str, measure_id: int | str, fields: dict[str, Any]
) -> RequestSpec:
    return RequestSpec(
        "PUT",
        f"/outher/measure/{type_}",
        "partner",
        {"patient": patient, "id": measure_id, **fields},
    )


def partner_delete_measure(
    patient: dict[str, Any], type_: str, measure_id: int | str
) -> RequestSpec:
    return RequestSpec(
        "DELETE", f"/outher/measure/{type_}", "partner", {"patient": patient, "id": measure_id}
    )

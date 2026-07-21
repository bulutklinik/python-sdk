"""Synchronous service resources."""

from __future__ import annotations

from typing import Any

from . import _spec
from ._auth import (
    connect_body,
    finish_login,
    register_body,
    store_tokens,
    verify_registration_body,
)
from ._http import HttpClient
from ._spec import RequestSpec
from .models import LoginResult

# Module-level alias: inside MeasuresResource the `list` method shadows the
# builtin `list`, so `list[...]` annotations there must use this instead.
_MeasureRecords = list[dict[str, Any]]


class AuthResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def connect(
        self,
        api_user_name: str,
        api_user_password: str | None,
        login_mode: str,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        with_phone_number: str | None = None,
    ) -> LoginResult:
        body = connect_body(
            api_user_name,
            api_user_password,
            client_id or self._http.client_id,
            client_secret or self._http.client_secret,
            login_mode,
            with_phone_number,
        )
        data = self._http.send(RequestSpec("POST", "/general/connectApi", "public", body))
        return finish_login(data, self._http.token_store)

    def connect_with_two_factor(self, sms_verification_code: str, response: str) -> None:
        data = self._http.send(
            RequestSpec(
                "POST",
                "/general/connectApiWithTwoFactor",
                "public",
                {"smsVerificationCode": sms_verification_code, "response": response},
            )
        )
        store_tokens(data, self._http.token_store)

    def verify_registration(
        self,
        *,
        name: str,
        surname: str,
        phone_number: str,
        phone_code: str,
        email: str,
        password: str,
        accept_user_agreement: int = 1,
        recaptcha_v2: str | None = None,
        captcha: str | None = None,
        user_agreements: list[Any] | None = None,
    ) -> Any:
        """Registration step 1: send the verification code, return the ``response`` blob.

        Uses the configured **partner** token (the endpoint is behind ``auth:apiusers``,
        not public). A CAPTCHA token (``recaptcha_v2`` or ``captcha``), minted by a
        browser/human, is required. Feed the returned ``response`` (and the code the
        user receives) into :meth:`register`.
        """
        body = verify_registration_body(
            name,
            surname,
            phone_number,
            phone_code,
            email,
            password,
            accept_user_agreement,
            recaptcha_v2,
            captcha,
            user_agreements,
        )
        return self._http.send(
            RequestSpec("POST", "/patients/verifyAddingNewPatient", "partner", body)
        )

    def register(
        self,
        *,
        name: str,
        surname: str,
        api_user_name: str,
        phone_number: str,
        password: str,
        sms_verification_code: str,
        response: str,
        accept_user_agreement: int = 1,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        body = register_body(
            name,
            surname,
            api_user_name,
            phone_number,
            password,
            sms_verification_code,
            response,
            accept_user_agreement,
            client_id or self._http.client_id,
            client_secret or self._http.client_secret,
        )
        data = self._http.send(RequestSpec("POST", "/patients/addNewPatient", "public", body))
        store_tokens(data, self._http.token_store)

    def confirm_registration_email(
        self,
        *,
        verification_code: str,
        response: str,
        user_agreements: list[Any] | None = None,
    ) -> Any:
        """Registration step 2 (e-mail branch): confirm the e-mailed code, get the SMS blob.

        When :meth:`verify_registration` returned ``confirmationType == "email"``, confirm
        the code here with the same ``response`` blob. Returns a fresh ``response`` blob +
        ``confirmationType: "sms"`` to feed into :meth:`register`. Public.
        """
        return self._http.send(
            _spec.confirm_registration_email(verification_code, response, user_agreements)
        )

    def verify_registration_social(
        self,
        *,
        name: str,
        surname: str,
        phone_number: str,
        password: str,
        social_type: str,
        key: str,
        email: str | None = None,
        accept_user_agreement: int = 1,
        user_agreements: list[Any] | None = None,
    ) -> Any:
        """Social sign-up step 1: send the SMS code, return a ``response`` blob. Public."""
        return self._http.send(
            _spec.verify_registration_social(
                name,
                surname,
                phone_number,
                password,
                social_type,
                key,
                email,
                accept_user_agreement,
                user_agreements,
            )
        )

    def register_social(
        self,
        *,
        sms_verification_code: str,
        response: str,
        user_agreements: list[Any] | None = None,
    ) -> Any:
        """Social sign-up step 2: create the social patient. Does NOT log in — call
        :meth:`connect` with ``login_mode="social"`` afterwards. Public.
        """
        return self._http.send(
            _spec.register_social(sms_verification_code, response, user_agreements)
        )

    def forgot_password(
        self,
        *,
        phone_number: str,
        birthdate: str | None = None,
        recaptcha_v2: str | None = None,
        captcha: str | None = None,
    ) -> Any:
        """Password reset step 1: send the SMS confirm code, return a ``response`` blob.

        A CAPTCHA token (``recaptcha_v2`` or ``captcha``) is required outside local env. Public.
        """
        return self._http.send(
            _spec.forgot_password(phone_number, birthdate, recaptcha_v2, captcha)
        )

    def reset_password(
        self,
        *,
        sms_confirm_code: str,
        response: str,
        password: str,
    ) -> Any:
        """Password reset step 2: set the new password with the SMS confirm code + blob. Public."""
        return self._http.send(_spec.reset_password(sms_confirm_code, response, password))

    def refresh(self) -> None:
        self._http.refresh()

    def disconnect(self) -> None:
        try:
            self._http.send(RequestSpec("POST", "/general/disconnectApi", "bearer", {}))
        finally:
            self._http.token_store.clear()


class DoctorsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def branches(self) -> Any:
        return self._http.send(_spec.branches())

    def locations(self) -> Any:
        return self._http.send(_spec.locations())

    def quick_search(
        self, search_text: str, list_type: str | None = None, location: str | None = None
    ) -> Any:
        return self._http.send(_spec.quick_search(search_text, list_type, location))

    def search(
        self,
        *,
        search_params: dict[str, Any] | None = None,
        order_params: list[str] | None = None,
        other_params: list[str] | None = None,
        current_page: int = 1,
        per_page_limit: int = 20,
    ) -> Any:
        return self._http.send(
            _spec.doctor_search(
                search_params or {},
                order_params or [],
                other_params or [],
                current_page,
                per_page_limit,
            )
        )

    def detail(self, doctor_id: int | str, corporate: int | str | None = None) -> Any:
        return self._http.send(_spec.doctor_detail(doctor_id, corporate))


class SlotsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def schedule(
        self,
        doctor_id: int | str,
        list_type: str,
        *,
        schedule_date: str | None = None,
        schedule_step: int | str = 7,
        schedule_page: int | str = 1,
    ) -> Any:
        return self._http.send(
            _spec.schedule(doctor_id, list_type, schedule_date, schedule_step, schedule_page)
        )


class AppointmentsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def reserve_interview(
        self, doctor_id: int | str, appointment_date: str, appointment_type: str = "interview"
    ) -> Any:
        return self._http.send(
            _spec.reserve_interview(doctor_id, appointment_date, appointment_type)
        )

    def add_physical(self, doctor_id: int | str, appointment_date: str) -> Any:
        return self._http.send(_spec.add_physical(doctor_id, appointment_date))

    def cancel(self, event_id: int | str) -> Any:
        return self._http.send(_spec.cancel_appointment(event_id))

    def list(self, page: int | str | None = None) -> Any:
        """The patient's appointments (``{foundAppointmentsCount, foundAppointments}``).

        Each item's ``event_id`` is the id for :meth:`cancel`; rows with ``event_id`` ``"0"``
        are paid-order/refund entries (not cancellable). Server paging is disabled — page 1
        (the default) returns the full list.
        """
        return self._http.send(_spec.user_appointments(page))

    def reservations(self) -> Any:
        """The patient's active online-slot reservation holds (with a ``minute_diff`` countdown)."""
        return self._http.send(_spec.user_reservations())


class AddressesResource:
    """The patient's saved addresses. Required by ``laboratory.order`` (needs an ``addressId``)."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> Any:
        """List saved addresses (default first). Each item's ``id`` is the ``addressId``."""
        return self._http.send(_spec.address_list())

    def add(
        self,
        *,
        title: str,
        city_id: int | str,
        district_id: int | str,
        address: str,
        location_lat: str,
        location_lng: str,
        description: str | None = None,
        is_default: int | None = None,
    ) -> Any:
        """Add an address. Success → ``{"addressId": ...}``. ``city_id`` comes from
        ``doctors.locations()``; ``district_id`` from ``GET /getConfig`` (``cities[].districts[]``).
        """
        return self._http.send(
            _spec.address_add(
                title,
                city_id,
                district_id,
                address,
                location_lat,
                location_lng,
                description,
                is_default,
            )
        )

    def update(
        self,
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
    ) -> Any:
        """Update an address by id. Pass ``is_default=1`` alone to flip the default flag,
        or any other field to edit it.
        """
        return self._http.send(
            _spec.address_update(
                address_id,
                title=title,
                description=description,
                city_id=city_id,
                district_id=district_id,
                address=address,
                location_lat=location_lat,
                location_lng=location_lng,
                is_default=is_default,
            )
        )

    def delete(self, address_id: int | str) -> Any:
        """Delete an address by id (default/used addresses cannot be deleted)."""
        return self._http.send(_spec.address_delete(address_id))


class PaymentsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def check_discount_code(
        self,
        check_type: str,
        discount_code: str,
        *,
        doctor_id: int | str | None = None,
        order_id: int | str | None = None,
        special_service_id: int | str | None = None,
        program_slug: str | None = None,
    ) -> Any:
        return self._http.send(
            _spec.check_discount_code(
                check_type, discount_code, doctor_id, order_id, special_service_id, program_slug
            )
        )

    def get_cards(self) -> Any:
        return self._http.send(_spec.get_cards())

    def save_card(
        self,
        card_holder: str,
        card_number: str,
        card_exp_month: str,
        card_exp_year: str,
        card_cvv: str,
    ) -> Any:
        return self._http.send(
            _spec.save_card(card_holder, card_number, card_exp_month, card_exp_year, card_cvv)
        )

    def pay(
        self,
        doctor_id: int | str,
        appointment_date: str,
        is_3d: bool,
        terms_accept: bool,
        *,
        appointment_type: str = "interview",
        card_info: dict[str, str] | None = None,
        card_id: int | str | None = None,
        save_card: int = 0,
        discount_code: str = "",
        case_detail: str | None = None,
    ) -> Any:
        return self._http.send(
            _spec.pay(
                doctor_id,
                appointment_date,
                is_3d,
                terms_accept,
                appointment_type,
                card_info,
                card_id,
                save_card,
                discount_code,
                case_detail,
            )
        )

    def delete_card(self, card_id: int | str) -> Any:
        return self._http.send(_spec.delete_card(card_id))


class MeasuresResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def add_list(self, records: _MeasureRecords) -> Any:
        return self._http.send(_spec.add_measures(records))

    def add(self, measure_type: str, fields: dict[str, Any]) -> Any:
        return self._http.send(_spec.add_measure(measure_type, fields))

    def update(self, measure_type: str, fields: dict[str, Any]) -> Any:
        return self._http.send(_spec.update_measure(measure_type, fields))

    def delete(self, measure_type: str, measure_id: int | str) -> Any:
        return self._http.send(_spec.delete_measure(measure_type, measure_id))

    def last(self) -> Any:
        return self._http.send(_spec.measures_last())

    def list(self, measure_type: str, page: int | str, glucose_type: int | None = None) -> Any:
        return self._http.send(_spec.measures_list(measure_type, page, glucose_type))

    def graph(
        self, measure_type: str, period: int, page: int | str, glucose_type: int | None = None
    ) -> Any:
        return self._http.send(_spec.measures_graph(measure_type, period, page, glucose_type))

    def partner_health_information(
        self, *, identity: str | None = None, phone_number: str | None = None, data: _MeasureRecords
    ) -> Any:
        return self._http.send(_spec.partner_health_information(identity, phone_number, data))


class SkinResource:
    """AI skin-lesion analysis ("Cildimde Neyim Var")."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def analyze(self, images: list[dict[str, Any]]) -> Any:
        """Analyze one or more skin photos. Each image is classified (lesion
        ``label``), summarized in Turkish (``comment``), and returned with quality
        flags, a ``confidence``, possible ICD hints and an opaque ``case_detail``
        blob. The ``case_detail`` may be forwarded verbatim as a payment's
        ``caseDetail``.
        """
        return self._http.send(_spec.image_check(images))


class MealsResource:
    """AI meal-photo calorie/nutrition estimation (sibling of ``skin``)."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def analyze(
        self,
        image: str,
        portion_size: str,
        meal_type: str,
        *,
        portion_grams: int | str | None = None,
        note: str | None = None,
    ) -> Any:
        """Estimate calories and nutrition from a meal photo. The input names map
        to the API's snake_case body (``image``, ``portion_size``, ``meal_type``);
        ``portion_grams`` and ``note`` are sent only when provided.
        """
        return self._http.send(
            _spec.analyze_meal(image, portion_size, meal_type, portion_grams, note)
        )


class LaboratoryResource:
    """Patient laboratory results, the orderable test catalog, and test pre-ordering."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def results(self, page: int | str | None = None) -> Any:
        """The patient's completed/in-progress lab results. ``page`` defaults to 1
        server-side; the ``/{page}`` segment is omitted when ``page`` is None. Some
        result ids carry a ``-lab`` suffix (TMC-lab-ordered tests)."""
        return self._http.send(_spec.lab_results(page))

    def result_detail(self, test_id: str) -> Any:
        """Detail of a single result. ``test_id`` is a **string** (a plain id such as
        ``"123"`` or a ``"<id>-lab"`` TMC id) and is interpolated verbatim."""
        return self._http.send(_spec.lab_result_detail(test_id))

    def catalog(self) -> Any:
        """The orderable test-group catalog."""
        return self._http.send(_spec.lab_catalog())

    def catalog_detail(self, id: int | str) -> Any:
        """A single catalog group by id."""
        return self._http.send(_spec.lab_catalog_detail(id))

    def order(self, test_id: int | str, address_id: int | str, laboratory_id: int | str) -> Any:
        """Pre-order a lab test. All three ids are required; success returns
        ``{"preOrderId": ...}``."""
        return self._http.send(_spec.add_laboratory_test(test_id, address_id, laboratory_id))


class DietsResource:
    """The patient's diet lists (a dietitian's "Diyet Listesi"). JSON only."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, page: int | str | None = None) -> Any:
        """The patient's diet lists. ``page`` defaults to 1 server-side (page size is
        fixed to 10); the ``/{page}`` segment is omitted when ``page`` is None."""
        return self._http.send(_spec.diet_list(page))

    def detail(self, list_id: int | str) -> Any:
        """A single diet list (array of meal-time groups) by ``list_id``."""
        return self._http.send(_spec.diet_detail(list_id))

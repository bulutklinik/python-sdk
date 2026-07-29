"""The company-scoped partner surface (``/outher``).

A **second persona**, not a replacement for the patient one:

==========================  ==============================  ==============================
                            patient (``client.*``)          partner (``client.partner.*``)
==========================  ==============================  ==============================
Auth                        patient login, access token     pre-issued partner token
Who the data belongs to     the patient, across clinics     your own company only
How a patient is named      implicit (the session)          inline, per request
==========================  ==============================  ==============================

Requests here use the configured ``partner_token``; no patient login is involved
and the silent access-token refresh does not apply.

Patient login/registration, the card vault, 3-D Secure payment, self-service AI
and address CRUD have no partner equivalent and stay on the patient surface by
design.

Sync and async classes deliberately share the same ``_spec`` builders, so request
shapes can never drift between the two surfaces.
"""

from __future__ import annotations

from typing import Any

from . import _spec
from ._http import AsyncHttpClient, HttpClient

# ``patient`` shapes accepted by the endpoints below:
#   read  -> {"identityNumber": str | None, "phoneNumber": str | None}
#            identityNumber is primary; phoneNumber is accepted only when it
#            matches exactly one patient in your company.
#   write -> {"name": str, "surname": str, "phoneNumber": str, ...optional}
#            the patient is created inside your company when absent.
Patient = dict[str, Any]

# Module-level alias on purpose: the measures resources define a method called
# ``list``, which shadows the builtin inside the class body, so ``list[...]``
# cannot be spelled in those signatures.
MeasureRows = list[dict[str, Any]]


class PartnerDoctorsResource:
    """Doctor discovery. Scoped to the doctors enabled for your integration, so a
    doctor returned here is one you can actually book."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def search(
        self,
        search_params: dict[str, Any],
        current_page: int = 1,
        order_params: list[str] | None = None,
    ) -> Any:
        return self._http.send(
            _spec.partner_doctor_search(search_params, current_page, order_params)
        )

    def branches(self) -> Any:
        return self._http.send(_spec.partner_branches())

    def detail(self, doctor_id: int | str) -> Any:
        return self._http.send(_spec.partner_doctor_detail(doctor_id))

    def locations(self) -> Any:
        """City list. Global catalogue — not scoped to your company."""
        return self._http.send(_spec.partner_locations())


class PartnerSlotsResource:
    """Doctor availability."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def schedule(
        self,
        doctor_id: int | str,
        *,
        schedule_date: str | None = None,
        schedule_step: int | None = None,
        schedule_page: int | None = None,
    ) -> Any:
        """Either pass ``schedule_date`` (``Y-m-d``), or page through with
        ``schedule_step`` + ``schedule_page``; the server requires one form."""
        return self._http.send(
            _spec.partner_slot_schedule(doctor_id, schedule_date, schedule_step, schedule_page)
        )


class PartnerAppointmentsResource:
    """Appointment lifecycle.

    The patient is supplied inline as ``user`` — there is no patient login in this
    mode. **Payment is not taken through the API**: ``reserve`` returns a process
    settled through the hosted web checkout.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def reserve(
        self,
        slot_id: int | str,
        doctor_id: int | str,
        user: Patient,
        *,
        without_agreement: bool = False,
    ) -> Any:
        return self._http.send(_spec.partner_reserve(slot_id, doctor_id, user, without_agreement))

    def instant_reserve(self, user: Patient) -> Any:
        return self._http.send(_spec.partner_instant_reserve(user))

    def create(self, hash_: str, outher_process_id: int | str) -> Any:
        """Turn a reservation into a confirmed appointment."""
        return self._http.send(_spec.partner_create_appointment(hash_, outher_process_id))

    def create_without_slot(
        self,
        doctor_id: int | str,
        start_date: str,
        finish_date: str,
        user: Patient,
        *,
        is_outher_doctor: int | None = None,
    ) -> Any:
        return self._http.send(
            _spec.partner_appointment_without_slot(
                doctor_id, start_date, finish_date, user, is_outher_doctor
            )
        )

    def cancel_without_slot(self, lookup: dict[str, Any]) -> Any:
        """Address the appointment either by process (``hash`` + ``outherProcessId``)
        or by coordinates (``doctorId`` + ``appointmentDate`` + ``isOutherDoctor``)."""
        return self._http.send(_spec.partner_cancel_without_slot(lookup))

    def list(
        self, phone_number: str, page: int | str | None = None, type_: str | None = None
    ) -> Any:
        return self._http.send(_spec.partner_appointment_list(phone_number, page, type_))

    def info(self, lookup: dict[str, Any]) -> Any:
        return self._http.send(_spec.partner_appointment_info(lookup))

    def check_doctor(self, doctor_id: int | str, is_outher_doctor: int) -> Any:
        return self._http.send(_spec.partner_check_doctor(doctor_id, is_outher_doctor))


class PartnerDietsResource:
    """Diet lists recorded for a patient **inside your own company**."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, patient: Patient, page: int | str | None = None) -> Any:
        return self._http.send(_spec.partner_diet_list(patient, page))

    def detail(self, patient: Patient, list_id: int | str) -> Any:
        return self._http.send(_spec.partner_diet_detail(patient, list_id))


class PartnerLaboratoryResource:
    """Laboratory catalogue (global, static) and results (your company only)."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def catalog(self) -> Any:
        return self._http.send(_spec.partner_lab_catalog())

    def catalog_detail(self, test_id: int | str) -> Any:
        """Prices are the plain list prices — the patient-side discount pass does
        not apply on the partner surface."""
        return self._http.send(_spec.partner_lab_catalog_detail(test_id))

    def results(self, patient: Patient, page: int | str | None = None) -> Any:
        """Ids returned here are accepted verbatim by ``result_detail``; a ``-lab``
        suffix marks a TmcLab order group, a plain number an HBYS lab request."""
        return self._http.send(_spec.partner_lab_results(patient, page))

    def result_detail(self, patient: Patient, test_id: int | str) -> Any:
        return self._http.send(_spec.partner_lab_result_detail(patient, test_id))


class PartnerMeasuresResource:
    """Health measurements.

    **Scope:** written into and read from **your own company**. Values the patient
    entered in the Bulutklinik mobile app live in the consumer tenant and are not
    visible here — a consequence of tenant isolation, not a bug.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def last(self, patient: Patient) -> Any:
        return self._http.send(_spec.partner_last_measures(patient))

    def list(
        self,
        patient: Patient,
        type_: str,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        return self._http.send(_spec.partner_measures_list(patient, type_, page, glucose_type))

    def graph(
        self,
        patient: Patient,
        type_: str,
        period: int,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        """``period``: 1=day, 2=week, 3=month, 4=year."""
        return self._http.send(
            _spec.partner_measures_graph(patient, type_, period, page, glucose_type)
        )

    def add_list(self, patient: Patient, data: MeasureRows) -> Any:
        """Write several measurements of mixed types in one transaction. Max 200 rows."""
        return self._http.send(_spec.partner_add_measures(patient, data))

    def add(self, patient: Patient, type_: str, fields: dict[str, Any]) -> Any:
        return self._http.send(_spec.partner_add_measure(patient, type_, fields))

    def update(
        self, patient: Patient, type_: str, measure_id: int | str, fields: dict[str, Any]
    ) -> Any:
        return self._http.send(_spec.partner_update_measure(patient, type_, measure_id, fields))

    def delete(self, patient: Patient, type_: str, measure_id: int | str) -> Any:
        return self._http.send(_spec.partner_delete_measure(patient, type_, measure_id))

    def health_information(
        self,
        *,
        identity: str | None = None,
        phone_number: str | None = None,
        data: MeasureRows,
    ) -> Any:
        """Legacy teusan bulk submission.

        .. deprecated::
            Writes into the shared consumer tenant rather than your own company,
            so the values are not readable through ``last`` / ``list``. Prefer
            ``add_list``. Kept for existing teusan integrations.
        """
        return self._http.send(_spec.partner_health_information(identity, phone_number, data))


class PartnerNamespace:
    """Synchronous partner surface, exposed as ``client.partner``."""

    def __init__(self, http: HttpClient) -> None:
        self.doctors = PartnerDoctorsResource(http)
        self.slots = PartnerSlotsResource(http)
        self.appointments = PartnerAppointmentsResource(http)
        self.diets = PartnerDietsResource(http)
        self.laboratory = PartnerLaboratoryResource(http)
        self.measures = PartnerMeasuresResource(http)


# --- async mirror -----------------------------------------------------------
# Same builders, same request shapes; only the await boundary differs.


class AsyncPartnerDoctorsResource:
    """Async counterpart of :class:`PartnerDoctorsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def search(
        self,
        search_params: dict[str, Any],
        current_page: int = 1,
        order_params: list[str] | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.partner_doctor_search(search_params, current_page, order_params)
        )

    async def branches(self) -> Any:
        return await self._http.send(_spec.partner_branches())

    async def detail(self, doctor_id: int | str) -> Any:
        return await self._http.send(_spec.partner_doctor_detail(doctor_id))

    async def locations(self) -> Any:
        return await self._http.send(_spec.partner_locations())


class AsyncPartnerSlotsResource:
    """Async counterpart of :class:`PartnerSlotsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def schedule(
        self,
        doctor_id: int | str,
        *,
        schedule_date: str | None = None,
        schedule_step: int | None = None,
        schedule_page: int | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.partner_slot_schedule(doctor_id, schedule_date, schedule_step, schedule_page)
        )


class AsyncPartnerAppointmentsResource:
    """Async counterpart of :class:`PartnerAppointmentsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def reserve(
        self,
        slot_id: int | str,
        doctor_id: int | str,
        user: Patient,
        *,
        without_agreement: bool = False,
    ) -> Any:
        return await self._http.send(
            _spec.partner_reserve(slot_id, doctor_id, user, without_agreement)
        )

    async def instant_reserve(self, user: Patient) -> Any:
        return await self._http.send(_spec.partner_instant_reserve(user))

    async def create(self, hash_: str, outher_process_id: int | str) -> Any:
        return await self._http.send(_spec.partner_create_appointment(hash_, outher_process_id))

    async def create_without_slot(
        self,
        doctor_id: int | str,
        start_date: str,
        finish_date: str,
        user: Patient,
        *,
        is_outher_doctor: int | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.partner_appointment_without_slot(
                doctor_id, start_date, finish_date, user, is_outher_doctor
            )
        )

    async def cancel_without_slot(self, lookup: dict[str, Any]) -> Any:
        return await self._http.send(_spec.partner_cancel_without_slot(lookup))

    async def list(
        self, phone_number: str, page: int | str | None = None, type_: str | None = None
    ) -> Any:
        return await self._http.send(_spec.partner_appointment_list(phone_number, page, type_))

    async def info(self, lookup: dict[str, Any]) -> Any:
        return await self._http.send(_spec.partner_appointment_info(lookup))

    async def check_doctor(self, doctor_id: int | str, is_outher_doctor: int) -> Any:
        return await self._http.send(_spec.partner_check_doctor(doctor_id, is_outher_doctor))


class AsyncPartnerDietsResource:
    """Async counterpart of :class:`PartnerDietsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self, patient: Patient, page: int | str | None = None) -> Any:
        return await self._http.send(_spec.partner_diet_list(patient, page))

    async def detail(self, patient: Patient, list_id: int | str) -> Any:
        return await self._http.send(_spec.partner_diet_detail(patient, list_id))


class AsyncPartnerLaboratoryResource:
    """Async counterpart of :class:`PartnerLaboratoryResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def catalog(self) -> Any:
        return await self._http.send(_spec.partner_lab_catalog())

    async def catalog_detail(self, test_id: int | str) -> Any:
        return await self._http.send(_spec.partner_lab_catalog_detail(test_id))

    async def results(self, patient: Patient, page: int | str | None = None) -> Any:
        return await self._http.send(_spec.partner_lab_results(patient, page))

    async def result_detail(self, patient: Patient, test_id: int | str) -> Any:
        return await self._http.send(_spec.partner_lab_result_detail(patient, test_id))


class AsyncPartnerMeasuresResource:
    """Async counterpart of :class:`PartnerMeasuresResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def last(self, patient: Patient) -> Any:
        return await self._http.send(_spec.partner_last_measures(patient))

    async def list(
        self,
        patient: Patient,
        type_: str,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.partner_measures_list(patient, type_, page, glucose_type)
        )

    async def graph(
        self,
        patient: Patient,
        type_: str,
        period: int,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.partner_measures_graph(patient, type_, period, page, glucose_type)
        )

    async def add_list(self, patient: Patient, data: MeasureRows) -> Any:
        return await self._http.send(_spec.partner_add_measures(patient, data))

    async def add(self, patient: Patient, type_: str, fields: dict[str, Any]) -> Any:
        return await self._http.send(_spec.partner_add_measure(patient, type_, fields))

    async def update(
        self, patient: Patient, type_: str, measure_id: int | str, fields: dict[str, Any]
    ) -> Any:
        return await self._http.send(
            _spec.partner_update_measure(patient, type_, measure_id, fields)
        )

    async def delete(self, patient: Patient, type_: str, measure_id: int | str) -> Any:
        return await self._http.send(_spec.partner_delete_measure(patient, type_, measure_id))

    async def health_information(
        self,
        *,
        identity: str | None = None,
        phone_number: str | None = None,
        data: MeasureRows,
    ) -> Any:
        """.. deprecated:: Prefer :meth:`add_list`; see the sync counterpart."""
        return await self._http.send(
            _spec.partner_health_information(identity, phone_number, data)
        )


class AsyncPartnerNamespace:
    """Asynchronous partner surface, exposed as ``client.partner``."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self.doctors = AsyncPartnerDoctorsResource(http)
        self.slots = AsyncPartnerSlotsResource(http)
        self.appointments = AsyncPartnerAppointmentsResource(http)
        self.diets = AsyncPartnerDietsResource(http)
        self.laboratory = AsyncPartnerLaboratoryResource(http)
        self.measures = AsyncPartnerMeasuresResource(http)

"""Synchronous resource groups.

Every call runs on the company-scoped ``/outher`` surface with the partner token
issued for your integration: you act on the patients of **your own company**, and
the patient is named inline on each request — there is no login and no session.

Sync and async resources share the same :mod:`._spec` builders, so request shapes
can never drift between them.
"""

from __future__ import annotations

from typing import Any

from . import _spec
from ._http import HttpClient

#: ``patient`` shapes accepted by the endpoints below:
#:   read  -> {"identityNumber": str | None, "phoneNumber": str | None}
#:            identityNumber is primary; phoneNumber is accepted only when it
#:            matches exactly one patient in your company.
#:   write -> {"name": str, "surname": str, "phoneNumber": str, ...optional}
#:            the patient is created inside your company when absent.
Patient = dict[str, Any]

# Module-level alias on purpose: the measures resource defines a method called
# ``list``, which shadows the builtin inside the class body, so ``list[...]``
# cannot be spelled in those signatures.
MeasureRows = list[dict[str, Any]]


class DoctorsResource:
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
        """``order_params``: ``name`` / ``order`` / ``slot``."""
        return self._http.send(_spec.doctor_search(search_params, current_page, order_params))

    def branches(self) -> Any:
        return self._http.send(_spec.branches())

    def detail(self, doctor_id: int | str) -> Any:
        """The ``doctor_id`` here feeds :meth:`SlotsResource.schedule`."""
        return self._http.send(_spec.doctor_detail(doctor_id))

    def locations(self) -> Any:
        """City list. Global catalogue — not scoped to your company."""
        return self._http.send(_spec.locations())


class SlotsResource:
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
        ``schedule_step`` + ``schedule_page``; the server requires one form.

        Returns a date-keyed map; ``slotId`` feeds
        :meth:`AppointmentsResource.reserve`.
        """
        return self._http.send(
            _spec.slot_schedule(doctor_id, schedule_date, schedule_step, schedule_page)
        )


class AppointmentsResource:
    """Appointment lifecycle.

    The patient is supplied inline as ``user`` — there is no session in this mode.
    On write the server materialises the patient inside your company.

    **Payment is never taken through the API.** ``reserve`` returns a ``url`` for
    the patient to complete agreements and payment in a browser; use
    ``without_agreement=True`` plus :meth:`create` when your own flow already
    collected them.
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
        """Hold an online slot.

        Default: returns ``{"url", "hash"}`` — hand ``url`` to the patient.
        With ``without_agreement=True``: returns ``{"hash", …, "reservationExpired"}``
        for you to confirm with :meth:`create` before the hold expires.
        """
        return self._http.send(_spec.reserve(slot_id, doctor_id, user, without_agreement))

    def instant_reserve(self, user: Patient) -> Any:
        """Instant reservation — no slot; the server picks an available doctor."""
        return self._http.send(_spec.instant_reserve(user))

    def create(self, hash_: str, outher_process_id: int | str) -> Any:
        """Turn a reservation into a confirmed appointment. Both arguments come
        from the reservation response."""
        return self._http.send(_spec.create_appointment(hash_, outher_process_id))

    def create_without_slot(
        self,
        doctor_id: int | str,
        start_date: str,
        finish_date: str,
        user: Patient,
        *,
        is_outher_doctor: int | None = None,
    ) -> Any:
        """Book a free-form range outside the slot grid, for integrations running
        their own calendar."""
        return self._http.send(
            _spec.appointment_without_slot(
                doctor_id, start_date, finish_date, user, is_outher_doctor
            )
        )

    def cancel_without_slot(self, lookup: dict[str, Any]) -> Any:
        """Cancel an appointment created with :meth:`create_without_slot` — and
        only those; ones confirmed through :meth:`create` are not cancellable here.

        Address it either by process (``hash`` + ``outherProcessId``) or by
        coordinates (``doctorId`` + ``appointmentDate`` + ``isOutherDoctor``).
        """
        return self._http.send(_spec.cancel_without_slot(lookup))

    def list(
        self, phone_number: str, page: int | str | None = None, type_: str | None = None
    ) -> Any:
        """The appointments **you** created for that phone number, not the
        patient's history across the platform. ``type_``: ``normal`` / ``instant``."""
        return self._http.send(_spec.appointment_list(phone_number, page, type_))

    def info(self, lookup: dict[str, Any]) -> Any:
        """One appointment; same lookup shape as :meth:`cancel_without_slot`."""
        return self._http.send(_spec.appointment_info(lookup))

    def check_doctor(self, doctor_id: int | str, is_outher_doctor: int) -> Any:
        """Whether a doctor is bookable through your integration. Fails with 501
        when they are not — call it before offering a doctor."""
        return self._http.send(_spec.check_doctor(doctor_id, is_outher_doctor))


class DietsResource:
    """Diet lists recorded for a patient **inside your own company**.
    Lists written by other clinics are not visible here."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, patient: Patient, page: int | str | None = None) -> Any:
        """Page size is fixed to 20 server-side."""
        return self._http.send(_spec.diet_list(patient, page))

    def detail(self, patient: Patient, list_id: int | str) -> Any:
        """``list_id`` comes from :meth:`list`."""
        return self._http.send(_spec.diet_detail(patient, list_id))


class LaboratoryResource:
    """Laboratory catalogue (global, static) and results (your company only).

    Ordering a test is not available here — it creates a financial record.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def catalog(self) -> Any:
        return self._http.send(_spec.lab_catalog())

    def catalog_detail(self, test_id: int | str) -> Any:
        """Prices are the plain list prices — the patient-side discount pass does
        not apply here."""
        return self._http.send(_spec.lab_catalog_detail(test_id))

    def results(self, patient: Patient, page: int | str | None = None) -> Any:
        """Ids returned here are accepted verbatim by :meth:`result_detail`; a
        ``-lab`` suffix marks a TmcLab order group, a plain number an HBYS lab
        request."""
        return self._http.send(_spec.lab_results(patient, page))

    def result_detail(self, patient: Patient, test_id: int | str) -> Any:
        return self._http.send(_spec.lab_result_detail(patient, test_id))


class MeasuresResource:
    """Health measurements.

    **Scope:** written into and read from **your own company**. Values the patient
    entered in the Bulutklinik mobile app are not visible here, and a value you
    write does not appear in their app — a consequence of tenant isolation, not a
    bug.

    Writes take the descriptive ``patient`` shape (created if absent); reads and
    edits take the lighter reference.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def last(self, patient: Patient) -> Any:
        """Most recent value of every measurement type."""
        return self._http.send(_spec.last_measures(patient))

    def list(
        self,
        patient: Patient,
        type_: str,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        """``glucose_type`` applies to ``glucose`` only (0=fasting, 1=postprandial)."""
        return self._http.send(_spec.measures_list(patient, type_, page, glucose_type))

    def graph(
        self,
        patient: Patient,
        type_: str,
        period: int,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        """``period``: 1=day, 2=week, 3=month, 4=year."""
        return self._http.send(_spec.measures_graph(patient, type_, period, page, glucose_type))

    def add_list(self, patient: Patient, data: MeasureRows) -> Any:
        """Write several measurements of mixed types in one transaction. Max 200 rows."""
        return self._http.send(_spec.add_measures(patient, data))

    def add(self, patient: Patient, type_: str, fields: dict[str, Any]) -> Any:
        return self._http.send(_spec.add_measure(patient, type_, fields))

    def update(
        self, patient: Patient, type_: str, measure_id: int | str, fields: dict[str, Any]
    ) -> Any:
        """``measure_id`` comes from :meth:`list`."""
        return self._http.send(_spec.update_measure(patient, type_, measure_id, fields))

    def delete(self, patient: Patient, type_: str, measure_id: int | str) -> Any:
        return self._http.send(_spec.delete_measure(patient, type_, measure_id))

    def health_information(
        self,
        *,
        identity: str | None = None,
        phone_number: str | None = None,
        data: MeasureRows,
    ) -> Any:
        """Legacy bulk submission for ``teusan`` integrations.

        .. deprecated::
            Requires the ``teusan`` scope instead of ``apiouther``, takes a flat
            ``identity`` + ``phone_number`` instead of ``patient``, and writes into
            the shared consumer tenant rather than your own company — so the
            values are not readable through :meth:`last` / :meth:`list`. Prefer
            :meth:`add_list`.
        """
        return self._http.send(_spec.health_information(identity, phone_number, data))

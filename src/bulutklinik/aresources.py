"""Asynchronous resource groups — mirror of :mod:`bulutklinik.resources`.

Same builders, same request shapes; only the await boundary differs. See the sync
counterparts for the behavioural documentation.
"""

from __future__ import annotations

from typing import Any

from . import _spec
from ._http import AsyncHttpClient
from .resources import MeasureRows, Patient

__all__ = [
    "AsyncAppointmentsResource",
    "AsyncDietsResource",
    "AsyncDoctorsResource",
    "AsyncLaboratoryResource",
    "AsyncMeasuresResource",
    "AsyncSlotsResource",
    "MeasureRows",
    "Patient",
]


class AsyncDoctorsResource:
    """Async counterpart of :class:`bulutklinik.resources.DoctorsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def search(
        self,
        search_params: dict[str, Any],
        current_page: int = 1,
        order_params: list[str] | None = None,
    ) -> Any:
        return await self._http.send(_spec.doctor_search(search_params, current_page, order_params))

    async def branches(self) -> Any:
        return await self._http.send(_spec.branches())

    async def detail(self, doctor_id: int | str) -> Any:
        return await self._http.send(_spec.doctor_detail(doctor_id))

    async def locations(self) -> Any:
        """City list. Global catalogue — not scoped to your company."""
        return await self._http.send(_spec.locations())


class AsyncSlotsResource:
    """Async counterpart of :class:`bulutklinik.resources.SlotsResource`."""

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
            _spec.slot_schedule(doctor_id, schedule_date, schedule_step, schedule_page)
        )


class AsyncAppointmentsResource:
    """Async counterpart of :class:`bulutklinik.resources.AppointmentsResource`."""

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
        return await self._http.send(_spec.reserve(slot_id, doctor_id, user, without_agreement))

    async def instant_reserve(self, user: Patient) -> Any:
        return await self._http.send(_spec.instant_reserve(user))

    async def create(self, hash_: str, outher_process_id: int | str) -> Any:
        return await self._http.send(_spec.create_appointment(hash_, outher_process_id))

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
            _spec.appointment_without_slot(
                doctor_id, start_date, finish_date, user, is_outher_doctor
            )
        )

    async def cancel_without_slot(self, lookup: dict[str, Any]) -> Any:
        return await self._http.send(_spec.cancel_without_slot(lookup))

    async def list(
        self, phone_number: str, page: int | str | None = None, type_: str | None = None
    ) -> Any:
        return await self._http.send(_spec.appointment_list(phone_number, page, type_))

    async def info(self, lookup: dict[str, Any]) -> Any:
        return await self._http.send(_spec.appointment_info(lookup))

    async def check_doctor(self, doctor_id: int | str, is_outher_doctor: int) -> Any:
        return await self._http.send(_spec.check_doctor(doctor_id, is_outher_doctor))


class AsyncDietsResource:
    """Async counterpart of :class:`bulutklinik.resources.DietsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self, patient: Patient, page: int | str | None = None) -> Any:
        return await self._http.send(_spec.diet_list(patient, page))

    async def detail(self, patient: Patient, list_id: int | str) -> Any:
        return await self._http.send(_spec.diet_detail(patient, list_id))


class AsyncLaboratoryResource:
    """Async counterpart of :class:`bulutklinik.resources.LaboratoryResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def catalog(self) -> Any:
        return await self._http.send(_spec.lab_catalog())

    async def catalog_detail(self, test_id: int | str) -> Any:
        return await self._http.send(_spec.lab_catalog_detail(test_id))

    async def results(self, patient: Patient, page: int | str | None = None) -> Any:
        return await self._http.send(_spec.lab_results(patient, page))

    async def result_detail(self, patient: Patient, test_id: int | str) -> Any:
        return await self._http.send(_spec.lab_result_detail(patient, test_id))


class AsyncMeasuresResource:
    """Async counterpart of :class:`bulutklinik.resources.MeasuresResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def last(self, patient: Patient) -> Any:
        return await self._http.send(_spec.last_measures(patient))

    async def list(
        self,
        patient: Patient,
        type_: str,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        return await self._http.send(_spec.measures_list(patient, type_, page, glucose_type))

    async def graph(
        self,
        patient: Patient,
        type_: str,
        period: int,
        page: int | str | None = None,
        glucose_type: int | None = None,
    ) -> Any:
        return await self._http.send(
            _spec.measures_graph(patient, type_, period, page, glucose_type)
        )

    async def add_list(self, patient: Patient, data: MeasureRows) -> Any:
        return await self._http.send(_spec.add_measures(patient, data))

    async def add(self, patient: Patient, type_: str, fields: dict[str, Any]) -> Any:
        return await self._http.send(_spec.add_measure(patient, type_, fields))

    async def update(
        self, patient: Patient, type_: str, measure_id: int | str, fields: dict[str, Any]
    ) -> Any:
        return await self._http.send(_spec.update_measure(patient, type_, measure_id, fields))

    async def delete(self, patient: Patient, type_: str, measure_id: int | str) -> Any:
        return await self._http.send(_spec.delete_measure(patient, type_, measure_id))

    async def health_information(
        self,
        *,
        identity: str | None = None,
        phone_number: str | None = None,
        data: MeasureRows,
    ) -> Any:
        """.. deprecated:: Prefer :meth:`add_list`; see the sync counterpart."""
        return await self._http.send(_spec.health_information(identity, phone_number, data))

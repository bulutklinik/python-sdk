"""End-to-end partner example: check a doctor -> slots -> reserve, plus a
health-measures read/write round trip.

Provide credentials via env: BK_PARTNER_TOKEN, BK_DOCTOR_ID, BK_PATIENT_PHONE,
BK_PATIENT_TCKN. Run: python examples/flow.py
"""

from __future__ import annotations

import os

from bulutklinik import BulutklinikClient


def main() -> None:
    with BulutklinikClient(
        environment="test",
        partner_token=os.environ.get("BK_PARTNER_TOKEN", ""),
    ) as client:
        # 1. Discovery. Needs no patient data, so it is the fastest way to prove
        #    the token and base URL are right.
        branches = client.doctors.branches()
        print("branches:", len(branches))

        doctor_id = int(os.environ.get("BK_DOCTOR_ID", "8282"))
        print("bookable through this integration:", client.appointments.check_doctor(doctor_id, 0))

        # 2. Availability. `slotId` from here feeds the reservation.
        schedule = client.slots.schedule(doctor_id, schedule_date="2026-08-01")
        print("slots:", schedule)

        # 3. Booking. The patient is named inline — there is no session.
        #
        #    `reserve` alone returns a `url` to hand to the patient for
        #    agreements and payment. `without_agreement=True` returns a `hash`
        #    for you to confirm yourself, as below.
        user = {
            "name": "Ada",
            "surname": "Lovelace",
            "phoneNumber": os.environ.get("BK_PATIENT_PHONE", "+905551112233"),
            "identityNumber": os.environ.get("BK_PATIENT_TCKN"),
        }

        first_day = next(iter(schedule.values()), [])
        if first_day:
            held = client.appointments.reserve(
                first_day[0]["slotId"], doctor_id, user, without_agreement=True
            )
            print("held until", held["reservationExpired"])
            # `outherProcessId` arrives alongside `hash` in the same response:
            # client.appointments.create(held["hash"], outher_process_id)

        # 4. Measurements. Writes create the patient in your company if absent;
        #    reads only ever look inside your company.
        client.measures.add_list(
            user,
            [
                {
                    "type": "tension",
                    "date_time": "2026-06-17 09:30",
                    "hypertension": 120,
                    "hypotension": 80,
                },
                {"type": "pulse", "date_time": "2026-06-17 09:31", "pulse": 72},
            ],
        )
        print("measures submitted")

        print("latest:", client.measures.last({"phoneNumber": user["phoneNumber"]}))


if __name__ == "__main__":
    main()

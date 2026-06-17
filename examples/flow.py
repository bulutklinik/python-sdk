"""End-to-end example: login -> search -> slots, plus health measures.

Provide credentials via env: BK_CLIENT_ID, BK_CLIENT_SECRET, BK_USERNAME,
BK_PASSWORD, BK_DOCTOR_ID. Run: python examples/flow.py
"""

from __future__ import annotations

import os

from bulutklinik import BulutklinikClient


def main() -> None:
    with BulutklinikClient(
        environment="test",
        client_id=os.environ.get("BK_CLIENT_ID", ""),
        client_secret=os.environ.get("BK_CLIENT_SECRET", ""),
    ) as client:
        login = client.auth.connect(
            os.environ.get("BK_USERNAME", ""),
            os.environ.get("BK_PASSWORD", ""),
            "email",
        )

        if login.two_factor_required:
            print("2FA required; call connect_with_two_factor with the SMS code")
            print("response =", login.two_factor_response)
            return

        print("quickSearch:", client.doctors.quick_search("kardiyo", "interview"))

        doctor_id = int(os.environ.get("BK_DOCTOR_ID", "8282"))
        print("slots:", client.slots.schedule(doctor_id, "interview"))

        client.measures.add_list(
            [
                {
                    "type": "tension",
                    "date_time": "2026-06-17 09:30",
                    "hypertension": 120,
                    "hypotension": 80,
                },
                {"type": "pulse", "date_time": "2026-06-17 09:31", "pulse": 72},
            ]
        )
        print("measures submitted")

        client.auth.disconnect()


if __name__ == "__main__":
    main()

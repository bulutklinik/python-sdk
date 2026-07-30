# bulutklinik-sdk

Official Bulutklinik **partner** API SDK for Python. Sync **and** async (httpx),
fully typed (`py.typed`), Python 3.10+.

This is a single-persona SDK: every call runs on the company-scoped `/outher`
surface with the partner token issued for your integration. You act on the
patients of **your own company**, and the patient is named inline on each
request — there is no login and no session. See [`DESIGN.md`](./DESIGN.md) for
the full wire contract.

> **1.0.0 is a breaking release.** The patient persona (login, registration,
> payments, AI analysis, address book) has been removed and the former
> `client.partner.*` namespace was lifted to the client root. See
> [CHANGELOG.md](./CHANGELOG.md) and DESIGN.md §12 for the migration.

## Install

```bash
pip install bulutklinik-sdk
```

## Quick start (sync)

```python
from bulutklinik import BulutklinikClient

with BulutklinikClient(
    environment="production",  # "production" | "test" | "local"
    api_version="v3",          # "v3" (default) | "v4"
    partner_token="…",
) as client:
    # 1) Find a doctor you can book
    result = client.doctors.search(
        search_params={"withFreeText": "kardiyoloji"},
        order_params=["slot"],
    )
    doctor_id = result["foundDoctors"][0]["doctor_id"]

    # 2) Free slots
    schedule = client.slots.schedule(doctor_id, schedule_date="2026-08-01")
    slot = next(iter(schedule.values()))[0]

    # 3) Hold it for a patient — named inline, no session
    held = client.appointments.reserve(
        slot["slotId"],
        doctor_id,
        {"name": "Ada", "surname": "Lovelace", "phoneNumber": "+905551112233"},
        without_agreement=True,
    )

    # 4) Confirm before held["reservationExpired"] passes
    client.appointments.create(held["hash"], held["outherProcessId"])
```

## Quick start (async)

```python
from bulutklinik import AsyncBulutklinikClient

async with AsyncBulutklinikClient(environment="production", partner_token="…") as client:
    result = await client.doctors.search(search_params={"withFreeText": "kardiyoloji"})
```

## Services

28 endpoints across six groups. The async client exposes the same methods
(awaitable) under the same names.

| Group                 | Methods |
|-----------------------|---------|
| `client.doctors`      | `search`, `branches`, `detail`, `locations` |
| `client.slots`        | `schedule` |
| `client.appointments` | `reserve`, `instant_reserve`, `create`, `create_without_slot`, `cancel_without_slot`, `list`, `info`, `check_doctor` |
| `client.measures`     | `last`, `list`, `graph`, `add_list`, `add`, `update`, `delete`, `health_information` |
| `client.laboratory`   | `catalog`, `catalog_detail`, `results`, `result_detail` |
| `client.diets`        | `list`, `detail` |

`appointments.reserve(..., without_agreement=True)` covers the second reservation
endpoint, so the nine documented appointment endpoints map to eight methods.

## Naming a patient

There is no session, so every patient-scoped call carries the patient in its
body — never in the URL, since a TCKN in a path segment would land in access
logs, proxy logs and error breadcrumbs.

**Reads** take a light reference. The server looks only inside your own company
and never creates anything:

```python
client.measures.last({"identityNumber": "12345678901"})
client.diets.list({"phoneNumber": "+905551112233"})
```

`identityNumber` is primary; `phoneNumber` is a fallback accepted only when it
matches exactly one patient (the column is not unique — family members share
numbers). A patient you have never treated resolves to "not found", with the same
message as "not yours" so the endpoint cannot be used to probe for TCKNs.

**Writes** take the descriptive shape, because the patient is created inside your
company if absent:

```python
client.measures.add_list(
    {"name": "Ada", "surname": "Lovelace", "phoneNumber": "+905551112233"},
    [{"type": "pulse", "date_time": "2026-06-17 09:31", "pulse": 72}],
)
```

## Booking

Two flows, depending on who collects the agreements and the payment:

```python
# (A) Hand off to the patient — returns a browser `url` for agreements + payment.
held = client.appointments.reserve(slot_id, doctor_id, user)
print(held["url"])

# (B) You already collected them — returns a `hash` to confirm yourself.
held = client.appointments.reserve(slot_id, doctor_id, user, without_agreement=True)
client.appointments.create(held["hash"], outher_process_id)
```

**Payment is never taken through the API.** No partner endpoint produces a
financial record; the browser hand-off in (A) is where payment happens. The SDK
returns `url` verbatim and never opens or follows it.

`create_without_slot` books a free-form range outside the slot grid, for
integrations running their own calendar; `cancel_without_slot` reverses it — and
only it.

## Authentication

The partner token is **issued out of band** through the Bulutklinik Developer
Platform. It behaves like an API key: there is no login method, and the SDK
cannot renew it.

```python
client = BulutklinikClient(partner_token="…")
```

The token is read from a token store on **every** request, so a long-running
process can pick up a newly issued one without being rebuilt. Implement
`bulutklinik.TokenStore` and pass it via `token_store=…`:

```python
class VaultTokenStore:
    def get_token(self) -> str | None: ...
    def set_token(self, token: str | None) -> None: ...
    def clear(self) -> None: ...

client = BulutklinikClient(token_store=VaultTokenStore())

# …or rotate the default in-memory store in place:
client.token_store.set_token(newly_issued_token)
```

Pass `partner_token` **or** `token_store`, not both — the constructor raises
`ValueError` rather than guessing which one you meant.

### When the token expires

Tokens last about 30 days. An expired one comes back as `401` / `resultType 4`;
the SDK raises `AuthenticationError` and does **not** retry — there is nothing to
refresh. Recovery is operational: obtain a newly issued token and write it into
the store.

> This is the one behaviour that changed meaning in 1.0.0. On the patient SDK
> `resultType 4` meant "the SDK will fix this silently". Here it means the opposite.

An `AuthorizationError` (403) means the credential itself is wrong — either the
token lacks the `apiouther` scope, or it resolves to a user with no company. The
company boundary comes from the token, never from request input, so retrying with
different body parameters will not help.

## Health measures

```python
ref = {"identityNumber": "12345678901"}

# Write several measurements at once (max 200 per call, one transaction)
client.measures.add_list(patient, [
    {"type": "tension", "date_time": "2026-06-17 09:30", "hypertension": 120, "hypotension": 80},
    {"type": "glucose", "date_time": "2026-06-17 09:35", "glucose": 95, "glucose_type": 0},
])

client.measures.last(ref)
client.measures.list(ref, "glucose", 1, 0)  # glucose_type 0=fasting, 1=postprandial
client.measures.graph(ref, "tension", 2)     # period 2 = weekly
```

> Measurements are written to **your own company**. A value you write does not
> appear in the patient's Bulutklinik mobile app, and values they entered there
> are not visible to you. That is tenant isolation working as intended.

`measures.health_information` is the legacy `teusan` bulk endpoint, kept for
existing integrations: it needs the `teusan` scope instead of `apiouther`, takes
a flat `identity` + `phone_number` instead of `patient`, and writes into the
shared consumer tenant. The API currently matches on `phone_number` only (a
server-side bug nulls `identity` during validation); pass both for forward
compatibility. Prefer `add_list` for anything new.

## Laboratory & diets

```python
ref = {"identityNumber": "12345678901"}

# Global, static catalogue — no patient context
catalog = client.laboratory.catalog()
group = client.laboratory.catalog_detail(7)

# Results for a patient in your company. Ids may carry a "-lab" suffix; pass them back verbatim.
results = client.laboratory.results(ref)          # or .results(ref, 2)
detail = client.laboratory.result_detail(ref, "4821-lab")

# Diet lists written by a dietitian. Page size is fixed to 20 server-side.
diets = client.diets.list(ref)
plan = client.diets.detail(ref, diets["foundDiets"][0]["list_id"])
```

Ordering a lab test is not available to partners — it creates a financial record.

## Escape hatch

Not every endpoint has a typed method. `client.request` reuses the same
transport, so headers, envelope unwrapping and typed errors all still apply:

```python
data = client.request("GET", "/outher/somethingNew")

# "public" reaches unauthenticated endpoints outside the partner surface,
# e.g. the city/district catalogue that feeds address forms.
config = client.request("GET", "/general/getConfig", auth="public")
```

## Errors

All errors subclass `bulutklinik.BulutklinikError`:

`TransportError` (network) · `ApiError` → `ValidationError` (422),
`AuthenticationError` (401 / revoked / expired), `AuthorizationError` (403),
`NotFoundError` (404), `RateLimitError` (429, `.retry_after`).
Attributes: `http_status`, `result_type`, `error_type`, `data`, `method`, `path`,
`retry_after`.

```python
from bulutklinik import RateLimitError, ValidationError

try:
    client.measures.last(ref)
except RateLimitError as exc:
    print("retry after", exc.retry_after)
except ValidationError as exc:
    print("invalid:", exc.data)
```

Note that `/outher` reports most business-rule failures as HTTP **`501`** with
`resultType 1` — "patient not found in your company", "slot no longer free",
"doctor not bookable through your integration". It is not a server crash; read
the message.

## Development

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

## License

MIT

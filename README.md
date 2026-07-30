# bulutklinik-sdk

Official Bulutklinik **partner** API SDK for Python. Sync **and** async (httpx),
fully typed (`py.typed`), Python 3.10+.

This is a single-persona SDK: every call runs on the company-scoped `/outher`
surface with the partner token issued for your integration. You act on the
patients of **your own company**, and the patient is named inline on each
request — there is no patient session. See [`DESIGN.md`](./DESIGN.md) for
the full wire contract.

> **1.1.0 restores `client.auth`.** 1.0.x wrongly assumed the partner token could
> only be issued out of band; it is in fact minted by `connectApi` from your
> portal credentials, and it is refreshable. Existing 1.0.x code that passes
> `partner_token` keeps working. See [CHANGELOG.md](./CHANGELOG.md).

## Install

```bash
pip install bulutklinik-sdk
```

## Quick start (sync)

```python
from bulutklinik import BulutklinikClient

with BulutklinikClient(
    environment="production",  # "production" | "test" | "local"
    api_version="v3",  # "v3" (default) | "v4"
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

31 endpoints across seven groups. The async client exposes the same methods
(awaitable) under the same names.

| Group                 | Methods |
|-----------------------|---------|
| `client.auth`         | `connect`, `refresh`, `disconnect` |
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

Your portal application issues a **client ID**, a **client secret** and a
project-specific **service identity**; the password is the one you set when
registering on the portal. `auth.connect` exchanges them for an access token and
a refresh token:

```python
client = BulutklinikClient(client_id="…", client_secret="…")

client.auth.connect(
    "svc@your-app.bulutklinik",
    "your-portal-password",
    login_mode="email",  # default
)
```

The granted scope comes from the credentials, not the request — a partner
application is provisioned with `apiouther`, which is what makes `/outher`
reachable. Already holding a token? Pass `partner_token=…` and skip the login.

### Refresh

Access tokens last ~30 days, refresh tokens ~130. You do not normally call
`refresh` yourself: on a `401` / `resultType 4` the SDK refreshes once and retries
the original request.

```python
client.auth.refresh()  # only useful to refresh ahead of time
client.auth.disconnect()  # revokes both tokens and clears the store
```

If the refresh fails — or there is no refresh token because you supplied a bare
`partner_token` — the call raises `AuthenticationError` and you should
`auth.connect` again.

### Token storage

Tokens are read from a token store on **every** request, so a long-running
process can rotate them without being rebuilt. Implement
`bulutklinik.RefreshTokenStore` to persist both:

```python
class VaultTokenStore:
    def get_token(self) -> str | None: ...
    def set_token(self, token: str | None) -> None: ...
    def get_refresh_token(self) -> str | None: ...
    def set_refresh_token(self, token: str | None) -> None: ...
    def clear(self) -> None: ...


client = BulutklinikClient(token_store=VaultTokenStore(), client_id="…", client_secret="…")
```

The two refresh methods are **optional**. A plain `TokenStore` — the 1.0.x shape,
access token only — still works; the SDK then keeps the refresh token in memory,
so a process restart needs `auth.connect` rather than a refresh.

An `AuthorizationError` (403) means the credential itself is wrong: either the
granted scope does not include `apiouther`, or the account has no company. The
company boundary comes from the token, never from request input.

## Health measures

```python
ref = {"identityNumber": "12345678901"}

# Write several measurements at once (max 200 per call, one transaction)
client.measures.add_list(
    patient,
    [
        {
            "type": "tension",
            "date_time": "2026-06-17 09:30",
            "hypertension": 120,
            "hypotension": 80,
        },
        {"type": "glucose", "date_time": "2026-06-17 09:35", "glucose": 95, "glucose_type": 0},
    ],
)

client.measures.last(ref)
client.measures.list(ref, "glucose", 1, 0)  # glucose_type 0=fasting, 1=postprandial
client.measures.graph(ref, "tension", 2)  # period 2 = weekly
```

> Measurements are written to **your own company**. A value you write does not
> appear in the patient's Bulutklinik mobile app, and values they entered there
> are not visible to you. That is tenant isolation working as intended.

`measures.health_information` is the legacy `teusan` bulk endpoint, kept for
existing integrations: it needs the `teusan` scope instead of `apiouther`, takes
a flat `identity` + `phone_number` instead of `patient`, and writes into the
shared consumer tenant. Its patient matching is an **OR**, and it is loose: the lookup is
`identity OR phoneNumber` against the *global* user table and takes the first
row, so a phone number alone can resolve someone whose TCKN differs from the one
you sent. Send both, but do not assume they are checked as a pair — the
`apiouther` reads above do the opposite, scoping to your company and failing
closed on ambiguity. Prefer `add_list` for anything new.

## Laboratory & diets

```python
ref = {"identityNumber": "12345678901"}

# Global, static catalogue — no patient context
catalog = client.laboratory.catalog()
group = client.laboratory.catalog_detail(7)

# Results for a patient in your company. Ids may carry a "-lab" suffix; pass them back verbatim.
results = client.laboratory.results(ref)  # or .results(ref, 2)
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

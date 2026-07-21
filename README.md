# bulutklinik-sdk

Official Bulutklinik API SDK for Python. Sync **and** async (httpx), fully typed
(`py.typed`), Python 3.9+.

Covers the patient flow: **auth, doctor search, slots, appointments, payments,
and health measures**. See [`DESIGN.md`](./DESIGN.md) for the full wire contract.

## Install

```bash
pip install bulutklinik-sdk
```

## Quick start (sync)

```python
from bulutklinik import BulutklinikClient

with BulutklinikClient(
    environment="production",  # "production" | "test" | "local"
    client_id="…",
    client_secret="…",
) as client:
    # 1) Log in (tokens are stored automatically)
    login = client.auth.connect("patient@example.com", "•••••••", "email")

    if login.two_factor_required:
        client.auth.connect_with_two_factor("123456", login.two_factor_response)

    # 2) Find a doctor
    result = client.doctors.search(
        search_params={"withFreeText": "kardiyoloji"},
        order_params=["slot"],
        other_params=["isInterviewable"],
    )

    # 3) Slots, then 4) reserve ("YYYY-MM-DD HH:mm")
    doctor_id = result["foundDoctors"][0]["doctor_id"]
    slots = client.slots.schedule(doctor_id, "interview")
    client.appointments.reserve_interview(doctor_id, "2026-06-20 14:30")
```

## Quick start (async)

```python
from bulutklinik import AsyncBulutklinikClient

async with AsyncBulutklinikClient(environment="production", client_id="…", client_secret="…") as client:
    await client.auth.connect("patient@example.com", "•••••••", "email")
    result = await client.doctors.search(search_params={"withFreeText": "kardiyoloji"})
```

## Services

| Group                   | Methods |
|-------------------------|---------|
| `client.auth`           | `connect`, `connect_with_two_factor`, `verify_registration`, `confirm_registration_email`, `register`, `verify_registration_social`, `register_social`, `forgot_password`, `reset_password`, `refresh`, `disconnect` |
| `client.doctors`        | `branches`, `locations`, `quick_search`, `search`, `detail` |
| `client.slots`          | `schedule` |
| `client.appointments`   | `reserve_interview`, `add_physical`, `cancel`, `list`, `reservations` |
| `client.payments`       | `check_discount_code`, `get_cards`, `save_card`, `pay`, `delete_card` |
| `client.measures`       | `add_list`, `add`, `update`, `delete`, `last`, `list`, `graph`, `partner_health_information` |
| `client.skin`           | `analyze` |
| `client.meals`          | `analyze` |
| `client.laboratory`     | `results`, `result_detail`, `catalog`, `catalog_detail`, `order` |
| `client.diets`          | `list`, `detail` |
| `client.addresses`      | `list`, `add`, `update`, `delete` |

The async client exposes the same methods (awaitable) under the same names.

## Authentication & tokens

- `connect` / `connect_with_two_factor` / `register` store the access + refresh
  tokens automatically.
- On a `401` (or `resultType 4`), the SDK silently refreshes once and retries.
- Provide a custom token store by implementing `bulutklinik.TokenStore` and
  passing it via `token_store=…`.

## Payments (3-D Secure)

`payments.pay(...)` returns a dict with `payment3DUrl` on a 3DS flow. Open that URL
in a browser; the bank → server callback completes the capture. The SDK never
opens or parses the URL.

## Health measures

```python
client.measures.add_list([
    {"type": "tension", "date_time": "2026-06-17 09:30", "hypertension": 120, "hypotension": 80},
    {"type": "glucose", "date_time": "2026-06-17 09:35", "glucose": 95, "glucose_type": 0},
])

client.measures.last()
client.measures.list("glucose", 1, 0)  # glucose_type 0=fasting, 1=postprandial
client.measures.graph("tension", 2, 1)  # period 2 = weekly
```

> The partner endpoint (`partner_health_information`) uses `partner_token` from
> the client config. The API currently matches the patient by `phone_number`;
> pass both `identity` and `phone_number` for forward compatibility.

## AI image analysis

```python
# "Cildimde Neyim Var" — analyze one or more skin photos (base64)
result = client.skin.analyze([{"image": b64}])
for s in result["status"]:
    print(s["label"], s["comment"], s["possible_icd"])
    # s["case_detail"] can be forwarded verbatim as a payment's case_detail

# Meal photo → calorie/nutrition estimate
meal = client.meals.analyze(
    image=b64,
    portion_size="medium",  # small | medium | large | custom
    meal_type="lunch",       # breakfast | lunch | dinner | snack
    # portion_grams=300,     # required when portion_size is "custom"
    # note="az yağlı",
)
print(meal["status"]["comment"])
```

## Laboratory & diets

```python
# Lab results (page optional; omit for page 1). Result ids may carry a "-lab" suffix.
results = client.laboratory.results()          # or .results(2)
detail = client.laboratory.result_detail("4821-lab")

# Orderable test catalog, then pre-order (all three ids required)
catalog = client.laboratory.catalog()
group = client.laboratory.catalog_detail(7)
order = client.laboratory.order(test_id=12, address_id=34, laboratory_id=56)
print(order["preOrderId"])

# Diet lists written by the dietitian (JSON only)
diets = client.diets.list()                    # or .list(2)
plan = client.diets.detail(diets["foundDiets"][0]["list_id"])
```

## Errors

All errors subclass `bulutklinik.BulutklinikError`:

`TransportError` (network) · `ApiError` → `ValidationError` (422),
`AuthenticationError` (401 / logout), `AuthorizationError` (403),
`NotFoundError` (404), `RateLimitError` (429, `.retry_after`).
Attributes: `http_status`, `result_type`, `error_type`, `data`, `method`, `path`,
`retry_after`.

```python
from bulutklinik import RateLimitError, ValidationError

try:
    client.payments.pay(doctor_id, "2026-06-20 14:30", is_3d=True, terms_accept=True, card_id=5)
except RateLimitError as exc:
    print("retry after", exc.retry_after)
except ValidationError as exc:
    print("invalid:", exc.data)
```

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

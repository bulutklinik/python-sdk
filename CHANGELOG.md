# Changelog

All notable changes to `bulutklinik-sdk` are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1]

Documentation and contract corrections found by auditing the SDKs against the
API source before release. No wire change.

### Fixed

- `doctors.search` no longer lets `searchParams` default to an empty map. The
  server rule is `required|array` and PHP's `required` rejects an empty array, so
  `{}` was a guaranteed `422` rather than an unfiltered search.
- Corrected the `measures.health_information` note. The defect it described — the API
  nulling `identity` before the patient lookup — was fixed API-side on
  2026-07-21. What actually remains is looser and worth knowing: the lookup is
  `identity OR phoneNumber` against the global user table and takes the first
  row, so a phone number alone can resolve a person whose TCKN differs from the
  one you sent.

## [1.0.0]

The SDK becomes **partner-only**. Everything that required a patient login is
gone; the company-scoped `/outher` surface that shipped under `client.partner.*`
in 0.6.0 is now the client root. See `DESIGN.md` §12 for the full migration.

### Changed — BREAKING

- **`client.partner.<group>` → `client.<group>`.** The six partner groups
  (`doctors`, `slots`, `appointments`, `measures`, `laboratory`, `diets`) moved to
  the root on both the sync and async clients. Their paths, bodies and behaviour
  are unchanged — this is a rename. Resource classes lost the `Partner` prefix
  (`PartnerDoctorsResource` → `DoctorsResource`, `AsyncPartnerDoctorsResource` →
  `AsyncDoctorsResource`); `PartnerNamespace` / `AsyncPartnerNamespace` are gone.
- **`TokenStore` now holds one partner token**: `get_token` / `set_token` /
  `clear` replace `get_access_token` / `get_refresh_token` / `set_tokens`.
  `InMemoryTokenStore` takes the token as its single argument.
- **`partner_token` is now the client's credential** and is required for every
  call. Passing both `partner_token` and `token_store` raises `ValueError` at
  construction rather than silently picking one.
- **No silent refresh.** A `401` / `resultType 4` raises `AuthenticationError`
  with no retry — a partner token is issued out of band and cannot be renewed
  from here. Install a newly issued token in the token store instead.
- **A missing token fails before dispatch** with `AuthenticationError`, rather
  than sending an anonymous request that returns an opaque `401`.
- **Escape hatch `auth` defaults to `"partner"`**; the `"bearer"` mode no longer
  exists. `"public"` remains, for unauthenticated endpoints outside the surface.
- `_BASE_URLS` → `API_ROOTS` (now version-less); `resolve_base_url` takes an
  `api_version` argument.
- `measures.partner_health_information` → `measures.health_information`.
- `doctors.search` no longer accepts `other_params` / `per_page_limit`, and
  `order_params` no longer accepts `point` — the `/outher` search has neither.

### Added

- **`api_version="v3" | "v4"`** client option (plus an `ApiVersion` enum). Every
  path is version-agnostic, so targeting v4 is configuration, not a code change.
  Default stays `v3`.

### Removed

- `client.auth` (all 11 methods), `client.payments` (5), `client.skin`,
  `client.meals`, `client.addresses` (4) — no company-scoped equivalent exists.
- The patient-persona `doctors` / `slots` / `appointments` / `measures` /
  `laboratory` / `diets` that lived at the root in 0.6.0.
- `client_id` / `client_secret` client options.
- The `LoginResult` model and the `bulutklinik.models` module.

## [0.6.0]

### Added

- `client.auth.confirm_registration_email(...)` (sync + async) — the **required**
  e-mail-branch middle step of registration (`POST /patients/emailConfirmationRegister`).
  A headerless SDK caller always gets `confirmationType == "email"` from
  `verify_registration`; confirm the e-mailed code here to receive the SMS blob that
  `register` consumes (without it, `register` returns 501).
- Social sign-up: `client.auth.verify_registration_social(...)` +
  `client.auth.register_social(...)` (both public; `register_social` does not
  auto-login — call `connect(..., login_mode="social")` after).
- Password reset: `client.auth.forgot_password(...)` + `client.auth.reset_password(...)`.
- `client.appointments.list(page=None)` (`GET /patients/userAppointments`) — the source of
  the `event_id` that `cancel` requires — and `client.appointments.reservations()`.
- New `client.addresses` group (`list`/`add`/`update`/`delete`) over `/patients/userAddress`,
  required by `laboratory.order` (which needs an `addressId`). Available on both clients.

## [0.5.0]

### Added

- `client.auth.verify_registration(...)` (sync + async) — step 1 of registration
  (`POST /patients/verifyAddingNewPatient`): sends the verification code and returns
  the encrypted `response` blob to pass to `register`. Uses the configured
  **partner** token (`auth:apiusers`, not public) and requires a browser-minted
  CAPTCHA token (`recaptcha_v2` or `captcha`).

## [0.4.0]

### Added

- `client.laboratory` — patient lab group (DESIGN.md §6.9): `results(page=None)`
  (`GET /patients/userLabTestList/{page?}`, `/{page}` omitted when None),
  `result_detail(test_id)` (`GET /patients/userLabTestDetail/{testId}`, `test_id`
  is a string and interpolated verbatim, e.g. `"4821-lab"`), `catalog()`
  (`GET /patients/allLaboratoryTests`), `catalog_detail(id)`
  (`GET /patients/laboratoryTestDetail/{id}`), and `order(test_id, address_id, laboratory_id)`
  (`POST /patients/addNewLaboratoryTest`; all three ids required).
- `client.diets` — patient diet group (DESIGN.md §6.10): `list(page=None)`
  (`GET /patients/dietLists/{page?}`, `/{page}` omitted when None) and
  `detail(list_id)` (`GET /patients/diet/{listId}`).
- The async client exposes both groups under the same names (`await client.laboratory.results(...)`,
  `await client.diets.list(...)`).

## [0.3.0]

### Added

- `client.skin.analyze(images)` — "Cildimde Neyim Var" AI skin-lesion analysis
  (`POST /patients/imageCheck`). Returns per-image lesion `label`, a Turkish AI
  `comment`, `confidence`, `possible_icd` and an opaque `case_detail` blob (which
  can be forwarded as a payment's `case_detail`).
- `client.meals.analyze(image, portion_size, meal_type, *, portion_grams=None, note=None)` —
  AI meal-photo calorie/nutrition estimation (`POST /patients/imageAnalyzeMeal`).
  The input names map to the API's snake_case body; `portion_grams` and `note`
  are sent only when provided.
- The async client exposes both under the same names (`await client.skin.analyze(...)`,
  `await client.meals.analyze(...)`).

## [0.2.0]

### Added

- `client.request(...)` escape hatch for calling any endpoint not yet covered by a
  typed resource method (DESIGN.md §7.2). Available on both the sync and async clients.

## [0.1.0]

### Added

- Initial release: `auth`, `doctors`, `slots`, `appointments`, `payments`,
  `measures` service groups over a shared transport with silent token refresh.
  Sync (`BulutklinikClient`) and async (`AsyncBulutklinikClient`) surfaces.

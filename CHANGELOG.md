# Changelog

All notable changes to `bulutklinik-sdk` are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

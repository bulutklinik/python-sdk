# Changelog

All notable changes to `bulutklinik-sdk` are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

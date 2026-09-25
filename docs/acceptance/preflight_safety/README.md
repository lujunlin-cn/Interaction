# Effective generation preflight regression

Date: 2026-09-25. Isolated tests; **external paid media requests: 0**.

The old endpoint and Settings button used test K/shot/duration/reference settings
even while the test override was disabled. A configured K=3 run was incorrectly
shown as one job, and reference counts were clipped to the test cap. An open
billing circuit was also reported as allowed whenever the paid guard was enabled.

The endpoint now estimates from effective configuration. Speculation uses normal
K/shots/duration unless the test override is enabled; opening and ending use one
shot and their phase duration under the configured cap. This is labeled an
estimate, not a locked Production plan. Explicit request numbers are labeled
manual preview and never alter settings. Unsupported counts/durations are reported
instead of silently clipped. Unresolved reference counts are null/unknown, with
caps shown separately. Guard, billing/key circuit, router circuit, credential
presence, and live route status contribute to whether a Fal request is allowed.

Settings only sends `{ "role": "h3_max" }`. Viewing a preflight does not append a
fake generation attempt to Usage Ledger.

- `backend/tests/test_generation_preflight.py`: **11 passed**, in-memory ASGI,
  no database/provider calls. Before the fix all 11 cases failed.
- `frontend/tests/preflight_settings.mjs`: **PASS**, actual React Settings at
  1920×1080 with all API responses mocked and external origins blocked. Confirms
  the request contains no inactive test knobs, three jobs are shown, references
  remain unknown, and an open circuit shows `fal_request_allowed=false`.
- Screenshot and browser result: `settings_preflight.png`, `browser.json`.

This evidence proves preview behavior, not successful paid generation or FULL E2E.

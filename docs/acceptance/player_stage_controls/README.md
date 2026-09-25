# Player stage control regression

Date: 2026-09-25. Result: **4 PASS / 0 FAIL**.

This is an isolated browser layout regression, not real H3/Decision/Runtime acceptance. The test starts Vite on port 9012, intercepts API and WebSocket traffic, and uses explicit fixtures. External paid media requests and API mutations: **0**.

Run from `frontend`: `node tests/player_stage_controls.mjs`.

The four cases cover 1920×1080 and 2560×1440, each with three Ready recommendations, with and without the failure overlay. The test verifies default application Theater in a normal browser window, Stage controls/menu bounds and hit targets, Video→Decision→Agency order, typing, HUD hover/pin/unpin, manual Theater exit with state preserved, and default Theater after leaving and returning to Player.

`browser_before_fix.json` records the reproduced controls-over-Agency failures. `browser_default_before_fix.json` records the default-Theater failures. `browser.json` and the PNGs record the passing final source.

The actual deployed historical failed Session was also inspected read-only on port 9000: see `../biohazard_full_e2e/theater_readonly.json` and matching screenshots. Its empty recommendations and absent H3 video remain honestly distinct from this fixture-driven layout test.

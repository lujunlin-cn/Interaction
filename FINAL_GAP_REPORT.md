# Final Gap Report · PRD v0.6

Final SHA：本报告所在最终提交；交付回复提供完整 SHA，使用 `git rev-parse HEAD` 核对。PRD 基线：`b055674aa0702fc1c1ed50f7c3ee62e4ea43dc88`；当前 FULL E2E Start SHA：`1eabeb6afc89e8bdcb402f5b2b452499e7089b9e`。
本报告取代此前旧SHA和“旧现状→新修复”混合结论。详细验收见 [LATEST_PRD_UX_ACCEPTANCE.md](LATEST_PRD_UX_ACCEPTANCE.md)。

## Current closure status (2026-09-25)

- **CLOSED — Character management Q109–Q112 / AT-80:** shared scope-aware Studio now supports actual reference-pack, outfit slot, pose, motion, canonical/alternate voice, version pin and Promote operations. The earlier seven-title evidence was insufficient and is superseded by `docs/acceptance/character_scope_regression/scope_regression.json` (1920×1080 A–F, persisted-state assertions, zero paid submits).
- **CLOSED — Theater controls/default entry regressions:** fresh port-9000 read-only checks at 1920×1080 and 2560×1440 reproduced and then verified repair of controls covering Agency. Four isolated browser cases pass default in-app Theater, navigation/reentry, fullscreen=false, HUD and input/session/progress preservation; `docs/acceptance/player_stage_controls/browser.json`, `docs/acceptance/biohazard_full_e2e/theater_readonly.json`. These error/fixture layout checks are not real H3 play proof.
- **Previously verified, not rerun by this isolated scope regression:** media Settings parameter chain, Developer Test Override, Paid Guard/Circuit, Usage Ledger/Preflight, pure-text Publish warning, AI-guided Drama and natural-language mechanics. Their evidence remains in the matrix. There is no blanket Q105–Q122 CLOSED claim.
- Final frontend `npm ci` / build: **PASS** (42 modules). Backend: **195 passed / 0 failed / 6 warnings**, plus compileall/pip check PASS. Service restarted **active on 9000**, served JS/CSS match final build by bytes/SHA-256; `docs/acceptance/biohazard_full_e2e/deployment_final.json`. User objects remained unchanged; existing startup seed refreshed only the two official rainy-apartment rows. Previous 63/64-pass counts remain historical.
- **CLOSED — current story parameter review and Standard UI publication:** overview/world/drama/characters/mechanics reviewed and corrected through visible controls, explicit “我已审阅” confirmation, version **0.2.0** published as `ver_00001_b26e3c`. Leon v8 / Claire v7 / Victor v7 are pinned; three snapshot IDs returned. See `docs/acceptance/biohazard_full_e2e/scenario_published_ui.json`. This is not a successful video Session.

## Remaining real-provider validation

- Paid-01: complete real Relay character creation/reference/edit identity QA for Leon, Claire and Victor.
- Paid-02: real H3 opening, Jev 3/3 READY and FREE CANONICAL while all three options are visible; complete official mechanics/StateManager evidence.
- Paid-03: real video Ending, Arc CLOSED and Continue World.
- Current FULL E2E is **PARTIAL**, blocked by missing `IMAGE_PROVIDER_API_KEY`. Four measured 4K Leon images exist; Claire/Victor currently have no formal images. The latest continuation made 0 new paid media submits. Two supplied Fal keys are configured and enabled but were not probed; earlier TOP_UP is not proof that these current keys are blocked. Exact historic image HTTP count remains unknown. See `BIOHAZARD_FULL_E2E_ACCEPTANCE.md`.
- AT-44 independent human feedback and historical AT-01–76 cases not rerun retain their prior status.

## Cost boundary and provider routing

The isolated character scope regression on 9001 used explicit local upload fixtures, mock providers and paid guard OFF: **paid media requests 0**. This does not erase the broader live E2E's four earlier Relay candidates or Fal attempt. The production service is on 9000 and the user now requests that paid generation remain enabled for human testing after integration.

IMAGE_GENERATION / IMAGE_EDIT → configured image provider → current deployment prefers OpenAI-compatible Relay. This is a **USER-approved cost optimization**, not an unauthorized Provider deviation. FalImageProvider is retained in code; this FULL E2E uses Fal only for H3.

## Remaining non-Fal P0

No known P0 remains in the verified scope. The discovered backend publication transaction gap is fixed: ScenarioVersion and all CharacterSnapshots use one transaction and a frozen reviewed-draft source. Seven failure-injection/source-drift/compatibility tests pass, including complete rollback on first/second snapshot failure. The final 195-test integration run, Theater/default-entry regression and build/deployment checks all pass. The real-provider journey remains blocked and PARTIAL; do not infer FULL E2E PASS from AT-80.

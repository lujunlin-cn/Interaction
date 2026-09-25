# Character Library ↔ Creator Granularity Closure

Date: 2026-09-25.
Start SHA for the current FULL E2E work: `1eabeb6afc89e8bdcb402f5b2b452499e7089b9e`.
Final SHA: 本报告所在最终提交；交付回复提供完整 SHA，使用 `git rev-parse HEAD` 核对。

**AT-80: PASS for character management scope.** The old PASS based mainly on seven matching tabs was insufficient and is superseded. This pass is based on persisted A–F UI operations against an isolated backend, including explicit empty overrides, refresh, version pinning, and Promote.

## Scope and paid-request accounting

The character scope regression used a separate temporary SQLite database on port 9001, `FAL_PAID_GENERATION_ENABLED=false`, `PROVIDER_MODE=mock`, and `PROFILE_LIFECYCLE_ENABLED=false`. All media were locally created, clearly labeled upload fixtures. Browser external network access and media-generation submits were blocked.

**Paid media generation requests in this isolated scope regression: 0.** This is not an assertion that the broader FULL E2E has incurred no paid requests: that work already has four historical Relay candidate images and a Fal attempt; its final usage accounting belongs in `BIOHAZARD_FULL_E2E_ACCEPTANCE.md`. The production service on port 9000 was not changed by this regression.

## Results

| Area | Status | Evidence |
| --- | --- | --- |
| Character naming | PASS | Standard uses 角色库 / 角色 / 从角色库添加角色 / 来自角色库 vN / 本故事覆盖 N 项. |
| Shared Studio architecture | PASS | Both entries use `CharacterStudio`, shared tabs and `CharacterProfile`; scope chooses GlobalCharacter versus ScenarioCharacter writes. |
| Standard Reference Pack | PASS | Uploaded and bound front / three_quarter / side / full_front / full_side; back/other remain extra references; generated CharacterAssets and uploaded Assets share the picker. |
| Outfit | PASS | Default and Yellow Raincoat created through UI; editable name/description/default and front/side/back/full_body/additional slots; Creator selects inherited outfits or saves a local outfit/ref without altering the library. |
| Pose | PASS | Three library uploads; Creator selects two; explicit zero selected remains OVERRIDE; uploaded story-only pose persists. |
| Motion | PASS | Two library uploads; Creator selects one and retains it after refresh. |
| Canonical Voice | PASS | Uploaded Voice A is canonical with audition control; remains unchanged after story selection. |
| Alternate Voice | PASS | Uploaded Voice B is selectable and auditionable; story stores voice_id and OVERRIDE. |
| Scenario Overlay | PASS | Read-only state comparisons prove library data is unchanged by outfit, pose, motion, voice, and story-upload edits. |
| Version Pin | PASS | Library v24→v25 leaves story at v24; Continue v24 preserves it; explicit Update v25 refreshes inherited personality while keeping overrides. |
| Promote Global | PASS | Explicit Promote creates library v26 from local outfit/pose/voice overrides; story stays v25 and prior immutable CharacterVersion rows are unchanged. |
| AT-80 | PASS | Actual 1920×1080 Standard UI A–F operations and strict persisted-state assertions, not label-only checks. |

## Verification

- Backend full integration suite: **197 passed / 0 failed / 6 warnings**, with mock providers, Fal Guard OFF and lifecycle disabled. This supersedes the historical 64-pass count and does not prove real-provider media quality.
- Frontend: `npm run build` → **PASS** after shared Studio changes and checkbox layout repair (42 modules).
- Final deployment: `npm ci` / build and backend compileall/pip check **PASS**; `interaction.service` restarted active on 9000. Served JS/CSS bytes/SHA-256 match final dist; `docs/acceptance/biohazard_full_e2e/deployment_final.json`.
- Browser: **PASS**, 1920×1080, no page errors and zero generation/edit submission attempts.
- Evidence: `docs/acceptance/character_scope_regression/scope_regression.json`, replayable `regression.cjs`, screenshots, and README.
- Latest regression character: `chr_00136_31e26b`; scenario: `scn_00180_9ee3f0`. These exist only in the isolated regression database, not the live E2E story.

## Remaining

No known non-Fal P0 remains in the tested character management scope. Real multi-character image/video quality, Production Resolver integration and the complete Paid-01 / Paid-02 / Paid-03 narrative path are **not** proved by upload fixtures; the authorized FULL E2E is tracked separately. AT-44 remains independent human feedback.

The live story was subsequently reviewed and published through Standard UI as **v0.2.0**, `ver_00001_b26e3c`, with Leon v8 / Claire v7 / Victor v7 pins; GET-only checks matched all snapshots and complete local overrides. The full E2E remains PARTIAL because the Image Relay credential is missing and the three-character media/runtime path is unfinished. The later-discovered backend atomic-publication gap was fixed and seven transaction/source-drift/compatibility regressions passed; see `BIOHAZARD_FULL_E2E_ACCEPTANCE.md`.

Image routing is a **USER-approved cost optimization**: IMAGE_GENERATION / IMAGE_EDIT → configured image provider → current deployment prefers OpenAI-compatible Image Relay (`gpt-image-2.5-sunburst`); FalImageProvider remains available in code. This is not an unauthorized PRD deviation, and this FULL E2E must not call Fal Nano Banana.

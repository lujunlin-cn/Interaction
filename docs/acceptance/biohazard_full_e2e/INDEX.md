# Biohazard full E2E evidence index

Checkpoint: **2026-09-25**. Service: **port 9000**. Scenario:
`scn_00003_364d7e`, **生化危机：黑雨隔离区**.

**Overall: PARTIAL.** Creator parameters have been reviewed and the story has
been published through Standard UI. Character media and the full Player path
remain incomplete at this checkpoint. Evidence below distinguishes actual UI
actions, read-only verification, historical checkpoints and isolated mock tests.

Detailed metric/file boundaries, missing required Player evidence and final deployment checks are in [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md); the full A–G report is [BIOHAZARD_FULL_E2E_ACCEPTANCE.md](../../../BIOHAZARD_FULL_E2E_ACCEPTANCE.md).

## 1. Natural-language creation and confirmation

| Stage | Evidence | What it proves |
| --- | --- | --- |
| Initial idea | [Initial intent](creator_initial_intent.png), [first draft readback](creator_scenario_after_idea.json) | Natural-language starting point and its generated draft; this early draft contained mistakes corrected later. |
| AI understanding | [Understanding](creator_ai_understanding.png) | The actual AI understanding screen. |
| Suggested answer | [Suggestion selected](creator_suggestion_selected.png) | A contextual suggestion was selected through UI. |
| Clarification | [Question](creator_clarification_question.png), [clarification](creator_clarification.png), [confirmation](creator_clarification_confirmed.png), [saved result](creator_after_clarification_confirmed.json) | User clarification and confirmation, before the later detailed parameter review. |
| Final World / Drama / Mechanics | [Review summary](creator_review/README.md), [World](creator_review/final_world.png), [Drama](creator_review/final_drama.png), [Mechanics](creator_review/final_mechanics.png) | Standard UI parameter review with seven locations, corrected truth/secret/pressure boundaries, four ending tradeoffs and four typed mechanics. |
| Persisted parameters | [Final readback](creator_review/final_parameters_readback.json), [strict assertions](creator_review/final_parameters_assertions.json), [operator page review](creator_review/root_parameter_review.json) | Saved authoring state, including a 15-second nonfatal QTE restricted to the sample room/control center. This does not prove a Runtime QTE has fired. |

## 2. Character text, Scope and visual evidence

| Character / capability | Evidence | Current boundary |
| --- | --- | --- |
| Leon text review | [AI proposals](creator_review/leon_review_proposal.json), [confirmed values](creator_review/leon_review_confirmed.json), [UI](creator_review/leon_review_confirmed.png) | Existing library character reviewed through Standard UI; stable text confirmed to v8. Existing canonical image retained. |
| Claire AI creation | [UI creation](creator_review/claire_ui_character_creation.json), [proposals](creator_review/claire_review_proposal.json), [confirmed values](creator_review/claire_review_confirmed.json), [UI](creator_review/claire_review_confirmed.png) | New character created and text confirmed through Standard UI; pinned v7. Visual assets are still missing in this publication. |
| Victor AI creation | [UI creation](creator_review/victor_ui_character_creation.json), [proposals](creator_review/victor_review_proposal.json), [confirmed values](creator_review/victor_review_confirmed.json), [UI](creator_review/victor_review_confirmed.png) | New character created and text confirmed through Standard UI; pinned v7. Visual assets are still missing in this publication. |
| Scenario binding and overlays | [Rebind timeline](creator_review/ui_rebind_timeline.json), [saved bindings](creator_review/after_ui_character_rebind.json), [characters UI](creator_review/final_characters.png) | Formal picker added the UI-created library characters; story-specific rain, dust, injury and RPD outfit remain in Scenario scope. |
| Leon existing 4K candidates | [Candidates UI](leon_candidates.png), [canonical UI](leon_canonical.png), [asset readback](leon_assets_current.json), [measured dimensions](leon_image_dimensions.json) | Four actual Relay image artifacts from two internal generation jobs. All measured 4096 × 4096; prior declared 16:9 is not evidence of actual 16:9. Pre-fix adapter did not capture provider request IDs. |
| Leon Step 5 candidate QA | [Structured review](visual_qa/leon_candidate_review_step5.json), [schema validation](visual_qa/leon_candidate_review_validation.json), [request summary](visual_qa/leon_candidate_review_step5_request_summary.json) | One recorded review of all four images accepts the current canonical; no major failure and no new image generation in that review. Requested reasoning effort is high; reported reasoning tokens are recorded as received. |
| Shared Library / Creator management | [Independent A–F Scope regression](../character_scope_regression/README.md) | Persisted Outfit/Pose/Motion/Voice/version/promotion behavior in isolated no-cost regression. It is not real image/video generation or Player E2E evidence. |

The older API-created Claire/Victor records are historical. The UI publication
uses `chr_00018_204d12` and `chr_00032_149758`; it does not substitute the older
records for real UI creation evidence.

## 3. Explicit review and real UI publication — PASS

| Evidence | Result |
| --- | --- |
| [Publish gate](publish_gate.png) | Final authoring checklist shown before review. |
| [Review checkbox](publish_reviewed.png) | Operator explicitly checked the review checkbox. |
| [Published version history](published_version.png) | New v0.2.0 visible after publication. |
| [Captured publication request / response](scenario_published_ui.json) | One Standard UI Publish new version request with `reviewed=true, play=false`; version `ver_00001_b26e3c`; no Session created by this action. |
| [Live immutable snapshots](character_snapshots_ui.json) | Leon v8 → `snap_00004_a7cb7f`; Claire v7 → `snap_00005_54ba2c`; Victor v7 → `snap_00006_1589b7`. |
| [Read-only verification](published_snapshot_verification.json) | Snapshot set, pinned versions and complete story overlays exactly match the publication capture; Leon RPD outfit retained. |
| [Publish safety regression](../publish_safety/README.md) | Nine isolated browser cases, including visible natural-language missing-image advisory with text publication still permitted. |

`scenario_published.json` is the earlier **v0.1.0 API checkpoint**, including an
earlier Session. It is retained for provenance and is not accepted as Standard UI
publication or successful Player E2E evidence.

The published story is valid for text authoring. Missing character images remain
an explicit warning. Publication is not an assertion that this version is ready
for multi-character video production.

## 4. Provider and usage evidence

- [Provider configuration](provider_matrix.json), [provider audit](provider_audit.json), [environment health](environment_live_health.json).
- [Generation settings snapshot](generation_settings_live.json).
- [Usage ledger snapshot](usage_ledger_current_snapshot.json), [earlier ledger](usage_ledger_live.json).
- [Measured image provenance](leon_image_dimensions.json): provider **image_relay**, recorded/configured model **gpt-image-2.5-sunburst** for the four existing assets. The pre-fix adapter did not retain independent upstream-returned model/request IDs, so those historical fields cannot be asserted as independently confirmed actual-model evidence.

OpenAI-compatible Image Relay is **USER-approved cost optimization**. Images use
the configured Relay; Fal is reserved for H3 video in this E2E. Configured video
route and readiness flags alone do not prove a successful H3 generation. Runtime
request IDs and actual returned video model must be recorded when execution
occurs.

Parameter review, the v0.2.0 UI publication, subsequent GET-only snapshot
verification and the isolated publish regression made **0 new media generation
or edit submissions**. This does not erase the earlier Relay jobs or any earlier
Fal attempts from the full E2E usage ledger.

Final [environment](environment.json), [provider matrix](provider_matrix_final.json) and [durable ledger](usage_ledger_final.json) confirm paid enabled/persisted, two configured Fal accounts not probed, and the missing Relay credential. An empty final ledger does not erase pre-ledger historical attempts.

## 5. Final regression and deployment — PASS

- [Backend full regression](backend_regression_final.txt): **195 passed / 0 failed / 6 warnings**, 96.58s; compileall/pip check also PASS.
- [Final frontend build](frontend_build_final.txt): `npm ci` / build PASS, 42 modules, `index-DBDSet8X.js` / `index-C4Yk5vqH.css`.
- [Deployment](deployment_final.json): `interaction.service` active on **9000**, served JS/CSS bytes/SHA-256 match final dist. All user Scenario/Version/Session/Character objects preserved; existing startup seed refreshed only official `rainy_apartment` / `ver_rainy_1_0_0` rows.
- [Read-only Theater](theater_readonly.json): 1920×1080 and 2560×1440, default in-app Theater, fullscreen=false, Sidebar/Header hidden, controls inside Stage, Agency bottom, HUD/input/Session preserved. This uses the historical failed Session and proves layout, not a new successful video.
- [Four isolated Player regressions](../player_stage_controls/browser.json): error/Ready geometry, default entry/navigation, input/session/progress preservation; 0 external paid media requests.
- Seven publication transaction/source-drift/compatibility cases passed in `test_publish_atomicity.py`; nine isolated Publish UI safety cases pass. No known non-Fal P0 remains in these verified scopes.

## 6. Remaining real-provider evidence

The following are **not complete at this checkpoint** and must not be marked
PASS based on mock regression or existing configuration:

- Complete Leon Standard Reference Pack and real 4K outfit edit.
- Claire and Victor real 4K candidates, canonical/reference assets and Step 5 QA.
- Three-character identity separation and multi-character Reference Resolver.
- Fresh Standard Player Session, real H3 Opening and Step 5 video QA.
- Real Jev Top-3 with three Ready H3 branches; independent FREE action while all three are visible; FREE canonical state and speculative isolation.
- A subsequent real recommendation selection.
- Runtime Inventory, Clue, Claire Relationship, Wish and Timed interaction, each with Skill/Proposal/StateManager and before/after evidence.
- Truth/secret boundary during play, real video Ending, closed Arc and explicit Continue World with inherited canonical state.

Full E2E status remains **PARTIAL** until those user paths and evidence are
complete. Later character media versions must be explicitly adopted by the
Scenario and reviewed/published again before a new Session uses them.

# Biohazard E2E Evidence Index

Date: 2026-09-25. Overall result: **PARTIAL**. Main report: [BIOHAZARD_FULL_E2E_ACCEPTANCE.md](../../../BIOHAZARD_FULL_E2E_ACCEPTANCE.md).

## Evidence rules

- Files here record this story's observed actions or their explicit diagnostic checkpoints. Missing steps have no invented screenshot/trace.
- `scenario_published_ui.json` is the latest real Standard UI publication, version **0.2.0**. `scenario_published.json` is an earlier **0.1.0 API checkpoint** and must not prove UI publishing.
- `creator_review/final_parameters_assertions.json` is the pre-publication review. The subsequent UI publish is separate evidence.
- `provider_audit.json`, `usage_ledger_current_snapshot.json`, `usage_ledger_live.json` and `provider_matrix.json` are timestamped/historical checkpoints. In-memory counters and old route-health labels do not prove current balance/readiness or erase prior attempts.
- The parameter-review continuation made no media submissions; the later Relay continuation is recorded separately in `RELAY_VISUAL_CONTINUATION.md` and `usage_ledger_after_relay.json`.

## Creator: natural idea → understanding → confirmation

| Step | Evidence |
| --- | --- |
| Initial idea | [creator_initial_intent.png](creator_initial_intent.png), [creator_scenario_after_idea.json](creator_scenario_after_idea.json) |
| AI understanding | [creator_ai_understanding.png](creator_ai_understanding.png) |
| Suggested choice and free clarification | [creator_suggestion_selected.png](creator_suggestion_selected.png), [creator_clarification_question.png](creator_clarification_question.png), [creator_clarification.png](creator_clarification.png), [creator_after_clarification_confirmed.json](creator_after_clarification_confirmed.json) |
| Visible World/Overview corrections | [static_review_timeline.json](creator_review/static_review_timeline.json), [final_world.png](creator_review/final_world.png) |
| Real Drama AI proposal and confirmation | [drama_proposal.json](creator_review/drama_proposal.json), [drama_timeline.json](creator_review/drama_timeline.json), [final_drama.png](creator_review/final_drama.png) |
| Pressure failure and repair | [pressure_instruction_result.json](creator_review/pressure_instruction_result.json), [pressure_repaired_readback.json](creator_review/pressure_repaired_readback.json), [pressure_repaired_ui.png](creator_review/pressure_repaired_ui.png) |
| Real mechanics proposal and confirmation | [mechanics_proposal.json](creator_review/mechanics_proposal.json), [mechanics_timeline.json](creator_review/mechanics_timeline.json), [final_mechanics.png](creator_review/final_mechanics.png) |
| Final parameter inspection | [final_parameters_readback.json](creator_review/final_parameters_readback.json), [final_parameters_assertions.json](creator_review/final_parameters_assertions.json), [root_parameter_review.json](creator_review/root_parameter_review.json) |

Full review chronology and its checkpoint boundaries: [creator_review/README.md](creator_review/README.md).

## Characters and publication

| Step | Evidence / status |
| --- | --- |
| Leon text AI creation/review | [leon_create_form.png](leon_create_form.png), [leon_review_proposal.json](creator_review/leon_review_proposal.json), [leon_review_confirmed.json](creator_review/leon_review_confirmed.json) |
| Leon existing candidates/canonical | [leon_candidates.png](leon_candidates.png), [leon_canonical.png](leon_canonical.png), [leon_assets_current.json](leon_assets_current.json) |
| Actual 4K dimensions | [leon_image_dimensions.json](leon_image_dimensions.json): four 4096×4096 PNG assets with SHA-256; one canonical |
| Leon reference pack | [leon_reference_pack_before.png](leon_reference_pack_before.png) is an incomplete pre-generation view, **not pack PASS** |
| Leon Outfit | [leon_pinned_outfit_review.png](creator_review/leon_pinned_outfit_review.png) proves selection only, **not real IMAGE_EDIT** |
| Claire Standard AI creation | [claire_ui_character_creation.json](creator_review/claire_ui_character_creation.json), [claire_review_confirmed.json](creator_review/claire_review_confirmed.json), [Relay assets](relay_character_assets_final.json) |
| Victor Standard AI creation | [victor_ui_character_creation.json](creator_review/victor_ui_character_creation.json), [victor_review_confirmed.json](creator_review/victor_review_confirmed.json), [Relay assets](relay_character_assets_final.json) |
| Pins and Scenario overlays | [ui_rebind_timeline.json](creator_review/ui_rebind_timeline.json), [final_characters.png](creator_review/final_characters.png), [final_parameters_readback.json](creator_review/final_parameters_readback.json) |
| Final gate / review checkbox | [publish_gate.png](publish_gate.png), [publish_reviewed.png](publish_reviewed.png) |
| Real UI publication | [scenario_published_ui.json](scenario_published_ui.json), [published_version.png](published_version.png): v0.2.0, three snapshots, no Play/Session request |
| Exact published snapshot verification | [character_snapshots_ui.json](character_snapshots_ui.json), [published_snapshot_verification.json](published_snapshot_verification.json): GET-only comparison proves all three pins and complete local overrides match the reviewed publication |
| Earlier API checkpoint | [scenario_published.json](scenario_published.json), [scenario_characters.json](scenario_characters.json): historical v0.1.0, **not current UI proof** |

Claire/Victor standard reference packs and Outfit edit QA do not exist yet. Candidate assets and failed Relay edit attempts are recorded in `RELAY_VISUAL_CONTINUATION.md`; these capabilities remain PARTIAL.

Repository copies of the returned 4K candidate assets are indexed in [relay_assets/README.md](relay_assets/README.md); they are evidence copies, not additional generation requests.

## Visual QA

| Review | Evidence |
| --- | --- |
| Historical Leon candidate call | [leon_candidate_step5.json](visual_qa/leon_candidate_step5.json), [leon_candidate_step5_raw.json](visual_qa/leon_candidate_step5_raw.json) |
| Fresh all-four Leon candidate adjudication | [leon_candidate_review_step5.json](visual_qa/leon_candidate_review_step5.json) |
| Request parameters and source assets | [leon_candidate_review_step5_request_summary.json](visual_qa/leon_candidate_review_step5_request_summary.json), [leon_candidate_review_context.json](visual_qa/leon_candidate_review_context.json) |
| Contract validation / counts | [leon_candidate_review_validation.json](visual_qa/leon_candidate_review_validation.json): 4 reviewed, 0 major failures, existing canonical accepted, 1 new QA call, 0 media calls |

Total Step 5 visual QA calls: **2**. No real video exists, so no opening/FREE/ending frame folders or video QA results are claimed. Missing multi-character QA cannot be reported as “no identity swap”.

## Provider and usage checkpoints

| File | Meaning |
| --- | --- |
| [environment_live_health.json](environment_live_health.json) | Live provider/profile health checkpoint on the formal service |
| [generation_settings_live.json](generation_settings_live.json) | 4K / 480P / 16:9, test override disabled, paid switch enabled at capture |
| [provider_matrix.json](provider_matrix.json) | Earlier configured routes/events; not a current key-balance probe or successful full runtime trace |
| [provider_audit.json](provider_audit.json) | Pre-fix audit of missing historical image ledger/model/request evidence; implementation defects described there were later repaired |
| [usage_ledger_current_snapshot.json](usage_ledger_current_snapshot.json) | Historical one H3 submit entry (5s/480P) and one local BILLING_LOCKED rejection; no accepted job |
| [usage_ledger_live.json](usage_ledger_live.json) | Empty old process-local snapshot; must not replace historical accounting |
| [environment.json](environment.json), [provider_matrix_final.json](provider_matrix_final.json) | Final read-only live configuration: two configured Fal accounts unprobed, 4K/480P/16:9, default 5s/opening 8s/ending 8s/max 10s, paid enabled and persisted; credential values are excluded |
| [usage_ledger_after_relay.json](usage_ledger_after_relay.json) | Durable Relay continuation ledger: successful candidate generations plus failed edit attempts; no secrets |
| [deployment_final.json](deployment_final.json) | Final 9000 active restart; served JS/CSS bytes/SHA-256 match latest dist; all user objects unchanged, existing seed refreshed only official rainy-apartment rows |
| [backend_regression_final.txt](backend_regression_final.txt), [frontend_build_final.txt](frontend_build_final.txt) | 197 passed / 0 failed / 6 warnings; final 42-module frontend build PASS |

Final deployment/environment/ledger verification is complete in the files above. Credentials, `.env`, signed secrets and key values are excluded.

## Theater error-state regression

[theater_readonly_before_controls_fix.json](theater_readonly_before_controls_fix.json) and the `*_before_controls_fix.png` screenshots are fresh port-9000 read-only inspections of the historical failed Session at 1920×1080 and 2560×1440. They exposed video controls overlapping Agency. The localized Player/CSS repair passes four isolated regression cases at those sizes with both error+Ready and normal Ready states; see [controls before](../player_stage_controls/browser_before_fix.json), [default entry before](../player_stage_controls/browser_default_before_fix.json) and [final after](../player_stage_controls/browser.json). The final isolated test verifies default in-app Theater, navigation/reentry, fullscreen=false, HUD, Agency and input/session/progress preservation with zero mutations/external media requests.

Latest [theater_readonly.json](theater_readonly.json), [1920 screenshot](theater_readonly_1920.png) and [2560 screenshot](theater_readonly_2560.png) verify the deployed controls are within Stage, Sidebar/Header hidden, ordinary browser window, error overlay inside Stage, and Session/input preserved. These are read-only historical-error layout checks; no Retry/Play/media request was made, and they are not real H3 play evidence.

## Required Player evidence still missing

The following files were requested but **have not been produced as successful real product-path evidence**:

- Opening/theater/playback lead, real Top-3, 3/3 READY plus free input, FREE result and selected recommendation screenshots.
- `character_reference_resolution.json`, `opening_provenance.json`, `jev_top3.json`, `ready_branch_jobs.json`.
- `free_action_trace.json`, `free_action_state_diff.json`, `recommendation_selection_trace.json`.
- Inventory, clue, relationship, Wish and timed HUD screenshots and their Skill/Proposal/StateManager before-after traces.
- `ending_provenance.json`, ending screenshot, Continue World screenshot and `continue_world_state.json`.
- Leon reference/outfit QA, Claire/Victor reference QA, separation QA and all video frame/QA results. Candidate generation evidence exists, but no Step 5 review was performed for the new Relay outputs.

Do not add placeholder success files to fill this list. Resume through the real UI after the Relay edit endpoint is healthy and generated assets are explicitly adopted and republished.

## Separate regression evidence (not real-provider success)

- [Character scope A–F](../character_scope_regression/README.md): isolated mock backend, uploaded fixtures, 1920×1080, zero paid requests; supports AT-80 management PASS.
- [Publish safety](../publish_safety/README.md): failed-save/stale-review/double-submit regression.
- [Pressure contract](../pressure_contract/README.md): JSON/driver normalization and Standard UI editing.
- [Preflight safety](../preflight_safety/README.md): actual effective settings/circuit checks and preview-only accounting.
- Publication atomicity: `backend/tests/test_publish_atomicity.py`, seven transaction/source-drift/compatibility cases; first/second snapshot faults roll back ScenarioVersion and all snapshots together.
- Backend full regression: **197 passed / 0 failed / 6 warnings**, 97.05s; compileall/pip check PASS. Final frontend `npm ci` / build and 9000 deployment verification after Publish-warning/Player changes **PASS**.

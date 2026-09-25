# Biohazard E2E evidence index

Overall: PARTIAL. Current Scenario scn_00003_364d7e is published as 0.3.0 / ver_00001_1fa925. Current Player Session: sess_00006_6051ee. Earlier 0.1.0 and 0.2.0 records are immutable historical checkpoints, not the current publication.

## Creation and character system

| Evidence | Scope |
| --- | --- |
| [Initial idea](creator_initial_intent.png), [understanding](creator_ai_understanding.png), [clarification](creator_clarification.png) | Real Standard Creator path; not rerun during continuation |
| [Parameter review](creator_review/README.md) | World, Drama and mechanics human-style review |
| [Latest publish](continuation/republish/published.json), [verification](continuation/republish/verification.json), [snapshots](continuation/republish/snapshots.json) | 0.3.0, Leon v13, Claire v12, Victor v12; reviewed overlays and frozen refs |
| [Duplicate archival](continuation/duplicate_archive_result.json), [browser regression](continuation/duplicate_browser_regression.json) | Old Claire/Victor archived; historical snapshots resolve; active identities retained |
| [Leon references](continuation/leon_reference_approved_ui.json), [Outfit](continuation/leon_outfit_approved_ui.json) | Relay 4K edits, approved through UI |
| [Claire references](continuation/claire_reference_approved_ui.json), [Victor references](continuation/victor_reference_approved_ui.json) | Complete reference packs, old 401 superseded by actual success |
| [QA index](visual_qa/call_index.json) | 16 unique completion IDs; report/validation mirrors deduplicated |
| [Opening retry](continuation/opening_quality_retry.json) | One major-semantic quality retry; not zero retries |

Images use USER-approved OpenAI-compatible Image Relay, preferred gpt-image-2.5-sunburst. Fal is reserved for minimax/h3-max/reference-to-video. Historical IMAGE_EDIT 502 failures were followed by successful multipart edits; credentials are not a current blocker.

## Player and mechanics

All files below are under [continuation/play_final](continuation/play_final/) unless linked elsewhere. Full state, view, trace, ledger and screenshot variants share each prefix.

| Prefix / evidence | Verified boundary |
| --- | --- |
| opening_playback_verified; [opening provenance](continuation/opening_provenance.json) | Real Opening H3 and Theater Mode |
| three_ready_plus_free_input | Real Jev Top-3, three READY videos and visible free input |
| free_action_before, free_canonical | Independent FREE branch, canonical commit and speculative isolation |
| recommendation_selected | Real recommendation selection and commit |
| inventory_action_before, inventory_hud_fixed | Inventory proposal and canonical state |
| wish_active | Real ACTIVE wish, soft preference |
| [Clue trace](clue_trace.json) | Real text-mode terminal clue: Skill → Proposal → StateManager, before/after |
| [Relationship trace](relationship_trace.json) | Real text-mode Claire trust: 50 + 10 = 60 |
| [Text continuation](continuation/text_tail/) | Standard UI actions; zero new media; separate from real-video acceptance |
| [Visual QA](visual_qa/) | Existing portraits, reference packs, Opening, READY branches, FREE, inventory and multi-character reviews |

QTE/countdown, real video Ending, formal Arc closure and Continue World are not certified by these earlier checkpoints. Refer to the latest acceptance report for the text-tail result and remaining blockers. No text result or mock artifact is counted as an H3 success.

## Cost, timing, deployment and regression

- [Timing report](../../../BIOHAZARD_FULL_E2E_TIMING.md), [phase data](phase_timings.json): measured spans, not parallel durations summed as user wait.
- [New primary-key validation](continuation/key_handoff/probe.json): one authorized 5s/480P/16:9 job, no retry or fallback; secondary unchanged.
- Cumulative recorded H3: 29 successes, 166 requested seconds, longest 9s. Includes 28 story jobs and the separately labeled key validation.
- Relay continuation: 5 generation HTTP attempts and 21 edit attempts; no Fal image calls.
- [Backend regression](continuation/backend_regression.txt): latest full suite log.
- [Player visibility](../player_decision_visibility/regression.json): five offline 1920×1080 cases, no media calls.
- [Nemotron](continuation/nemotron_health.json): actual model / serving evidence.
- [Final handoff](continuation/key_handoff/health.json): app, model, settings, published version and served-build verification.

Paid generation remains enabled for human testing. Recommendation video pre-generation remains disabled. No background loop submits videos. Secrets stay only in ignored configuration.

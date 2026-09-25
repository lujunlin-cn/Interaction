# Biohazard FULL E2E Acceptance

Date: 2026-09-25. Story: **《生化危机：黑雨隔离区》**.

**Overall: PARTIAL.** The real Standard Creator path is published at 0.3.0. Verified play includes real Opening H3, Jev Top-3/3 READY, FREE canonical, recommendation selection, inventory, wish and multi-character H3; subsequent text play adds canonical Clue and Claire relationship. Arc ending, timed chase and Continue World remain incomplete. No mock or old artifact is counted as a real-provider PASS.

| Audit field | Value |
| --- | --- |
| Requirements SoT | `Agent_Skills_Interactive_Drama_PRD_AI_v0.6.md`, with the user's later explicit provider/quality instructions |
| Original creation Start SHA | `1eabeb6afc89e8bdcb402f5b2b452499e7089b9e` |
| Continuation Start SHA | `9e4e6fdf15753ccbf9fdc978552b6cc19bb94310` |
| Inspected integration base | 9e4e6fdf15753ccbf9fdc978552b6cc19bb94310 |
| Final SHA | This report is stored in the delivery commit; use `git log -1 --format=%H -- BIOHAZARD_FULL_E2E_ACCEPTANCE.md` to resolve its exact SHA without a self-referential hash. |
| Service | Port **9000** |
| Latest real UI publication | Scenario `scn_00003_364d7e`, version **0.3.0**, `ver_00001_1fa925` |
| Latest review/publish | 1920×1080 Standard UI; final checkbox explicitly checked; one `publish` POST with `reviewed=true, play=false` |
| Latest published character pins | Leon v13; Claire v12; Victor v12 |
| Relay continuation media requests | **26 image HTTP attempts: 5 generation (3 succeeded, 2 failed) and 21 edit (13 succeeded, 8 historical transient failures); no Fal image requests** |
| H3 continuation media | **29 succeeded (28 story jobs + 1 explicitly authorized key validation)**, Fal `minimax/h3-max/reference-to-video`, 480P, 5–9 seconds, 166 requested seconds total (161 story + 5 key validation) |
| Current blocker | Fal balance is now deliberately protected by disabling speculative recommendation pre-generation. Ending/QTE/Continue World are still unplayed; no new video request is being made. |
| Paid switch on live service | **Enabled**, as the user's latest instruction requires for later human testing. New primary validated with one H3 job; secondary unchanged. Exact account balances are not inferred. |

The image route is a **USER-approved cost optimization**: `IMAGE_GENERATION / IMAGE_EDIT → configured OpenAI-compatible Image Relay`, preferred model `gpt-image-2.5-sunburst`, fallback sequence documented in `IMAGE_RELAY_ACCEPTANCE.md`. Fal is reserved for H3 video in this E2E. The Fal image adapter remains in code and is not used here. The Relay credential is configured only in ignored `backend/.env`; no credential is committed.

The Jev decision result is now exposed as soon as the locked recommendation labels are available. Recommendation media readiness is independent: with `pre_generate_recommendation_media=false`, all three labels remain selectable while their videos are deferred until a player choice. The setting stays false under the latest user instruction, including after replacing and validating the primary Fal key.

## Evidence interpretation

- [Evidence index](docs/acceptance/biohazard_full_e2e/EVIDENCE_INDEX.md) identifies actual screenshots, readbacks, QA reports and missing proof.
- [Latest UI publication](docs/acceptance/biohazard_full_e2e/scenario_published_ui.json) supersedes the earlier API-only publication checkpoint for product-path acceptance.
- [Final parameter readback](docs/acceptance/biohazard_full_e2e/creator_review/final_parameters_readback.json) and [assertions](docs/acceptance/biohazard_full_e2e/creator_review/final_parameters_assertions.json) were captured before the final review checkbox and publication. [Root review](docs/acceptance/biohazard_full_e2e/creator_review/root_parameter_review.json) records the last visible page review.
- The earlier `0.1.0` publication `ver_00017_8f2d1c`, Session `sess_00028_dc6cb4` and opening `opening_00033_23675f` are diagnostic/API checkpoints. Their failed opening is not a successful Player journey. No Session was created by the final `0.2.0` UI publish.
- PASS below applies only to the named, observed step. PARTIAL includes blocked or unexecuted portions. It does not imply that an untested runtime feature has failed.

The continuation evidence under `continuation/play_final/` supersedes earlier rows that described the pre-opening billing checkpoint. Those earlier failures remain historical diagnostics.

## A. Story Creation

**Story Creation: PASS for the reviewed and published authoring path; full production readiness remains PARTIAL.**

| Required step | Result | Evidence and boundary |
| --- | --- | --- |
| Natural-language Initial Intent | PASS | `creator_initial_intent.png`, `creator_scenario_after_idea.json`: new story starts from the supplied natural-language Resident Evil side-story idea. |
| AI Understanding | PASS | Real Step 5 understanding, visible proposals and later explicit confirmations; `creator_ai_understanding.png`, `creator_review/drama_proposal.json`. |
| Contextual Clarification | PASS | A suggested option was selected and free-text additions were confirmed; `creator_suggestion_selected.png`, `creator_clarification*.png`, `creator_after_clarification_confirmed.json`. Final confirmed UI reports no repeated question for already explicit information. |
| World Authoring | PASS | Seven reviewed locations and rules covering infection, doors, movement, death, permissions and knowledge. Visible fields were inspected and corrected; `creator_review/static_review_timeline.json`, `final_world.png`. |
| Drama Authoring | PASS | Real AI understanding and confirmation, followed by visible corrections. Four ending families, evidence-bound truth/secrets, Claire's agency and nonfatal pursuit constraints are persisted. `drama_timeline.json`, `final_drama.png`, `final_parameters_readback.json`. |
| Natural-language Mechanics | PASS for authoring | Standard UI instruction → real Step 5 projection → explicit confirmation of inventory, clue-system, relationship and qte typed configs. `mechanics_timeline.json`, `mechanics_proposal.json`, `final_mechanics.png`. Runtime execution is not proved by this row. |
| Human-style parameter review | PASS | Overview, World, Characters, Drama, Mechanics, version differences and Publish Gate inspected through Standard UI. Incorrect Victor/T-103 details were corrected, seven locations verified, all four mechanics confirmed, pins explicitly updated. |
| Publish Gate | PASS | Standard UI reviewed and published 0.3.0; continuation/republish/published.json, publish_reviewed.png, verification.json. Earlier 0.2.0 evidence remains historical. |

The final draft treats Victor as a research supervisor, not a security supervisor; removes unsupported T-103 human-origin/obsession claims and predetermined Leon death; preserves the tradeoff between rescue, evidence and sample containment. These are Scenario data corrections through user-visible controls, not special runtime rules.

### Historical 0.2.0 character references (immutable)

Current 0.3.0 pins: Leon v13, Claire v12, Victor v12. Current snapshots: snap_00002_dbf942, snap_00003_4371ac, snap_00004_d65603. See continuation/republish/snapshots.json. The following table is historical.

| Character | Library ID | Pinned version | Story scope |
| --- | --- | --- | --- |
| Leon | `chr_00013_113084` | 8 | Player role; selected RPD outfit `outfit_00005_931bd6`; reviewed personality/knowledge/relationship and wet, dirty uniform description |
| Claire | `chr_00018_204d12` | 7 | Newly UI-created library character; independent judgement and cooperation; rain/dust story appearance |
| Victor | `chr_00032_149758` | 7 | Newly UI-created library character; motive/secrets/limited knowledge; blood on coat and injured right arm story appearance |

The publication returned Leon `snap_00004_a7cb7f`, Claire `snap_00005_54ba2c`, Victor `snap_00006_1589b7`. Subsequent GET-only verification compared the snapshot set, each pinned version and each complete local override against the reviewed publication; all matched. See `character_snapshots_ui.json` and `published_snapshot_verification.json`. The later real Opening context contains actual reference selection. Earlier Claire/Victor API-created records remain separate historical records and are not counted as the UI-created characters.

## B. Character System

**Character System: PASS for completed portraits, reference packs, Outfit, snapshots and resolver; Victor video identity remains unverified. AT-80: PASS.**

| Required step | Result | Evidence and boundary |
| --- | --- | --- |
| Leon AI Creation | PASS for text workflow | Standard creation evidence and later real AI understanding/confirmation; `leon_create_form.png`, `creator_review/leon_review_proposal.json`, `leon_review_confirmed.json`. |
| Leon 2×4K Candidate | PASS for existing outputs | Four candidate outputs from two historical service batches; all measured **4096×4096 PNG**. `leon_assets_current.json`, `leon_image_dimensions.json`. Exact external request count/IDs were not retained by the old adapter. |
| Leon Canonical | PASS | One of the four images, `ca_00016_628682`, is canonical; the other three are candidates. Step 5 retained the current canonical without regeneration. |
| Leon Standard Reference Pack | PASS | Five 4K views approved through Standard UI after Step 5 identity QA; continuation/leon_reference_approved_ui.json. |
| Leon Outfit Edit | PASS | Separate 4K multipart IMAGE_EDIT asset ca_00006_9ac0e8; Step 5 accepted; Standard UI approved and bound to RPD outfit. Original canonical unchanged. |
| Claire AI Creation | PASS for text workflow | New character created and AI suggestions reviewed/confirmed through Standard UI; `claire_ui_character_creation.json`, `claire_review_confirmed.json`. |
| Claire 4K References | PASS | Existing canonical retained; four new 4K edits accepted by Step 5 and approved through Standard UI. Five-view pack frozen in v12. Historical 401 superseded. |
| Victor AI Creation | PASS for text workflow | New character created and AI suggestions reviewed/confirmed through Standard UI; `victor_ui_character_creation.json`, `victor_review_confirmed.json`. |
| Victor 4K References | PASS | Existing canonical retained; four new 4K edits accepted by Step 5 and approved through Standard UI. Five-view pack frozen in v12. Historical 401 superseded. |
| Three-character Identity Separation | PASS for existing canonical portraits | Step 5 reviewed all three pairs: separable, no identity swap/face mix. `visual_qa/three_character_separation_step5.json`. This does not certify a multi-character video. |
| Scenario Snapshots | PASS | GET-only checks prove the exact three returned snapshots, pinned versions, complete local overlays and the production reference selections used by the live opening. |
| Scenario Overlays | PASS | Visible story edits/rebinding and readback preserve library definitions. `creator_review/ui_rebind_timeline.json`, `scenario_published_ui.json`. |
| Multi-character Resolver | PASS | `character_reference_resolution.json` and the reviewed Leon + Claire H3 artifacts show cast/reference allocation used by the real production path. |

The separate [AT-80 closure](CHARACTER_GRANULARITY_CLOSURE.md) proves shared Studio tabs, identity/reference management, outfit reference slots, selectable pose/motion, canonical/alternate voice, uploads/bind/unbind, versions, scenario isolation and explicit Promote. Its media are labeled upload fixtures in a separate mock database. That scope PASS is not real visual-generation or gameplay proof.

## C. Story Play

**Story Play: PARTIAL — the live session completed opening, recommendation and multi-character scenes; text continuation verified clue and relationship, but formal ending/QTE/Continue World remain incomplete.**

| Required step | Result | Evidence and boundary |
| --- | --- | --- |
| Real Opening H3 | PASS | `opening_playback_verified_view/state.json`, `opening.mp4`, and `opening_provenance.json`; real 8s Fal H3 artifact with Leon + Claire. |
| Theater Mode | PASS for layout and opening playback | Port-9000 1920×1080 browser evidence plus `opening_playback_verified.png`; latest CSS hides playback controls/HUD/agency until a decision is open. |
| Decision Lead | PASS | The server transitions to `WAITING_DECISION` and exposes the decision layer independently of branch media readiness. |
| Real Jev Top-3 | PASS | `three_ready_plus_free_input_state.json` records a real locked epoch with `target_k=3`, `effective_k=3`; trace includes real decision routing. |
| 3 / 3 Ready | PASS | `br_00057_333e2c`, `br_00059_35f225`, `br_00061_8b5055` all reached `READY`; three branch videos were reviewed. |
| Free Input Visible With Three Options | PASS | `three_ready_plus_free_input.png` shows three recommendation cards and the agency textbox simultaneously. |
| FREE Branch | PASS | The submitted free action created `br_00012_e5b104` with `source=free`, independent of the three speculative branches. |
| FREE Canonical | PASS | `free_canonical_state.json` records the FREE branch as `CANONICAL`; earlier recommendations are invalidated/speculative. |
| Recommended Branch Selection | PASS | `recommendation_selected_view/state.json` records a later recommendation selected and canonicalized after media confirmation. |
| Speculative Isolation | PASS for recorded branch/world boundary | The before/after state snapshots show only the FREE branch committed while unselected branches are invalidated; no unselected branch became canonical. |
| Truth / Secret Boundary | PARTIAL | Authoring data now respects evidence boundaries; live disclosure progression has not been observed. |
| Video Ending | PARTIAL | No real ending video or ending provenance. |
| Arc Closed | PARTIAL | No completed canonical Arc. |
| Continue World | PARTIAL | No completed Arc 1/explicit Arc 2 UI transition. Generic regression verifies that Continue alone does not auto-submit media; this is not the requested live inheritance proof. |

## D. Mechanics

**Mechanics: PARTIAL.** Inventory, Wish, Clue and Claire relationship have real Runtime evidence. Clue and relationship were completed through Standard Player text continuation. Timed/QTE remains unverified; text mode suppresses recommendation scheduling.

| Mechanic | Confirmed authoring contract | Runtime result | Skill / Proposal / StateManager / before-after |
| --- | --- | --- | --- |
| Inventory | `inventory` v1.0.0; capacity 8; `addItem` / `removeItem` | PASS | `inventory_hud_traces.json` records three `skill.inventory` proposals; `inventory_action_before_state.json` → `inventory_hud_fixed_state.json` shows canonical medical supplies, ammunition and keycard. |
| Clue | clue-system v1.0.0 | PASS (real text Runtime) | clue_trace.json: clue_experiment_log_anomaly committed by br_00010_de1567; before/proposal/after captured. |
| Claire Relationship | relationship v1.0.0 | PASS (real text Runtime) | relationship_trace.json: char_204d12 old 50, delta +10, new 60, proposal mprop_00015_36321d, canonical br_00010_a0a79c. Rescue later increased trust to 70. |
| Wish | Formal player Wish capability | PASS for ACTIVE state | `wish_active.png` and `wish_active_traces.json` record the natural-language wish as ACTIVE; it did not force an ending. |
| Timed Interaction | `qte` v1.0.0; 15s, nonfatal fallback; cold sample room/control-center location gates | PARTIAL | Typed `TimedInteractionRequest` configured; no real countdown action, proposal, timeout/choice resolution or canonical consequence |

The final QTE configuration stores internal IDs for the reviewed cold sample room/control-center locations and fires only from canonical location/state. Those IDs are not evidence of live activation. No HUD screenshot or natural-language tutorial is treated as a StateManager commit.

## E. Visual QA

**Step 5 visual QA calls: 16 unique completion IDs recorded** — character candidates/references, first and accepted opening, three READY branches, FREE, inventory and a multi-character scene. These are visual text-model calls, not image/video generation.

| Required observation | Result | Boundary |
| --- | --- | --- |
| Leon Identity Stability | PASS | Fresh structured review accepted all four, retained canonical `ca_00016_628682`, and the reviewed H3 scenes preserved Leon identity. |
| Claire Identity Stability | PASS | Two candidates and the reviewed Leon + Claire scenes retained Claire identity. `visual_qa/claire_candidate_step5.json`. |
| Victor Identity Stability | PASS for existing candidates; video PARTIAL | Four candidates reviewed and canonical retained. Minor logo detail is not a major failure. `visual_qa/victor_candidate_step5.json`. |
| Character Separation | PASS | Three portrait pairs and the Leon + Claire H3 scene were accepted by Step 5 with separable identities. |
| Leon + Claire H3 | PASS | `multi_character.mp4` and `multi_character_step5.json` accepted the two-character scene. |
| Identity Swap | NO | Step 5 found `multi_character_identity_swap=false` in the reviewed opening, FREE and multi-character scenes. |
| Face Mix | NO | Step 5 found separable identities and no face mixing in the reviewed scenes. |
| Opening Semantics | PASS | `opening_step5.json` accepted scene semantics, action visibility and identity stability. |
| FREE Scene Semantics | PASS | `free_step5.json` accepted the maintenance/power-routing scene. |
| Ending Semantics | PARTIAL | Ending video was not generated after the low-balance stop. |

Latest QA count is deduplicated by completion ID in visual_qa/call_index.json; the nine elapsed_seconds records in the timing report are a timing subset, not the total call count.

Fresh QA evidence: `visual_qa/leon_candidate_review_step5.json`, request summary and validation JSON. Request used `reasoning_effort=high`, `max_tokens=32768`; actual response model was `step-5-preview`. Reported usage: 7,267 prompt + 2,644 completion = 9,911 tokens; provider-reported reasoning tokens were 0. The report records the requested setting without claiming measured high-effort internals.

Original image bytes were measured at 4096×4096 and hashed. QA used 2048×2048 review copies; no new image was generated and the source assets were not downgraded. The first Opening QA required retry for missing characters and incorrect staging. Later reviewed videos were accepted without identity swap or face mix. Responses supply completion IDs; absent HTTP request IDs remain explicitly absent.

**Image quality retries: 0 recorded. H3 quality retries: 1 Opening retry.** The eight early Relay edit failures remain historical transport failures; the later multipart adapter completed the required edits. Opening, READY-branch, FREE, inventory and multi-character video QA files are present; only ending QA remains absent.

## F. Provider / Cost

### Routes versus actual execution

| Logical capability | Configured provider/model | Actual evidence in this E2E |
| --- | --- | --- |
| Director | Local `nemotron_local` / `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`; fallback Step 5 Preview | Real opening and continuation traces use the local Nemotron route; current health is recorded in `continuation/nemotron_health.json`. |
| Narrative | Step / step-3.7-flash | Real Opening and continuation traces; ending video remains unverified. |
| Authoring | Step / `step-5-preview` | Real UI understanding/proposal/confirmation calls, including final mechanics and character reviews. |
| Decision | Jev / configured `jev-latest` | Real Top-3 lock and branch state are recorded in `three_ready_plus_free_input_state.json`; raw provider metadata is retained in the trace snapshot. |
| IMAGE_GENERATION | OpenAI-compatible `image_relay`; `gpt-image-2.5-sunburst` | Four earlier Leon outputs plus successful 4K Claire/Victor candidate outputs, with current Relay request IDs in `relay_character_assets_final.json`. |
| IMAGE_EDIT | Same configured Image Relay | 13 multipart edits succeeded with request IDs and 4K output; eight earlier 502/network attempts remain historical failures. |
| Video | Fal h3_max / minimax/h3-max/reference-to-video | 29 successful jobs including one key validation, all 480P and 5–9 seconds. |
| Visual QA | Step / step-5-preview | 16 unique completion IDs in visual_qa/call_index.json. Legacy calls without IDs excluded from exact count. |

Standard UI keeps provider/model/request/branch/state-machine diagnostics out of the user-facing workflow. They are recorded here as Developer evidence. Standard/Developer boundary checks pass for the observed Player path; only the intentionally unplayed ending tail remains incomplete.

### Usage reconciliation

| Required metric | Recorded value | Interpretation |
| --- | --- | --- |
| New paid media requests in Relay continuation | **55 external media HTTP attempts** | 5 Relay generation + 21 Relay edit attempts + 29 Fal H3 jobs (28 story + 1 key validation); Step 5 QA is not media generation. |
| Image Generation Requests | **5 external attempts / 3 succeeded** | Current durable ledger records two successful Claire/Victor batches plus one additional successful batch and two failed generation attempts. |
| Image Edit Requests | **21 external attempts / 13 succeeded** | Multipart Image Relay edits produced the approved Standard Reference Packs and Leon Outfit; eight older failed attempts are retained as historical diagnostics. |
| 4K Character Images | **10 candidate outputs plus 13 edited views/outfit assets** | Character assets use the configured Relay at 4K; no Fal image route was used. |
| Image Retries | **0 quality retries recorded** | Historical batch duplication/fallback cannot be fully reconstructed. |
| H3 accepted Jobs | 29 | 28 story jobs plus one explicitly authorized new-key validation, all succeeded. |
| H3 Successful | **29** | Opening, recommendations and mechanic scenes have playable artifacts. |
| H3 Retries | 1 Opening quality retry | First Opening missed Leon/Claire and misplaced Victor; continuation/opening_quality_retry.json records the single permitted retry after a generic fix. |
| H3 Total Requested Duration | 166 seconds | 161 story seconds plus 5 seconds for the explicit new-key validation. |
| Longest Shot | **9 seconds** | No request exceeded the 10-second cap. |
| Video Resolution | **480P** | All 29 H3 usage records report 480P. |
| Any Video >480P | **NO** | No higher-resolution video request was made. |
| Fal Nano Banana calls in this E2E | **0 recorded** | Image route remains Relay. No Fal image fallback or probe was used. |
| Aspect Ratio | **16:9 requested** | Historical Leon images actually returned 1:1; reported legacy aspect provenance was inaccurate. The adapter now preserves requested/submitted/actual values separately. |
| Exact monetary cost | **UNKNOWN** | Provider billing data was not captured; no estimate is presented as a charged amount. |

Historical sources: `leon_assets_current.json`, `leon_image_dimensions.json`, `usage_ledger_current_snapshot.json`, `provider_audit.json`. The last two are explicitly **pre-fix snapshots**, not claims about the final durable-ledger implementation. Empty process-local ledger snapshots do not erase earlier usage.

Current generic ledger fixes preserve external attempts, request IDs when returned, terminal status, parameter/reference summaries and transport uncertainty in a private append journal across restarts. Offline HTTP-spy tests verify those contracts. They cannot recover missing historical image HTTP IDs/counts or establish current account balances.

### Regression and deployment

- Backend: latest full regression **228 passed / 0 failed / 6 warnings** with Fal Guard OFF, mock providers and lifecycle disabled. `compileall` and `pip check` **PASS**. These tests are contract/regression evidence, not real-provider E2E evidence.
- Frontend: latest `npm ci` and `npm run build` **PASS**, 42 modules; `index-qs1l4fQb.js` and `index-B0pPKi6d.css`.
- Browser: character Scope A–F regression **PASS**, 1920×1080; publish-race, pressure-editing and preflight regressions passed with isolated API/network mocks. The live Creator review/publication used port 9000. No mock browser test is counted as H3/Relay acceptance.
- Deployment: `interaction.service` restarted and is **active on port 9000**. Served JS/CSS bytes and SHA-256 match the latest `dist` build. `GET /api/health` returns `provider_mode=live, profile=AGENT_LOCAL_PROFILE`; paid generation remains enabled, while recommendation pre-generation is disabled to protect balance.
- Restart preserved all user Scenario/Version/Session/Character objects. Existing startup seeding refreshed only official `rainy_apartment` / `ver_rainy_1_0_0` rows; this is not a claim that the entire database was byte-for-byte unchanged. Live paid generation remains **true and persisted**; Relay credential values remain outside Git.

## G. Bugs Found & Fixed

All listed fixes are generic. Leon/Claire/Victor/Umbrella/Raccoon City content is held in Scenario data, browser test/evidence inputs or this report; runtime logic does not special-case these names.

| Issue | General fix and verification | Remaining live boundary |
| --- | --- | --- |
| Creator character management below library granularity | Shared `CharacterStudio`, reference slots, outfit/pose/motion/voice operations, explicit inherited/empty overrides, pinned-version resolver and Promote; A–F persisted UI regression and character-scope tests. | Paid image/video quality not implied. |
| Promote could roll back newer library text from inherited old pin | `overlay_sources` controls promoted identity/personality/appearance fields; explicit overrides including empty values are allowed; inherited/unchanged legacy fields are not promoted. Three regressions. | No remaining reproduced case in tested scope. |
| AI Character Create combined text and paid image work | Text understanding/confirmation is distinct from media submission; Standard UI creation of Claire/Victor verified. Pending proposals survive same-session page closure. | Claire/Victor Relay candidates, reference edits, Outfit and QA are complete for the recorded scope. |
| Publish raced pending save, stale review and duplicate clicks | Wait/read saved draft, invalidate review when content changes, recheck before publish, synchronous shared submit lock; nine browser regressions, including missing-image warning visibility when the check itself is valid. | Real Standard UI 0.3.0 publication and snapshot readback passed. |
| ScenarioVersion and snapshots were not atomic | Publication now creates ScenarioVersion and all CharacterSnapshots in the same AsyncSession transaction from the frozen reviewed draft. Seven `test_publish_atomicity.py` regressions pass: injected first/second snapshot failures roll back first/existing publication; post-commit draft pin drift cannot alter the published snapshot source; compatibility preserved. | Closed for reproduced transaction/source-drift cases; final full suite **228 passed / 0 failed**. |
| Video controls covered Agency; Player did not default to Theater | Controls now remain in Stage, and Player entry defaults to in-app Theater. Four isolated cases changed from FAIL to PASS, covering both resolutions, error/Ready states, menu hit targets, Agency, HUD, navigation/reentry and input/session/progress preservation. Fresh deployed geometry and the live opening path pass. | Final build/deployment and default-entry checks pass; no additional media request came from layout verification. |
| Step pressure output leaked JSON or used an invalid driver | Shared lossless pressure normalization across generation/projection/confirmation/instruction/save/publish; explicit action/story-time drivers, no silent guessed semantics; 27 backend cases and five UI cases. | Current malformed live draft repaired through Standard UI and republished. |
| Preflight ignored actual formal settings and circuit | Effective K/shot/duration/reference limits, explicit unresolved counts, guard/circuit/credential checks; preview does not create fake ledger usage. Eleven backend cases and Settings UI regression. | An estimate is not an actual paid plan. |
| QTE could fire before the declared location | Typed location-gated config, canonical-location validation and generic timed-node checks; real mechanics recompiled/confirmed through UI. | Actual countdown/consequence still unplayed. |
| Opening/planning/reference/duration gaps | Formal Director opening, unauthorized state rejection, per-shot cast references, balanced reference limits, phase duration bounds, shot-count and duplicate-submit checks. | Real opening, Top-3 and multi-character H3 artifacts confirm the repaired path; ending remains intentionally unplayed. |
| Billing/invalid/uncertain submission retried too broadly | Terminal billing/auth/guard/request errors stop pipeline retries; uncertain submit is recorded distinctly; no mock canonical artifact on failure. Fault-injection and HTTP-spy regressions. | Remaining balance is deliberately protected; no automatic background generation is running. |
| Relay provenance, fallback and ledger incomplete | Capture returned request IDs/model/dimensions where available; explicit missing-credential failure; ordered Relay fallback for explicit model rejection or transient provider errors; durable private ledger; exact submit-attempt accounting in tests. | Old historical missing evidence remains unrecoverable. |
| Continue World could start media immediately | Explicit Continue creates Arc 2; subsequent player action starts new media. Generic regression covers this boundary. | Live Arc inheritance requires a real completed Arc 1. |

### Remaining blockers and residual risks

1. **Paid-03 incomplete:** real video Ending, Arc CLOSED, explicit Continue World and inherited canonical state remain unplayed. The earlier key was near one dollar; it has now been replaced and a single authorized validation succeeded. Automatic story media remains paused. This is not a claim about the new key balance.
2. **Timed / QTE incomplete:** the typed location gate and fallback contract are covered by regression tests, but no new paid chase was started after the balance warning.
3. **Clue terminal comparison recovered:** named terminal clue now committed through Skill/Proposal/StateManager in text mode. A later truncated Director response overflowed repair context; concise output and bounded repair fixed the reproduced continuation failure.
4. **Remaining Runtime gaps:** text mode suppresses Timed/QTE scheduling; evacuation narrative alone did not close the Arc. Neither is labeled PASS or concealed as a Fal billing issue.
5. **Historical audit gaps:** exact external request IDs for the oldest image batches cannot be recovered; they remain explicitly historical/unknown. Current Relay and H3 records include request IDs, provider, model, resolution and duration where returned.
7. **AT-44:** independent human feedback remains separate. The user's latest instruction keeps live paid generation enabled for that later testing; this overrides the earlier request to turn it off.

AT-80, early Jev exposure and publication transaction regressions pass. Full Runtime closure remains PARTIAL; see the explicit unverified/gap rows.

## Human Test Handoff

| Field | Status |
| --- | --- |
| Application | RUNNING |
| URL | `http://139.199.69.46:9000` |
| Provider Mode | live |
| Runtime Profile | `AGENT_LOCAL_PROFILE` |
| Nemotron Lightning | LOADED / serving; current `/models` check confirms the exact model, and a 200 tiny inference is recorded in `continuation/nemotron_health.json` |
| Step 3.7 | configured |
| Step 5 Preview | configured |
| Jev | configured |
| Image Relay | configured at `https://api-top.com`; `gpt-image-2.5-sunburst` preferred |
| Fal H3 | configured as `minimax/h3-max/reference-to-video` |
| Fal paid generation | enabled |
| Fal circuit | CLOSED |
| Recommendation video pre-generation | disabled; selection remains available and selected video is generated on demand |
| Biohazard Scenario | `scn_00003_364d7e`, published `0.3.0` / `ver_00001_1fa925` |
| Can create new Session | YES |
| Ready for manual testing | YES — stop at the published story/session entry; no background generation runs |

## Jev timing and cost policy

Before this fix, Player waited for `_maybe_publish` to see all H3 branches READY before showing Jev cards. The measured recommendation branch wall-clock range was roughly 96–111 seconds, while Director/Narrative/Production work was already complete earlier. The runtime now exposes locked labels as soon as the epoch is exposed and reports `media_ready` separately. With pre-generation disabled, video work waits for the player's selected branch, which preserves agency and prevents the three unselected H3 jobs from consuming the remaining balance.

## Phase timing

See [BIOHAZARD_FULL_E2E_TIMING.md](BIOHAZARD_FULL_E2E_TIMING.md) and `docs/acceptance/biohazard_full_e2e/phase_timings.json`. Recorded averages are: 4K Image HTTP 41.822s, H3 generation 19.275s, Step 5 QA 42.434s, Nemotron Director 9.226s, Step 3.7 Narrative 12.538s and Production 3.400s. These are measured phase spans; parallel branch durations must not be summed as a single user wait.

## Latest low-cost continuation and key handoff

- Existing Session retained: sess_00006_6051ee. No duplicate Scenario or Character created.
- Standard Player text actions produced canonical clue and Claire relationship changes. Evidence: continuation/text_tail, clue_trace.json, relationship_trace.json.
- Current media pre-generation setting is persisted false; paid generation is persisted true.
- New primary key fingerprint 19090382a2 replaced the previous primary fingerprint 49838f0961. Secondary fingerprint 20901bf4f9 is unchanged. Credentials exist only in ignored backend/.env.
- Explicit new-key validation: Fal minimax/h3-max/reference-to-video, 5s, 480P, 16:9; request 01a0d908-49b8-7613-8565-2532149fd835 succeeded in 20.091s with no retry/fallback. This is a key validation artifact, not a canonical story scene.
- New media in this handoff: 0 images, 1 explicitly authorized H3 validation. Text continuation created no media request.
- Five offline 1920x1080 cases verify input and playback controls reappear whenever a decision is available, including no recommendation cards.
- Long malformed Director output is no longer appended to repair context; a concise authoritative retry is used.

### Current text-tail limitation

After rescue, Claire trust reached 70. Evacuation branch br_00049_f32ffd became CANONICAL, but its outcome.ending was null, so prose saying the action ended did not close Arc 1. A subsequent disposal action br_00078_6edd5b was rejected because it proposed removeItem for an unowned sample; no illegal state patch committed and no video was generated. Timed/QTE is suppressed in text mode. Video Ending, formal Arc CLOSED and Continue World remain PARTIAL. These are explicit Runtime/model-contract gaps, not a credential blocker. The human handoff is the published Story Library; this existing text Session remains recoverable.

Final regression: 228 passed / 0 failed / 6 warnings. Frontend npm ci and build PASS; latest served files match dist by SHA-256. service is a user systemd unit and remains active. Local Nemotron model listing and tiny inference return HTTP 200. See continuation/key_handoff/health.json.

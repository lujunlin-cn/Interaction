# Biohazard FULL E2E Acceptance

Date: 2026-09-25. Story: **《生化危机：黑雨隔离区》**.

**Overall: PARTIAL.** The real Standard Creator path has been reviewed, corrected and published. The required complete three-character visual production and Creator → Player → video Ending → Continue World journey have not completed. No API checkpoint, upload fixture, old story artifact or mock result is counted as a real-provider play PASS.

| Audit field | Value |
| --- | --- |
| Requirements SoT | `Agent_Skills_Interactive_Drama_PRD_AI_v0.6.md`, with the user's later explicit provider/quality instructions |
| Start SHA | `1eabeb6afc89e8bdcb402f5b2b452499e7089b9e` |
| Inspected integration base | `803efbedc4d91b406159f439bb21ae590ab4f094`; working changes are included in the final integration commit |
| Final SHA | Updated in the delivery commit; verify with `git rev-parse HEAD` |
| Service | Port **9000** |
| Latest real UI publication | Scenario `scn_00003_364d7e`, version **0.2.0**, `ver_00001_b26e3c` |
| Latest review/publish | 1920×1080 Standard UI; final checkbox explicitly checked; one `publish` POST with `reviewed=true, play=false` |
| Latest published character pins | Leon v8; Claire v7; Victor v7 |
| Relay continuation media requests | **5 image-generation HTTP attempts: 3 succeeded, 2 failed; 8 image-edit HTTP attempts failed with transient 502/network errors; no Fal image requests** |
| Historical paid-media boundary | Four earlier Relay images plus this continuation's successful Claire/Victor candidates; the durable ledger records current Relay attempts. One H3 submit HTTP attempt failed billing, followed by one local blocked attempt. Zero accepted H3 jobs/videos. |
| Current blocker | Relay generation succeeds for Claire/Victor candidates, but `/v1/images/edits` returns 502/network errors for standard views and Outfit; no Fal image fallback is permitted. |
| Paid switch on live service | **Enabled**, as the user's latest instruction requires for later human testing. Two supplied Fal keys are configured; this continuation did not probe them. Old billing failure does not establish the current keys' balance. |

The image route is a **USER-approved cost optimization**: `IMAGE_GENERATION / IMAGE_EDIT → configured OpenAI-compatible Image Relay`, preferred model `gpt-image-2.5-sunburst`, fallback sequence documented in `IMAGE_RELAY_ACCEPTANCE.md`. Fal is reserved for H3 video in this E2E. The Fal image adapter remains in code and is not used here. The Relay credential is configured only in ignored `backend/.env`; no credential is committed.

## Evidence interpretation

- [Evidence index](docs/acceptance/biohazard_full_e2e/EVIDENCE_INDEX.md) identifies actual screenshots, readbacks, QA reports and missing proof.
- [Latest UI publication](docs/acceptance/biohazard_full_e2e/scenario_published_ui.json) supersedes the earlier API-only publication checkpoint for product-path acceptance.
- [Final parameter readback](docs/acceptance/biohazard_full_e2e/creator_review/final_parameters_readback.json) and [assertions](docs/acceptance/biohazard_full_e2e/creator_review/final_parameters_assertions.json) were captured before the final review checkbox and publication. [Root review](docs/acceptance/biohazard_full_e2e/creator_review/root_parameter_review.json) records the last visible page review.
- The earlier `0.1.0` publication `ver_00017_8f2d1c`, Session `sess_00028_dc6cb4` and opening `opening_00033_23675f` are diagnostic/API checkpoints. Their failed opening is not a successful Player journey. No Session was created by the final `0.2.0` UI publish.
- PASS below applies only to the named, observed step. PARTIAL includes blocked or unexecuted portions. It does not imply that an untested runtime feature has failed.

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
| Publish Gate | PASS | Twelve checks valid, missing-image warning retained. Operator checked review and published `0.2.0` via Standard UI; three snapshots returned. `scenario_published_ui.json`, `publish_reviewed.png`, `published_version.png`. |

The final draft treats Victor as a research supervisor, not a security supervisor; removes unsupported T-103 human-origin/obsession claims and predetermined Leon death; preserves the tradeoff between rescue, evidence and sample containment. These are Scenario data corrections through user-visible controls, not special runtime rules.

### Published character references

| Character | Library ID | Pinned version | Story scope |
| --- | --- | --- | --- |
| Leon | `chr_00013_113084` | 8 | Player role; selected RPD outfit `outfit_00005_931bd6`; reviewed personality/knowledge/relationship and wet, dirty uniform description |
| Claire | `chr_00018_204d12` | 7 | Newly UI-created library character; independent judgement and cooperation; rain/dust story appearance |
| Victor | `chr_00032_149758` | 7 | Newly UI-created library character; motive/secrets/limited knowledge; blood on coat and injured right arm story appearance |

The publication returned Leon `snap_00004_a7cb7f`, Claire `snap_00005_54ba2c`, Victor `snap_00006_1589b7`. Subsequent GET-only verification compared the snapshot set, each pinned version and each complete local override against the reviewed publication; all matched. See `character_snapshots_ui.json` and `published_snapshot_verification.json`. A full real Production reference-resolution trace is still required. Earlier Claire/Victor API-created records remain separate historical records and are not counted as the UI-created characters.

## B. Character System

**Character System: PARTIAL for this real-media E2E. AT-80 management scope is independently PASS.**

| Required step | Result | Evidence and boundary |
| --- | --- | --- |
| Leon AI Creation | PASS for text workflow | Standard creation evidence and later real AI understanding/confirmation; `leon_create_form.png`, `creator_review/leon_review_proposal.json`, `leon_review_confirmed.json`. |
| Leon 2×4K Candidate | PASS for existing outputs | Four candidate outputs from two historical service batches; all measured **4096×4096 PNG**. `leon_assets_current.json`, `leon_image_dimensions.json`. Exact external request count/IDs were not retained by the old adapter. |
| Leon Canonical | PASS | One of the four images, `ca_00016_628682`, is canonical; the other three are candidates. Step 5 retained the current canonical without regeneration. |
| Leon Standard Reference Pack | PARTIAL | Canonical front exists. The required complete front/three_quarter/side/full_front/full_side generated pack has not been completed. |
| Leon Outfit Edit | PARTIAL | Named RPD outfit exists and is selected in Scenario scope. A distinct real 4K IMAGE_EDIT output and canonical-versus-outfit QA are missing; a name/selection is not an edit PASS. |
| Claire AI Creation | PASS for text workflow | New character created and AI suggestions reviewed/confirmed through Standard UI; `claire_ui_character_creation.json`, `claire_review_confirmed.json`. |
| Claire 4K References | PARTIAL | Controlled Relay generation was attempted after credential configuration but returned HTTP 401; no candidate/canonical/reference pack was created. |
| Victor AI Creation | PASS for text workflow | New character created and AI suggestions reviewed/confirmed through Standard UI; `victor_ui_character_creation.json`, `victor_review_confirmed.json`. |
| Victor 4K References | PARTIAL | Controlled Relay generation was attempted after credential configuration but returned HTTP 401; no candidate/canonical/reference pack was created. |
| Three-character Identity Separation | PARTIAL | Cannot compare three visual identities until Claire/Victor have formal images. No fabricated separation QA. |
| Scenario Snapshots | PASS for publication; production PARTIAL | GET-only checks prove the exact three returned snapshots, pinned versions and complete local overrides match the reviewed publication; `published_snapshot_verification.json`. Media identity quality/resolver use await the real production path. |
| Scenario Overlays | PASS | Visible story edits/rebinding and readback preserve library definitions. `creator_review/ui_rebind_timeline.json`, `scenario_published_ui.json`. |
| Multi-character Resolver | PARTIAL | Generic cast/reference allocation tests pass. No successful Leon+Claire H3 scene proves actual provider use yet. |

The separate [AT-80 closure](CHARACTER_GRANULARITY_CLOSURE.md) proves shared Studio tabs, identity/reference management, outfit reference slots, selectable pose/motion, canonical/alternate voice, uploads/bind/unbind, versions, scenario isolation and explicit Promote. Its media are labeled upload fixtures in a separate mock database. That scope PASS is not real visual-generation or gameplay proof.

## C. Story Play

**Story Play: PARTIAL — the newly reviewed/published story has not entered a successful real video play session.**

| Required step | Result | Evidence and boundary |
| --- | --- | --- |
| Real Opening H3 | PARTIAL | Earlier API checkpoint hit billing failure before an accepted H3 job. No playable opening. The attempt requested 5s, below the requested opening 8–10s; generic phase-duration policy is now fixed and offline-tested, awaiting real validation. |
| Theater Mode | PASS for layout; real-media play PARTIAL | Port-9000 read-only historical failed-Session checks at 1920×1080 and 2560×1440 pass after fixing controls to stay inside Stage. Four isolated cases also verify default Theater entry, normal-window fullscreen=false, navigation/reentry, HUD and input/session/progress preservation. No new Biohazard opening is available; error-state layout proof is not H3 gameplay proof. |
| Decision Lead | PARTIAL | Not reached in the current story. Earlier cache-replay evidence is not substituted. |
| Real Jev Top-3 | PARTIAL | Configured real Jev route is not evidence of this story producing a real locked Top-3. |
| 3 / 3 Ready | PARTIAL | **0 / 3 confirmed READY** in this E2E. Zero accepted H3 jobs. |
| Free Input Visible With Three Options | PARTIAL | Required product checkpoint has not been reached. |
| FREE Branch | PARTIAL | No new real FREE media branch in this story. |
| FREE Canonical | PARTIAL | Not reached. No direct branch/status mutation used as proof. |
| Recommended Branch Selection | PARTIAL | No real ready recommendation selected through Player UI in this story. |
| Speculative Isolation | PARTIAL | Generic regressions exist; required real before/after World/Drama/inventory/relationship/knowledge evidence is absent. |
| Truth / Secret Boundary | PARTIAL | Authoring data now respects evidence boundaries; live disclosure progression has not been observed. |
| Video Ending | PARTIAL | No real ending video or ending provenance. |
| Arc Closed | PARTIAL | No completed canonical Arc. |
| Continue World | PARTIAL | No completed Arc 1/explicit Arc 2 UI transition. Generic regression verifies that Continue alone does not auto-submit media; this is not the requested live inheritance proof. |

## D. Mechanics

**Mechanics: PARTIAL.** Four mechanisms were compiled and confirmed through the real Standard Creator path. None of the five requested mechanisms has the required in-session Skill → Proposal → StateManager → before/after evidence for this story.

| Mechanic | Confirmed authoring contract | Runtime result | Skill / Proposal / StateManager / before-after |
| --- | --- | --- | --- |
| Inventory | `inventory` v1.0.0; capacity 8; `addItem` / `removeItem` | PARTIAL | Skill configured; live invocation, proposal and canonical inventory diff not produced |
| Clue | `clue-system` v1.0.0; DISCOVERED/VERIFIED/USED; `clues.*` | PARTIAL | Skill configured; live invocation, proposal and canonical knowledge/clue diff not produced |
| Claire Relationship | `relationship` v1.0.0; Standard hides values; `relationships.*` | PARTIAL | Skill configured; no live old/delta/new comparison or canonical trust update |
| Wish | Formal player Wish capability | PARTIAL | No ACTIVE Wish submitted in the current story; no preference-state before/after or later fulfilment evidence |
| Timed Interaction | `qte` v1.0.0; 15s, nonfatal fallback; cold sample room/control-center location gates | PARTIAL | Typed `TimedInteractionRequest` configured; no real countdown action, proposal, timeout/choice resolution or canonical consequence |

The final QTE configuration stores internal IDs for the reviewed cold sample room/control-center locations and fires only from canonical location/state. Those IDs are not evidence of live activation. No HUD screenshot or natural-language tutorial is treated as a StateManager commit.

## E. Visual QA

**Step 5 visual QA calls: 2 total** — one historical Leon candidate review and one fresh review of all four existing Leon images. These are visual text-model calls, not image/video generation.

| Required observation | Result | Boundary |
| --- | --- | --- |
| Leon Identity Stability | PASS for the four candidate portraits; pack/video PARTIAL | Fresh structured review accepted all four, retained canonical `ca_00016_628682`, zero major failures. |
| Claire Identity Stability | PARTIAL | No visual assets reviewed. |
| Victor Identity Stability | PARTIAL | No visual assets reviewed. |
| Character Separation | PARTIAL | Leon/Claire/Victor comparison not available. |
| Leon + Claire H3 | PARTIAL | No successful two-character video. |
| Identity Swap | NOT ASSESSED for multi-character media | Cannot report NO without a multi-character scene. |
| Face Mix | NOT ASSESSED for multi-character media | Cannot report NO without a multi-character scene. |
| Opening Semantics | PARTIAL | No video. |
| FREE Scene Semantics | PARTIAL | No video. |
| Ending Semantics | PARTIAL | No video. |

Fresh QA evidence: `visual_qa/leon_candidate_review_step5.json`, request summary and validation JSON. Request used `reasoning_effort=high`, `max_tokens=32768`; actual response model was `step-5-preview`. Reported usage: 7,267 prompt + 2,644 completion = 9,911 tokens; provider-reported reasoning tokens were 0. The report records the requested setting without claiming measured high-effort internals.

Original image bytes were measured at 4096×4096 and hashed. QA used 2048×2048 review copies; no new image was generated and the source assets were not downgraded. All four returned `accept`, no major artifact, and no quality retry. The response supplied a completion ID but no HTTP request ID; the two are kept distinct.

**Image quality retries: 0 recorded. H3 quality retries: 0.** The two historical image service batches are not relabeled as quality retries: their precise trigger and external attempt history cannot be reconstructed from the pre-fix ledger. Standard reference, outfit, separation and all video QA files remain absent because those media have not been produced.

## F. Provider / Cost

### Routes versus actual execution

| Logical capability | Configured provider/model | Actual evidence in this E2E |
| --- | --- | --- |
| Director | Local `nemotron_local` / `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`; fallback Step 5 Preview | Route/config evidence retained. No completed latest published-story Player chain certified. |
| Narrative | Step / `step-3.7-flash` | Configured route; no successful new opening/ending artifact used as proof. |
| Authoring | Step / `step-5-preview` | Real UI understanding/proposal/confirmation calls, including final mechanics and character reviews. |
| Decision | Jev / configured `jev-latest` | No actual locked Top-3 model/version response in the current play path. |
| IMAGE_GENERATION | OpenAI-compatible `image_relay`; `gpt-image-2.5-sunburst` | Four earlier Leon outputs plus successful 4K Claire/Victor candidate outputs, with current Relay request IDs in `relay_character_assets_final.json`. |
| IMAGE_EDIT | Same configured Image Relay | Eight current edit attempts were recorded as failed transient 502/network errors; no output was accepted. |
| Video | Fal `h3_max` / `minimax/h3-max/reference-to-video` | One historical POST rejected for billing. No accepted provider job ID or completed video. |
| Visual QA | Step / `step-5-preview` | Two review calls; fresh response explicitly records actual model, completion ID, usage and structured result. |

Standard UI keeps provider/model/request/branch/state-machine diagnostics out of the user-facing workflow. They are recorded here as Developer evidence. Full Standard/Developer boundary certification throughout Player remains incomplete because the play path is blocked.

### Usage reconciliation

| Required metric | Recorded value | Interpretation |
| --- | --- | --- |
| New paid media requests in Relay continuation | **13 external image HTTP attempts** | Five generation attempts (three succeeded, two failed) plus eight edit attempts (all failed transiently); no Fal image request. |
| Image Generation Requests | **5 external attempts / 3 succeeded** | Current durable ledger records two successful Claire/Victor batches plus one additional successful batch and two failed generation attempts. |
| Image Edit Requests | **8 external attempts / 0 succeeded** | Standard-view/edit requests returned transient 502/network failures; no mock or Fal fallback was used. |
| 4K Character Images | **10 recorded candidate outputs** | Four existing Leon assets plus six Claire/Victor candidate assets in the continuation; generated outputs report 4096×4096 where dimensions were returned. |
| Image Retries | **0 quality retries recorded** | Historical batch duplication/fallback cannot be fully reconstructed. |
| Historical H3 submit HTTP attempts | **1** | Billing failure; the second local blocked call did not reach HTTP. |
| H3 accepted Jobs | **0** | No provider job accepted. |
| H3 Successful | **0** | No playable output. |
| H3 Retries | **0 further HTTP retries recorded** | One later local circuit rejection; no quality retry. |
| H3 Total Requested Duration | **5 seconds in the one attempted POST** | Accepted-job duration 0 seconds. The blocked local retry is not counted as another paid request. |
| Longest Shot | **5 seconds requested; no generated shot** | This failed opening did not meet the requested 8–10s opening policy. Generic fix verified offline only. |
| Any Shot >10 sec | **NO in the recorded attempt** | No successful media exists for output-duration measurement. |
| Video Resolution | **480P requested** | No generated resolution to inspect. |
| Any Video >480P | **NO generated video** | Do not treat the absence of output as a successful quality check. |
| Aspect Ratio | **16:9 requested** | Historical Leon images actually returned 1:1; reported legacy aspect provenance was inaccurate. The adapter now preserves requested/submitted/actual values separately. |
| Fal Nano Banana calls in this E2E | **0 recorded** | Image route remains Relay. No Fal image fallback or probe was used. |
| Exact monetary cost | **UNKNOWN** | Provider billing data was not captured; no estimate is presented as a charged amount. |

Historical sources: `leon_assets_current.json`, `leon_image_dimensions.json`, `usage_ledger_current_snapshot.json`, `provider_audit.json`. The last two are explicitly **pre-fix snapshots**, not claims about the final durable-ledger implementation. Empty process-local ledger snapshots do not erase earlier usage.

Current generic ledger fixes preserve external attempts, request IDs when returned, terminal status, parameter/reference summaries and transport uncertainty in a private append journal across restarts. Offline HTTP-spy tests verify those contracts. They cannot recover missing historical image HTTP IDs/counts or establish current account balances.

### Regression and deployment

- Backend: latest full regression **197 passed / 0 failed / 6 warnings** with Fal Guard OFF, mock providers and lifecycle disabled. `compileall` and `pip check` **PASS**. These tests are contract/regression evidence, not real-provider E2E evidence.
- Frontend: final `npm ci` and `npm run build` **PASS** after Publish-warning/Player changes, 42 modules; `index-DBDSet8X.js` and `index-C4Yk5vqH.css`. See `frontend_build_final.txt`.
- Browser: character Scope A–F regression **PASS**, 1920×1080; publish-race, pressure-editing and preflight regressions passed with isolated API/network mocks. The live Creator review/publication used port 9000. No mock browser test is counted as H3/Relay acceptance.
- Deployment: `interaction.service` restarted and is **active on port 9000**. Served JS/CSS bytes and SHA-256 match the final `dist` build. Read-only post-restart health, route and ledger snapshots are in `deployment_final.json`, `environment.json`, `provider_matrix_final.json`, `usage_ledger_final.json`.
- Restart preserved all user Scenario/Version/Session/Character objects. Existing startup seeding refreshed only official `rainy_apartment` / `ver_rainy_1_0_0` rows; this is not a claim that the entire database was byte-for-byte unchanged. Live paid generation remains **true and persisted**; Relay credential values remain outside Git.

## G. Bugs Found & Fixed

All listed fixes are generic. Leon/Claire/Victor/Umbrella/Raccoon City content is held in Scenario data, browser test/evidence inputs or this report; runtime logic does not special-case these names.

| Issue | General fix and verification | Remaining live boundary |
| --- | --- | --- |
| Creator character management below library granularity | Shared `CharacterStudio`, reference slots, outfit/pose/motion/voice operations, explicit inherited/empty overrides, pinned-version resolver and Promote; A–F persisted UI regression and character-scope tests. | Paid image/video quality not implied. |
| Promote could roll back newer library text from inherited old pin | `overlay_sources` controls promoted identity/personality/appearance fields; explicit overrides including empty values are allowed; inherited/unchanged legacy fields are not promoted. Three regressions. | No remaining reproduced case in tested scope. |
| AI Character Create combined text and paid image work | Text understanding/confirmation is distinct from media submission; Standard UI creation of Claire/Victor verified. Pending proposals survive same-session page closure. | Claire/Victor Relay candidates exist; reference views, Outfit edits and QA remain incomplete. |
| Publish raced pending save, stale review and duplicate clicks | Wait/read saved draft, invalidate review when content changes, recheck before publish, synchronous shared submit lock; nine browser regressions, including missing-image warning visibility when the check itself is valid. | Real Standard UI v0.2.0 publication and snapshot readback passed. |
| ScenarioVersion and snapshots were not atomic | Publication now creates ScenarioVersion and all CharacterSnapshots in the same AsyncSession transaction from the frozen reviewed draft. Seven `test_publish_atomicity.py` regressions pass: injected first/second snapshot failures roll back first/existing publication; post-commit draft pin drift cannot alter the published snapshot source; compatibility preserved. | Closed for reproduced transaction/source-drift cases; final full suite **197 passed / 0 failed**. |
| Video controls covered Agency; Player did not default to Theater | Controls now remain in Stage, and Player entry defaults to in-app Theater. Four isolated cases changed from FAIL to PASS, covering both resolutions, error/Ready states, menu hit targets, Agency, HUD, navigation/reentry and input/session/progress preservation. Fresh deployed read-only error-state geometry also passes both resolutions. `docs/acceptance/player_stage_controls/browser.json`, `theater_readonly.json`. | Final build/deployment and default-entry checks pass; zero paid media submitted. |
| Step pressure output leaked JSON or used an invalid driver | Shared lossless pressure normalization across generation/projection/confirmation/instruction/save/publish; explicit action/story-time drivers, no silent guessed semantics; 27 backend cases and five UI cases. | Current malformed live draft repaired through Standard UI and republished. |
| Preflight ignored actual formal settings and circuit | Effective K/shot/duration/reference limits, explicit unresolved counts, guard/circuit/credential checks; preview does not create fake ledger usage. Eleven backend cases and Settings UI regression. | An estimate is not an actual paid plan. |
| QTE could fire before the declared location | Typed location-gated config, canonical-location validation and generic timed-node checks; real mechanics recompiled/confirmed through UI. | Actual countdown/consequence still unplayed. |
| Opening/planning/reference/duration gaps | Formal Director opening, unauthorized state rejection, per-shot cast references, balanced reference limits, phase duration bounds, shot-count and duplicate-submit checks. | Real H3 proof absent. |
| Billing/invalid/uncertain submission retried too broadly | Terminal billing/auth/guard/request errors stop pipeline retries; uncertain submit is recorded distinctly; no mock canonical artifact on failure. Fault-injection and HTTP-spy regressions. | New supplied Fal keys not charged/probed in this continuation. |
| Relay provenance, fallback and ledger incomplete | Capture returned request IDs/model/dimensions where available; explicit missing-credential failure; model fallback only for explicit model rejection; durable private ledger; exact submit-attempt accounting in tests. | Old historical missing evidence remains unrecoverable. |
| Continue World could start media immediately | Explicit Continue creates Arc 2; subsequent player action starts new media. Generic regression covers this boundary. | Live Arc inheritance requires a real completed Arc 1. |

### Remaining blockers and residual risks

1. **Relay edits incomplete:** the credential is configured outside Git and candidate generation succeeded, but standard-view edits returned transient 502/network errors. Ordered Relay fallback is offline-tested; paid fallback is not yet verified. Keep Relay for all 4K images/edits. Do not route to Fal Nano Banana or generate speculative “test” media.
2. **Paid-01 incomplete:** complete Leon reference pack/outfit edit, Claire/Victor candidates/canonicals/reference packs, 3-character separation and Step 5 identity QA. Explicitly update Scenario pins to newly approved media versions and republish after review.
3. **Paid-02 incomplete:** new UI Session, real opening, real Jev Top-3 with 3/3 H3 READY, FREE while three options remain visible, selected recommendation and all five mechanisms with canonical diffs. Restore exact job/request/duration/cost evidence from the new ledger.
4. **Paid-03 incomplete:** real video Ending, Arc CLOSED, explicit Continue World and inherited canonical state, preserving old ending/history without auto-submitting Arc 2 media.
5. **No known remaining non-Fal P0 in the verified scope:** publication atomicity and Theater control/default-entry defects were fixed. Seven publication cases, four Player layout cases, final 197-test suite and final build/deployment checks pass. No real-provider PASS is inferred from them.
6. **Historical audit gaps:** exact image HTTP count, external image request IDs and independent upstream model confirmation cannot be recovered; they remain UNKNOWN. Final application SHA is the containing integration commit supplied in the delivery reply.
7. **AT-44:** independent human feedback remains separate. The user's latest instruction keeps live paid generation enabled for that later testing; this overrides the earlier request to turn it off.

No known functional P0 remains in the browser-verified AT-80 management scope or the reproduced publication transaction cases. That scoped result does not close the full real-provider journey. **Paid-01 / Paid-02 / Paid-03 are not yet directly executable end to end until the Relay credential is available and the three character visual prerequisites are completed.**

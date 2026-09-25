# Live Creator parameter review and UI publication

Service: `http://127.0.0.1:9000`; exact Scenario: `scn_00003_364d7e`.
Date: 2026-09-25. Standard UI only for authoring writes; GET-only API readback verified persistence. The final operator review and **Publish new version** action completed through Standard UI as **v0.2.0** (`ver_00001_b26e3c`). It did not click Play or create a Session. Parameter review, this publication and snapshot verification submitted no image generation, image edit or video requests. This zero-media statement is specific to those phases, not the entire E2E directory.

## Completed before AI review

- Overview: title set to 生化危机：黑雨隔离区; description corrected to 1998, Leon/Claire/Victor, research supervisor and T-103.
- World: seven requested location labels; infection/door/death/movement/permission/knowledge rules; power, cold storage, resources, survivor pressure and nonfatal timeout constraints.
- Characters: 28 visible CharacterProfile edits correct Leon/Claire names and agency, Victor's motive/knowledge/secrets, and the T-103 threat. No global binding, pinned version or outfit selection was changed.

`static_review_timeline.json` and `character_review_timeline.json` record each visible edit/save. `before.json`, `after_static_review.json`, `after_character_review.json` contain readback. Screenshots show the actual Standard UI.

## Real AI review completed

Step 5 Preview received the corrected story intent through the Standard Drama understanding control. Eleven proposals were returned; the creator accepted understood items and then manually refined misbeliefs, conflict and anchors. World and character arrays compared unchanged. A separate natural-language mechanics request returned all four enabled mechanisms with typed configs, installed skill/version/trigger/StatePatch contracts, and a 15-second nonfatal timed interaction; the user-confirmation button persisted them.

## Pinned versions reviewed

Creator → each character → Versions → View changes → Update explicitly moved Leon v2→v3, Claire v1→v2, Victor v1→v2. Scenario overlays and selected outfit stayed unchanged. RPD outfit is now available and selected from Leon's actual pinned version. Old Leon v2 plus a later outfit caused HTTP422 during initial manual Drama save attempts; those attempts were not counted as successful. They were repeated after explicit version updates and verified by GET readback.

## Repaired failures and final checks

Real Step 5 returned a malformed pressure row layout, and the overview AI instruction later returned a JSON array encoded as a string. The backend currently accepted that representation, exposing raw JSON in Standard. `pressure_instruction_result.json` and screenshots preserve the failure. The general authoring normalization fix has now been deployed. The Standard UI was refreshed and saved five natural-language pressure rows; readback proves five valid name/source/trigger rows and no raw JSON visible. See `pressure_repaired_readback.json` and `pressure_repaired_ui.png`.

The parameter-editing phase did not publish or create a Session. The root operator subsequently inspected the final World, Drama, Mechanics and Character pages, explicitly checked the review checkbox and published through Standard UI. Publication evidence is described below. Full E2E remains incomplete because authoring publication alone does not establish media readiness or successful Runtime play.

## Real Character Library AI creation and confirmation

After repairing AI Create to require text review before media generation, two new characters were created using Standard UI and the supplied one-sentence definitions: Claire `chr_00018_204d12` v7 and Victor `chr_00032_149758` v7. Earlier API-created records remain untouched and are not counted as this UI creation evidence. Each returned real Step 5 understanding proposals. The operator accepted stable personality/desire/fear, refined ambiguous appearance descriptions, and ignored unsupported secrets. Creator has now removed only the earlier scenario references and added these UI-created library characters through the formal picker. The prior library records were retained. All reviewed story-specific text, Claire rain/dust and Victor blood/right-arm injury were restored via visible edit/save controls; comparisons confirmed library definitions stayed unchanged. See `ui_rebind_timeline.json`.

Existing Leon `chr_00013_113084` received real AI understanding through the overview button, then reached v8 after selected textual confirmations. His four existing images and canonical image were preserved. The proposed appearance included transient rain/dust and insufficient identity detail, so it was ignored. Knowledge was corrected to avoid assuming a first-day officer already knows every street/facility.

The initial Claire UI proposal was lost when the automation closed its browser before confirmation. This exposed a recovery issue: pending character understanding is now stored per character in sessionStorage and removed/updated when accepted/ignored. Claire's proposal was requested once more through the formal UI and reviewed. This extra text call is recorded; no image generation was repeated.

Files: `{claire,victor}_ui_character_creation.json`, `{claire,victor,leon}_review_proposal.json`, `{claire,victor,leon}_review_confirmed.json` and corresponding UI screenshots. All character review requests are text creation, text understanding or explicit character PATCH confirmation; media requests remain zero in this review phase.

## Final parameter checkpoint before Publish

`final_parameters_readback.json` is the fresh backend readback after all UI writes; `final_parameters_assertions.json` contains strict checks. Final page screenshots cover World, Drama, Mechanics, Characters and the unchecked Publish Gate. Seven locations, corrected truth/secrets/T-103, four ending families, all four installed mechanisms and pressure contract pass authoring checks. QTE is now both location-gated (cold sample room/control center) and 15 seconds with a nonfatal outcome. The real Step 5 mechanics request was repeated after that general contract repair and accepted through Standard UI.

Final bound library versions at this checkpoint: Leon v8 (`chr_00013_113084`), Claire v7 (`chr_00018_204d12`), Victor v7 (`chr_00032_149758`). Leon RPD outfit remains selected. Publish checklist is 12/12 valid. The backend response retains the missing-image warning for Claire and Victor; a missing visual identity does not block a text-only publication. The parameter checkpoint itself is **authoring-parameter PASS**, not runtime mechanics or video readiness.

## Reviewed and published through Standard UI — PASS

The root operator reviewed every final parameter page at 1920 × 1080, checked
“我已审阅这个故事”, and clicked “发布新版本”.

- Final visible-page review: `root_parameter_review.json` and `root_{overview,world,drama,mechanics,characters}_review.png`.
- Gate before confirmation: `../publish_gate.png`.
- Explicit human-style review: `../publish_reviewed.png`.
- Successful version history: `../published_version.png`.
- Captured UI request and response: `../scenario_published_ui.json`; one `POST /api/scenarios/scn_00003_364d7e/publish`, body `reviewed=true, play=false`.
- Published version: **v0.2.0**, `ver_00001_b26e3c`.
- Immutable snapshots: Leon **v8** → `snap_00004_a7cb7f`; Claire **v7** → `snap_00005_54ba2c`; Victor **v7** → `snap_00006_1589b7`.

`../character_snapshots_ui.json` contains the live snapshot response.
`../published_snapshot_verification.json` verifies the three snapshot IDs,
bound versions, all story overlay fields and selected Leon outfit against the
captured publication. It uses two read-only GET requests and performs no writes.

The older `../scenario_published.json` is a **v0.1.0 API checkpoint** and is not
used as evidence of this UI publication. Its earlier Session is also not claimed
as successful Player E2E.

The green asset gate initially hid its advisory detail in Standard UI. The
localized frontend repair now displays the natural-language warning while
preserving text publication and explicit review. The isolated browser regression
in `../../publish_safety/` records the failure before repair and **9 passed / 0
failed** afterward; no live publication or media submission occurs in that test.

This checkpoint does **not** claim Claire/Victor images, complete reference
packs, multi-character H3, Runtime mechanics, Ending or Continue World PASS.
Later library media versions require explicit Scenario version updates and a
new reviewed publication before they can be used by a new Session.

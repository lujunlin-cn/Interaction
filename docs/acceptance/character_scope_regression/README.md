# Character scope browser regression

Date: 2026-09-25. Resolution: 1920×1080. Result: PASS.

This is the no-cost AT-80 scope regression, not the Resident Evil real-provider E2E. It ran against an isolated temporary SQLite database and mock backend on port 9001. The production service on port 9000 was not changed. Every state mutation was made through rendered Standard UI controls; read-only API reads verified persistence, pinning, and library isolation.

Safety settings: `FAL_PAID_GENERATION_ENABLED=false`, `PROVIDER_MODE=mock`, `PROFILE_LIFECYCLE_ENABLED=false`. Browser interception prohibited generation/edit/session submit endpoints and non-local network traffic. Generation/edit submission attempts: **0**. The uploaded assets are explicit local test fixtures labeled `LOCAL TEST FIXTURE / NO AI GENERATION`, one-second silent WAV files, and one-second solid-color MP4 files. None are real-provider acceptance evidence.

## Verified UI flow

- Manual library creation → five standard reference-pack uploads; side reference unlink and existing-pool rebind persisted.
- Default + Yellow Raincoat outfits → name/description and front/side/back/full-body/additional asset uploads; outfit side unlink/rebind persisted.
- Three pose references and two motion references → actual persisted arrays.
- Canonical Voice A + alternate Voice B → controls include audio audition.
- Creator adds the same library character at v24.
- A: Yellow Raincoat selection changes only scenario outfit.
- B: Three poses reduced to two; explicit empty override also verified, then two restored.
- C: Two motions reduced to one.
- D: Voice B selection overrides story voice; library Voice A remains canonical.
- Browser refresh preserves all checked choices.
- Story-only pose upload, identity override and local outfit/reference upload leave the library byte-for-byte unchanged. Story reference null override and explicit restore inheritance were verified.
- E: Library advances v24→v25; story remains v24, Continue v24 preserves it, Update v25 refreshes inherited personality while retaining media overrides.
- F: Explicit Promote creates library v26; story stays pinned v25. Prior immutable CharacterVersion records compare byte-for-byte equal.

## Evidence

`scope_regression.json` contains exact state snapshots and strict assertion outcomes. The PNG files show both library and Creator panels. `regression.cjs` is the replayable Playwright script. The first development run stopped on an automation selector mismatch before scenario mutations; the final complete run passed. A visual review found and corrected stretched checkboxes inherited from the generic form stylesheet, then the complete run and screenshots were repeated.

Run the script with an isolated prepared mock server only. It uploads local fixtures and creates test characters/scenarios. Optional environment variables: `PLAYWRIGHT_MODULE`, `CHROMIUM_PATH`, `TEST_BASE_URL`, `FIXTURE_DIR`, `EVIDENCE_DIR`.

## AI creation confirmation regression

`ai_create_two_stage.json` and the matching browser script/screenshots verify a separate mock UI case after the creation-flow repair. AI Create now calls only character text creation and the understanding endpoint. Suggested personality/motivation/appearance remain proposals until a user accepts each card. Accepting a card creates the next CharacterVersion. Merely creating/reviewing the character creates zero CharacterAssets and zero generation/edit submits. The appearance tab retains an explicit two-candidate generation button. This test ran with paid guard OFF and does not prove real AI semantic quality.

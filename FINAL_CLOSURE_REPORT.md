# PRD v0.6 Final Closure

日期：2026-09-24

## PASS

- Backend regression: `44 passed, 6 warnings` with `PROVIDER_MODE=mock` and empty `SOL_H3_BASE_URL`.
- Server-side Decision Lead Gate exposes READY recommendations only after `position >= lead`.
- Real multi-shot contract submits one Provider Job per Shot and records `jobs`, `clips`, and `shot_ids` in Trace.
- Publish versions are server-owned and incremented from the latest ScenarioVersion.
- Missing global character references block publish.
- Typed AI patches cover world, drama, theme, characters, and mechanics with lock-prefix enforcement.
- Formal Character Studio actions are available in the React Character Library and `frontend/src/api.ts`.

## PARTIAL

- H3 Max real multi-shot was not re-run in this session because external fal task evidence was unavailable. Hybrid routes `h3_max -> mock_video` with provenance.
- Sol-H3 is implemented and historical output evidence exists, but no new target-machine output was captured.
- Existing five viewport screenshots remain under `docs/acceptance/shots/`; no new browser capture was possible because npm dependencies could not be installed.

## BLOCKED

- Nemotron 3.5 Lightning 30B-A3B NVFP4 was not running. `gemma3:27b` remains fallback only and is not PASS evidence.
- `npm run build` could not run because `node_modules` is absent and the environment rejected the required remote npm tarball.
- Actual model unload/start hooks for AGENT_LOCAL <-> VIDEO_LOCAL require the DGX service supervisor; the API timeline remains an orchestration boundary until connected.

## Evidence

- Existing viewport evidence: `docs/acceptance/shots/home_1366.png`, `home_1920.png`, `home_2560.png`, `creator_1440.png`, `creator_3840.png`.
- Historical H3 Max and Sol-H3 evidence is documented in `G29_MODEL_DEPLOY_AUDIT.md`; stale v0.5 claims are marked superseded.

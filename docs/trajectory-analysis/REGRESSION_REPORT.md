# Regression and deployment report

Date: 2026-09-26. Backend: **257 passed, 0 failed**, 96.19 seconds, six existing warnings. Frontend production build: **PASS**. Targeted new/relevant suite: **19 passed**. Final isolated browser regression: **PASS**, seven checks, no live writes and no paid media requests.

Artifacts: backend_regression.txt, targeted_regression.txt, frontend_build.txt, browser/results.json, browser/*.png.

Checks cover original intent/confirmed strategy propagation, prefill and cancellation, explicit mechanic targets, duplicate/conflicting proposals, secret-free ScenePacket projection, terminal idempotency, stale historical selections, duplicate pipeline/regenerate calls, spent recommendations, persisted trace restart/idempotency, and proposal-vs-commit metrics. Existing publish atomicity, character snapshots, paid guards, Theater and offline mock suites remain included in the full run.

## Test isolation incident and correction

The initial existing conftest inherited live profile lifecycle hooks and reused itest.db. This allowed an early test process to switch local model containers and parallel tests to conflict on SQLite. Fixed to a unique process-owned temporary DB/media/data directory with PROFILE_LIFECYCLE_ENABLED=false. Restored Nemotron and verified model listing and inference. Final full regression did not stop live services. Earlier failed logs are historical harness diagnostics, not current PASS evidence.

## Service handoff

A separately launched uvicorn process occupied 9000 while interaction.service was inactive / repeatedly failing to bind. Consolidated the identical app into the enabled systemd user service through a short graceful restart. Linger=yes. Final exact health/config/model proof is human_test_handoff.json. Application remains live on 9000, AGENT_LOCAL_PROFILE, Nemotron loaded. Fal paid generation remains enabled; Jev prediction media pre-generation remains disabled. No media health probe was sent.

The new Observatory successfully answers from the live app; historical missing spans are not fabricated or imported into canonical runtime. Browser fixture evidence is clearly distinct from live health checks and real-provider text research.

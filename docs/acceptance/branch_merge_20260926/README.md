# Player branch integration — 2026-09-26

Base main: 8e6056c909bb725f59f27f99ff794e3d99891a14.

Branches requested for integration:

- ux/player-crawl at e2026f6: already an ancestor of main; its opening crawl and Player buffering logic are retained.
- fix/player-buffering-and-generating-interstitial at 9134a291b1f51c76c8b8142666f668f78f5f6a21: merged with both parents preserved.

No textual merge conflicts. Integration checks found three concrete incompatibilities, corrected in this merge:

1. Optional interstitial text was awaited while holding the same session lock it needed, delaying completed media by up to eight seconds. Cancel outstanding optional work when media completes or is cancelled; never wait for it at the assembly gate.
2. Interstitial Narrative received the full Director brief, including hidden truth. It now receives only the authorized ScenePacket. Initial effects are checked after the packet is built, and terminal pending branches no longer keep waiting text visible.
3. Waiting text inside interaction-dock was hidden by Theater's pre-decision CSS. Render it inside the generating-stage status with bounded scrolling; decision controls keep their visibility policy.

The incoming feature may add one optional Narrative text request during real FREE/OPENING media generation. This is distinct from Jev speculative video generation, which remains disabled. Optional text cannot commit state. The previous trajectory research counts are historical to their captured revision, not a claim about this added text feature.

Validation:

- Full backend: **263 passed, 0 failed**, 95.01 seconds (backend.txt).
- Targeted pending-effects / skill tests: **22 passed** (targeted.txt).
- Final frontend production build: **PASS** (frontend.txt).
- Isolated browser: opening/skip, visible waiting text and actual phase, waiting text cleared after completion, first-frame buffering without full overlay, recovery to playback: **PASS** (browser.json).
- Browser evidence uses intercepted API fixtures and synthetic media events. It is not a new paid-media E2E.
- New image/video requests: **0**.
- Application and Nemotron handoff: health.json.

Added regressions cover hidden-context exclusion, effects revelation boundary, terminal pending visibility and fast-video/slow-optional-text scheduling. Existing trajectory contracts, cancellation, StateManager, paid guards, snapshots and mock regression remain included in the complete suite.

Original user PDF/screenshots in temp are left unmodified and uncommitted. No credential/config files are included.

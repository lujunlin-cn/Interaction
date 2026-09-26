# ADR-004: Freeze replay benchmarks and capture live trajectory state separately

Date: 2026-09-26
Status: Accepted

## Original Design

Trajectory reports and replay receipts were generated from a point-in-time
dataset, while the live SQLite database continued to receive manual-test and
recovery sessions. A later mining run could silently replace the evidence used
for the before/after comparison.

## Trajectory Evidence

The frozen corpus contains 42 deduplicated sessions and 214 typed turn
records. The current live database contains 49 sessions, 76 persisted spans,
207 branches and 32 player input events. The later records include recovery
and manual handoff activity and cannot be treated as a controlled replay
cohort.

## Observed Problem

Mixing the two captures makes the sample denominator drift and can present
post-fix recovery events as if they were part of the original baseline. It
also encourages mining tools to open the production database during replay.

## Decision

Keep `dataset.json`, `replay_sessions.json` and their before/after receipts
immutable for the frozen benchmark. Store a point-in-time inventory under
`docs/trajectory-analysis/current_capture_20260926/`. The
`tools/trajectory_replay_benchmark.py` command validates the frozen
`TrajectoryTurn` envelope, reads only stored receipts, verifies source hashes,
and records zero provider, media, player API, or canonical database writes.

## Expected Impact

Replay comparisons retain a stable denominator and are safe to run while the
live service is serving manual tests. New live observations remain visible
for follow-up research without being misrepresented as controlled evidence.

## Compatibility

Runtime behavior and StateManager authority are unchanged. Existing replay
commands continue to use the frozen files. The current capture is additive and
does not change session or branch state.

## Migration

Future studies create a new dated `current_capture_*` directory and explicitly
declare whether it is an exploratory cohort or a frozen benchmark. A promoted
benchmark must copy its source hashes and provenance rules into a new report;
it must never overwrite an older capture in place.

## Rollback

Delete the additive capture directory and benchmark tool/test. The original
frozen reports and runtime are unaffected.

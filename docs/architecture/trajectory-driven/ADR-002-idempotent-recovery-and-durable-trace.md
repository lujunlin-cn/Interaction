# ADR-002 — Idempotent recovery and durable Skill traces

Date: 2026-09-26. Status: implemented.

## Original Design

Tracer.emit broadcasts and stores recent in-memory spans but has no persistence consumer. Skill history query expects inventory-prefixed names while emitted names are skill.inventory. Repeated select historically returns 409; internal _commit_selected has no terminal short circuit. Repeated regeneration can start competing tasks.

## Evidence / Problem

Database trace rows=0 despite 467 recovered evidence spans. PDF issue7 reports repeated branch/video/options. Regression reproduces repeat canonical submission and duplicate task creation. These reproductions establish defects, not a historical count of all loop incidents.

## Options / Decision

Choose separate batched, idempotent trace persistence with visible failure counters. Return existing canonical receipt on current-choice retry, exclude spent canonical/selected/provisional branches from fresh choices, and reuse running pipeline/regeneration tasks. Existing fingerprints and StateManager idempotency keys still guard state. This changes duplicate-select response from 409 to idempotent 200 for successful network retry; update the regression expectation and verify world/turn history unchanged.

## Expected Impact

No repeated presentation/state mutation from the verified retry cases. Recoverable generation errors stay recoverable. Durable post-restart Skill evidence improves competition demonstration and future research. No claim that all narrative stagnation or playback bugs are resolved.

## Compatibility / Migration

TraceSpan table already exists: no schema migration. New JSON Branch fields default empty. UI changes limited to feedback 4/5/7/8; other UX changes are separately owned. Pytest uses a unique temporary DB and disables inherited profile lifecycle hooks so regression cannot delete another run's DB or stop the production model.

## Rollback

Revert writer/lifespan and query separately from gameplay policies. Do not delete historical traces. Revert response semantics alongside its test if clients cannot tolerate idempotent 200. Never rollback by disabling live services.

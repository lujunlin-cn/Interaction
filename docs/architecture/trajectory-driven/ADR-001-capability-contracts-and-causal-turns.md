# ADR-001 — Evidence-driven gameplay capability boundaries

Date: 2026-09-26. Status: implemented, evaluation limits retained.

## Original Design

PRD v0.6 puts semantic adjudication in Director, decision ranking in Jev and typed mechanic effects behind StateManager. Registry mostly lists implementation modules. Intent echo can ask the player to fill missing desire/strategy. The Player presents scene/video but no explicit action→result receipt.

## Trajectory Evidence

Frozen cohort: 25 real-provider-observed sessions, 26 acted turns, 16 FREE branches. Branch br_00335_aa08da acquires a rocket while declaring it USED; br_00010_cdc5e0 has the same stage/action mismatch. br_00010_cb8111 contains redundant clues envelope plus typed clue effect. Code shows confirmed strategy omitted from actual Director input. PDF issues 4/5/7/8 supply independent user UX observations.

## Observed Problem

Lost intent, repeated or contradictory proposals, opaque action/video causality, and unhelpful choice descriptions are routing/contract defects, not proof that the text model cannot reason.

## Options

1. Add a separate LLM critic/router for every function: high latency and difficult attribution.
2. Rewrite Runtime: large regression surface.
3. Compose existing calls through a versioned semantic packet, bounded joint arbitration and role-specific context, plus causal presentation (chosen).

## Decision

Implement Understand Free Action v2, Evaluate Choices v1, Reconcile Mechanics v1. Extract policies/schema; keep typed mechanic adapters and sole StateManager commit authority. AI pre-fills confirmation with editable, optional hypotheses; explicit cancellation never runs an action. Narrative proposes a single visible core action for existing Production; complex results remain readable text. Known outcomes and actual location delta feed Player action/result receipt.

## Expected Impact

Less discarded reasoning; prevent specific unsafe proposal patterns; improve interpretability. Context reduction is measured in characters. Story quality, semantic choice diversity and Ready latency require independent replay/online evidence, not assertions from unit tests.

## Compatibility / Migration

New Branch fields have defaults; old sessions still load. Immutable published scenario snapshots untouched. No new image/video calls, Provider route or local profile changes. Existing approved early text-options/deferred-media behavior is retained; this ADR does not change the historical READY-vs-exposure policy. A future PRD must explicitly distinguish decision availability from media readiness.

## PRD Amendment

Propose v0.7 sections: capability contracts and observability; authoritative confirmed semantic packet; AI prefilled optional intent; action/result/visible-focus presentation; distinct decision/media readiness. This is a documented UX/capability extension, not a waiver of speculative isolation or truth authority. Do not claim that unknown entities can now never leak merely because a prompt says so.

## Rollback

Revert capability Runtime integrations and UI receipt together; old data remains readable. Disable new skills only in Developer for diagnosis, noting arbitration fail-closed. Restore old candidate behavior if relevance regresses. Do not change Provider credentials or destroy evidence.

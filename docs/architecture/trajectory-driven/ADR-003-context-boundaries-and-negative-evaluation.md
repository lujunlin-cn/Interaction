# ADR-003 — Context boundaries and negative replay results

Date: 2026-09-26. Status: implemented limited projection; broader semantic critic deferred.

## Original Design

Narrative sees a minimal ScenePacket with personality, revelation permissions and relationships. Inventory, canonical location and authorized typed effects were absent. Director sees complete character asset metadata. Top-K candidates and player-visible options were not separated in research comparison.

## Trajectory Evidence

Stored 119 real-provider branches allow exact context-size comparison. Text replay br_00010_262ca1 invented portable equipment; br_00010_040fd6 unlocked a remote object. The first is a Narrative grounding problem; the second originates in Director. A rocket outcome remained unsupported even without a state patch.

## Observed Problem

More prose or valid JSON does not establish correct state. A ScenePacket without possessions/location encourages inventions, but contradictory historical canonical/prose state cannot be corrected by Narrative. Comparing five candidates to three final options rewards count, not quality.

## Options / Decision

1. Mandatory LLM continuity critic on every turn: defer pending labeled false-rejection/cost data.
2. Give every agent full world/secret JSON: reject.
3. Add known_state and authorized_changes to ScenePacket; keep hidden truth excluded; retain typed world/rules in Director; strip only known media metadata (chosen).
4. Correct evaluation to equal Jev-selected Top-3; preserve invalid preliminary reviews in evidence and exclude them from aggregate metrics.

## Expected Impact

Better observable authority boundaries and smaller Director context. No guarantee that a small model obeys constraints. Two fixed-outcome follow-up replays did not resolve all phantom props; record this rather than repeatedly tuning on the same examples.

## Compatibility / Migration

Optional ScenePacket fields with empty defaults keep old sessions readable. No automatic world repair, no altered historical snapshots, no additional normal-turn LLM call. Director adjudication and StateManager commit authority remain unchanged. Newly persisted traces contain narrative state projections and output proposals for future labels.

## Rollback / Quality Gate

Projection is independently removable without data migration. No promise of fewer tokens or faster Ready without controlled measurement. Semantic choice reranking and automatic knowledge reconciliation remain research candidates. General quality remains PARTIAL until observed old-preferred cases and held-out examples pass independent assessment. PRD v0.7 should describe these boundaries and incomplete knowledge explicitly.

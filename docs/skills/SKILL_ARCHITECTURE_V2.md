# Agent Skill Architecture v2

## Actual execution chain

Player raw input → Jev observation → **Understand Free Action v2** → [AI preview only if clarification/confirmation needed] → player approval → immutable ActionSemanticPacket → Director adjudication → **Reconcile Mechanics v1** → inventory/clue/relationship proposal adapters → ScenePacket → Narrative (one visual_focus) → Production plan → existing media pipeline → **StateManager** atomic commit → action/result/transition presentation.

After the current canonical beat: **Evaluate Choices v1** → grounded action/purpose candidates → exact duplicate filter → Jev ranking with readable context + OTHER evidence → existing decision epoch. No new speculative H3 request is introduced.

All nodes emit versioned spans. Developer → System Skills → Skill Observatory shows per-branch inputs, why triggered, policy result and proposal disposition. Standard mode only shows story and editable intent, never raw skill IDs.

## Formal contracts

Executable manifests: backend/app/skills/registry.py (CAPABILITY_CONTRACTS).
Policies: backend/app/skills/gameplay_policy.py.
Schemas and pure policies: backend/app/skills/gameplay.py.
Runtime orchestration: backend/app/runtime/engine.py.

| Capability | When / inputs | Outputs | Failure / fallback | Allowed effects / evaluation |
|---|---|---|---|---|
| Understand Free Action v2.0.0 | FREE raw text + Jev semantic observation + confirmed edits; ambiguity triggers preview | ActionSemanticPacket (original, effective action, strategy, desire, quoted constraints, provenance); editable preview | Preview unavailable → preserve original, optional fields empty. No execution before confirmation | Trace only before approval; original retention, cancellation, confirmation propagation, blinded fidelity |
| Evaluate Choices v1.0.0 | Canonical decision epoch + recent canonical outcomes, known state, wishes/preferences | Concrete action + plain purpose, rank, OTHER, exact-duplicate decisions | Provider unavailable → existing generic state-grounded candidates. High OTHER retained, no automatic recursive reroll | No canonical writes; relevance/knowledge/diversity evaluation; no claim that exact dedup solves semantic duplication |
| Reconcile Mechanics v1.0.0 | Director outcome + inventory, known NPC targets, clue lifecycle + enabled mechanic config | ArbitrationResult, typed proposals, explicit per-trigger decisions | Conflict → one bounded Director correction on same action; second failure recoverable before media | No world mutation; rejects unowned removal/use-as-acquisition/unknown target/conflicts; StateManager final validation |

Policies are composed around existing model calls. The new preview can add one call on ambiguous input; arbitration can add one corrective Director invocation (the existing schema retry policy still applies). Normal successful full turns have no added model call. No claim that calls/turn decreased.

## Examples (scenario-independent)

- “先到配电室恢复供电，不相信广播的指引” retains order/negation in the packet. A confirmed “不追击” strategy reaches the actual Director prompt.
- “用急救包处理伤口” cannot create an acute-care item via an inventory USED/add proposal. If the item is absent, the Director must explain the obstruction or adjudicate another player-approved action.
- Two identical relationship deltas from repeated triggers collapse to one proposal; two conflicting deltas require adjudication, never silently sum.
- Retrying the current selected canonical branch returns the existing receipt. It does not replay its video, add another turn or mutate the world.

## Persistence and observability

Trace writer batches 250 spans every 250ms independently of canonical transactions, retries uncertain writes idempotently by span ID and keeps a capped 10,000-span pending queue. A DB failure must not make a story commit fail. Pending/failure/drop counters are visible; this is best effort durability, not a claim of lossless crash-proof logging. Shutdown drains when possible. No model/container cleanup is performed by the trace writer.

Skill metrics: invocations, success/failure/fallback, recorded latency samples, proposed effects and linked committed branches. Trigger precision/recall and shared model token attribution remain null without evidence. Recent five calls query both persisted and pending spans by skill_id/name. Trace body retention contains user story text; no credentials are intentionally logged.

## No Skill explosion

Three reusable capability contracts are enhanced/introduced. Context projection, prompt formatting, StateManager, dedup and ffmpeg remain ordinary code/tools. We do not claim autonomous agents where only a deterministic transformation exists. Skills are discoverable through registry, independently tested, versioned and evaluated with historical outputs and separately labeled live-text counterfactuals.

## Narrative follow-up

ScenePacket now includes canonical known_state (location, inventory, clues, knowledge) and branch-authorized typed changes, while hidden revelations remain excluded. This is a context boundary, not a semantic proof. Follow-up negative results and old-preferred cases are retained in SKILL_EVALUATION.md. Understand Free Action spans attach to the resulting branch so the Observatory can show the complete capability chain; QUICK_ACK remains session-scoped because it creates no media branch.

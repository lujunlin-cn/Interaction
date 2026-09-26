# Trajectory Analysis — research before implementation

## Data Sources / Reconstruction
{
  "real_observed_sessions": 25,
  "real_player_turns": 26,
  "real_openings": 24,
  "real_speculative_branches": 69,
  "real_free_branches": 16,
  "real_canonical_free": 13,
  "real_failed_branches": 30,
  "real_skill_trigger_counts": {
    "clue-system": 13,
    "inventory": 13,
    "relationship": 8
  }
}

42 deduplicated sessions: 25 real-provider-observed, 14 mixed, 2 mock/fixture, 1 unknown. 214 branch records are not 214 player turns. Among real-provider-observed branches: 26 acted turns, 24 openings, 69 speculative branches. 474 source files, 467 recovered spans, 69 unique ledger operations. Database trace table is empty. Frozen read sets provide partial before-state; original canonical-after per turn cannot always be reconstructed without guessing. Missing observability is explicit.

## Failure Taxonomy / Gameplay Bottlenecks
1. Skill and provider traces disappear on restart.
2. Inventory use can become acquisition; phantom possession then affects later turns.
3. Discovered evidence lacks a clue proposal, so HUD/state lag behind prose.
4. Jev ranking lacks current story context; high OTHER is ignored.
5. Jev semantic observation and confirmed intent edits are dropped before Director.
6. Canonical character metadata bloats planning context.
7. Prose says movement/ending while the typed state remains unchanged.
8. Secrets guard historical name matches blocked harmless openings (already fixed).
9. Character reference and shot cast failures cost recovery time (existing fixes retained).
10. Media/provider schema/billing errors obscure gameplay; do not treat media retry as agent intelligence failure.

## Agent Redundancy / Skill Trigger Analysis
Jev classifies once, Director plans once, Narrative renders once: no evidence of four repeated understanding calls. Waste is discarded observation, repeated context, and uncontrolled proposal semantics. 34 real recorded mechanic triggers: inventory 13, clue 13, relationship 8. Missing trigger recall cannot be computed without labels; evidence_without_clue is a review queue, not an automatic false-negative count. qte is deterministic orchestration; Wish is preference state. Assembly/provider adapters are tools, not agent reasoning capabilities.

## Free Action / Top-K / Context / State Consistency
See dedicated reports. Preserve StateManager as only commit authority. Speculative isolation must be tested rather than assumed from absence of errors. Add a semantic packet carrying original/confirmed action, quote-grounded constraints and existing Jev observations. Add one mechanic arbitration capability: explicit skill outputs checked as a group; reject contradictions rather than invent facts. Role-context projection is a deterministic tool used by these skills, not a cosmetic new Skill.

## Latency / Cost
Historical spans contain partial latency/usage; no valid end-to-end median for every stage. No media requested during research. Never label unchanged stored Narrative as a newly generated improved story. Replay will distinguish recorded-output policy comparison, text-only counterfactual, regression fixtures and real historical evidence.

## Prioritized hypotheses and implementation plan
H1 Trace is lost because emit has no durability consumer; verify restart retrieval. H2 richer Jev context and action packet preserve previously discarded information; verify exact input invariants and blind text replay. H3 inventory proposal stage/action contradictions cause unsafe state; reproduce on frozen turns then reject/repair before Narrative. H4 asset metadata dominates planning context; measure lossless role projection.

Implement four bounded changes: durable Skill Observatory; reusable Understand Free Action contract; State-bound Mechanic Arbitration with one bounded Director correction; role-specific context plus exact-deduplicated choice ranking. Do not rewrite media or create 20 Skills. Before/after and limitations will be added to SKILL_EVALUATION.md after replay.

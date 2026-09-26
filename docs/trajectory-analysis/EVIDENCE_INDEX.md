# Research Evidence Index

Start SHA: c22d14bceea3930e2dd2c25eaaf449bc85fbbd0a. Root report: ../../TRAJECTORY_DRIVEN_SKILL_OPTIMIZATION_REPORT.md.

| Evidence | Meaning |
|---|---|
| TRAJECTORY_SOURCE_INDEX.md / source_index.json | Source hashes, timestamps, provenance, event types, completeness |
| dataset.json / replay_sessions.json | Frozen reconstructed envelopes and historical state; not live DB |
| TRAJECTORY_TURN.schema.json / schema_validation.json | Unified envelope; 214 validated records |
| TURN_TIMELINES.md | 16 real FREE causal timelines; missing steps explicit |
| TRAJECTORY_ANALYSIS.md / FAILURE_TAXONOMY.md | Pre-implementation hypotheses, roots and updated dispositions |
| GAMEPLAY_CHAIN_PROFILE.md / gameplay_profile.json | Per-branch observations; missing != zero |
| FREE_ACTION_ANALYSIS.md / TOPK_ANALYSIS.md / CONTEXT_ANALYSIS.md | Focused corpus analysis |
| replay_results.json / replay_isolation.json | 56 proposal comparisons, 119 contexts, frozen hash invariance |
| recovery_replay.json | Duplicate retry at 31 historical canonical states, no persistence |
| text_replay/*.json | 8 real local-Director / Step3.7 counterfactuals |
| text_replay/infrastructure_failure/ | Earlier transport/budget harness failures, not gameplay outcomes |
| choice_replay/*.json | 3 real Director/Jev contexts; old candidates and scores preserved |
| pairwise/ | Shuffled A/B FREE judgments and preliminary choice judgments |
| pairwise_choices/ | Corrected equal-Top3 choice judgments; final metrics use these |
| narrative_context_replay/ | Two fixed-outcome follow-ups, negative results retained |
| evaluation_metrics.json / evaluation_summary.txt | Before/after, critic receipts and limitations |
| browser/results.json / browser/*.png | Intercepted fixture UI regression, not live media acceptance |
| backend_regression.txt / frontend_build.txt | Final complete regression/build |
| REGRESSION_REPORT.md | Isolation incident, correction, deployment |
| human_test_handoff.json | Real service/model/config, tiny inference; secrets redacted |
| current_capture_20260926/ | Current live DB/source inventory at the audit Start SHA; kept separate from the frozen benchmark |
| ../../tools/trajectory_replay_benchmark.py | Read-only typed replay benchmark; validates 214 turns and records zero media/network/database writes |
| PLAYER_FEEDBACK_SCOPE.md | PDF issues 4/5/7/8 ownership |

Related: ../skills/CURRENT_SKILL_AUDIT.md, ../skills/AGENT_SKILL_OPPORTUNITIES.md, ../skills/SKILL_ARCHITECTURE_V2.md, ../skills/SKILL_EVALUATION.md, ../architecture/trajectory-driven/ADR-*.md.

The frozen/live boundary is specified in [ADR-004](../architecture/trajectory-driven/ADR-004-frozen-replay-and-live-capture-boundary.md).

## Reproduction

Frozen offline runs use no media and do not mutate live sessions:

    cd backend
    .venv/bin/python ../tools/replay_trajectories.py
    .venv/bin/python ../tools/replay_recovery.py
    .venv/bin/python ../tools/profile_trajectories.py
    .venv/bin/python ../tools/evaluate_trajectory_replay.py

Mining refreshes the frozen cohort; do not overwrite an established benchmark silently:

    .venv/bin/python ../tools/mine_trajectories.py

Real text-only research is opt-in. Existing completed files are reused:

    .venv/bin/python ../tools/replay_trajectories.py --text-replay --limit 8
    .venv/bin/python ../tools/trajectory_critic.py --choices
    .venv/bin/python ../tools/trajectory_critic.py --critique --critique-choices
    .venv/bin/python ../tools/replay_narrative_context.py

No replay invokes Image/Video providers. Stored Artifact paths are not new media. Keep live services running while replay executes in memory.

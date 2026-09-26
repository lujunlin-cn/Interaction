# Gameplay Chain Profile

| Metric | Value |
| --- | --- |
| real_observed_sessions | 25 |
| real_player_turns | 26 |
| real_openings | 24 |
| real_speculative_branches | 69 |
| real_free_branches | 16 |
| real_canonical_free | 13 |
| real_failed_branches | 30 |
| real_skill_trigger_counts | {'clue-system': 13, 'inventory': 13, 'relationship': 8} |
| rank_calls | 11 |
| other_over_50_percent | 4 |


| Provider | Observed calls with latency | Median ms | Max ms |
| --- | --- | --- | --- |
| step_37 | 22 | 12160.0 | 20621 |
| nemotron_local | 55 | 5616 | 59436 |
| step_5 | 1 | 34100 | 34100 |


Counts are lower bounds: 77 recovered provider.text records are not the entire execution history. Branch routes omit retries and session-level candidate/intent calls. Zero duration means missing, not instantaneous. Timelines in dataset.json retain phase timestamps and canonical events. created-to-ready includes queue/media; it is not Jev latency. K-ready uses epoch branch_ready events; deferred text-ready is separate from media-ready. Historical ledger has no reliable branch correlation for every request: do not assign all 43 H3 operations to canonical turns or call all speculative media waste. Human and automation operation ownership is not recorded. Future traces require turn_id, purpose, model request ID, usage, proposal decisions, explicit before/after snapshots.

## Reproducible per-turn metrics

See gameplay_profile.json. Recorded created→Ready: n74, median 97062.5ms; created→canonical: n31, median84948ms. Different cohorts; include media/queue/user waiting. FREE share among acted records: 16/26 (61.5%); canonical FREE13/16 (81.25%), not semantic fidelity. Complete stage/call/token denominators remain unavailable, not zero. No new-media latency comparison this round.

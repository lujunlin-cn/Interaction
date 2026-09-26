# Current Trajectory Replay Verification

This receipt was generated on 2026-09-26 from the existing frozen
`dataset.json` and saved offline replay result. It is a verification capture,
separate from the historical benchmark and reports, so rerunning the command
cannot rewrite historical evidence.

```bash
python tools/trajectory_replay_benchmark.py
```

The command validates all normalized `TrajectoryTurn` records, rejects
duplicate turn IDs, and records provenance and missing-observability counts.
It does not import the runtime, open the live database, call a provider, submit
Image/H3 work, or commit canonical state. Source hashes are checked before and
after the run.

Observed in this capture:

- 42 deduplicated sessions and 214 trajectory records.
- 119 records with real-provider provenance (provenance is not proof of human
  operation).
- 16 real-provider FREE turns; 13 have a recorded canonical status.
- 467 stored spans and 79 historical media job records.
- 0 new network calls, image requests, video requests, or canonical writes.
- Frozen source hashes unchanged.

Missing fields remain explicit in `replay_benchmark.json`; no token count,
trigger precision, or current Ready latency is inferred from incomplete logs.

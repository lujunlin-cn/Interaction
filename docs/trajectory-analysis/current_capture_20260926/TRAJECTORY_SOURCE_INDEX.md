# Current Trajectory Source Index (2026-09-26)

Capture ID: `current_capture_20260926`
Repository HEAD: `e4ecb92474953614def564c09743431494c1fbb2`
Captured: `2026-09-26T10:27:57.045693+00:00`
Frozen benchmark reference: [`../TRAJECTORY_SOURCE_INDEX.md`](../TRAJECTORY_SOURCE_INDEX.md), captured at SHA `c22d14bceea3930e2dd2c25eaaf449bc85fbbd0a`.

This directory is a point-in-time, read-only inventory of the live SQLite state plus existing evidence files. It does **not** overwrite `dataset.json`, `replay_sessions.json`, `source_index.json`, or the 42-session frozen benchmark. No provider, image, video, or player API call was made.

## Inventory summary

| Source class | Count | Notes |
| --- | ---: | --- |
| Acceptance JSON/JSONL | 485 | All parse successfully; hashes and extracted IDs in [`source_index.json`](source_index.json). Includes recovery, browser, and fixture evidence; provenance remains per source. |
| Trajectory-analysis artifacts | 84 | Frozen datasets, replays, metrics, reports, logs, and text outputs; not new live turns. |
| Root acceptance/trajectory reports | 9 | Reports referenced by the research/E2E handoff. |
| Usage ledger | 1 | Current private ledger is inventoried by hash; operation counts below come from its JSONL rows. |
| Runtime DB snapshot | 1 | `backend/itest.db` hash plus sanitized session/span/job summaries in [`db_snapshot.json`](db_snapshot.json). |
| Acceptance media | 348 | 295 PNG, 42 JPG, 11 MP4; binary hashes are in `source_index.json`, not copied. |
| Trajectory-analysis media | 3 | PNG evidence screenshots; binary hashes are in `source_index.json`. |
| Usage ledger records | 241 rows / 76 unique operations | Provider/status counts are preserved in `capture_metadata.json`; credentials are not. |

## Live DB counts at capture

| Metric | Value |
| --- | ---: |
| Session rows | 49 |
| Persisted trace spans | 76 |
| Job rows | 6 |
| Branch records in session state | 207 |
| Player input events | 32 |
| Branch statuses | CANONICAL=37, FAILED=62, GENERATING=1, INVALIDATED=46, NARRATIVE=4, PLANNING=3, PRODUCTION=1, READY=53 |
| Branch sources | fallback=6, free=23, opening=35, recommendation=125, timed=18 |
| Session provenance | mixed=14, mock_or_fixture=2, real_provider_observed=32, unknown=1 |
| Span names | director.plan=9, narrative.beat=9, narrative.interstitial=3, production.shots=8, provider.text=30, session.create=8, video.resume=2, video.submit=7 |
| Span providers | h3_max=9, nemotron_local=35, runtime=8, step_37=24 |
| Job statuses | GENERATING=2, READY=4 |

The database currently contains 26 `rainy_apartment` sessions and 23 `scn_00003_364d7e` sessions. This live cohort differs from the frozen benchmark because additional human-test/recovery sessions were created after its capture. Across all hashed JSON/JSONL/media sources, 55 distinct session IDs and 218 distinct branch IDs are referenced; evidence-only IDs may predate or outlive the live rows.

## Session inventory

| Session | Scenario | Provenance | Branches | Player input events | Branch status counts | Providers observed |
| --- | --- | --- | ---: | ---: | --- | --- |
| sess_00003_0fb7c7 | rainy_apartment | mock_or_fixture | 9 | 1 | CANONICAL:2, INVALIDATED:5, READY:2 | mock_text, mock_video |
| sess_00003_13fa29 | rainy_apartment | mixed | 7 | 4 | FAILED:5, READY:2 | mock_text, mock_video, step_37, step_5 |
| sess_00003_1f0161 | rainy_apartment | mock_or_fixture | 3 | 0 | READY:3 | mock_text, mock_video |
| sess_00003_25930d | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00003_3452cf | rainy_apartment | mixed | 4 | 0 | CANONICAL:1, FAILED:2, READY:1 | mock_video, nemotron_local, step_37 |
| sess_00003_7e1bf3 | rainy_apartment | mixed | 8 | 3 | CANONICAL:1, INVALIDATED:3, NARRATIVE:3, PRODUCTION:1 | mock_video, step_37, step_5 |
| sess_00003_847a85 | rainy_apartment | unknown | 3 | 0 | FAILED:3 | — |
| sess_00003_a0ed4a | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00003_abf087 | rainy_apartment | mixed | 10 | 0 | CANONICAL:1, FAILED:2, INVALIDATED:1, READY:6 | mock_video, step_37, step_5 |
| sess_00003_b830d5 | rainy_apartment | mixed | 8 | 1 | CANONICAL:1, FAILED:4, READY:3 | mock_video, nemotron_local, step_37 |
| sess_00003_e13d4c | rainy_apartment | mixed | 8 | 2 | CANONICAL:1, INVALIDATED:3, NARRATIVE:1, PLANNING:3 | mock_video, step_37, step_5 |
| sess_00003_e8a091 | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | step_37 |
| sess_00003_ebe93c | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00003_fef0ad | rainy_apartment | mixed | 11 | 4 | CANONICAL:2, FAILED:3, INVALIDATED:3, READY:3 | mock_text, mock_video, step_37 |
| sess_00004_b28f5d | rainy_apartment | real_provider_observed | 3 | 0 | FAILED:3 | nemotron_local, step_37 |
| sess_00006_273c79 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00006_301048 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00006_6051ee | scn_00003_364d7e | real_provider_observed | 27 | 11 | CANONICAL:10, FAILED:3, INVALIDATED:14 | h3_max, nemotron_local, step_37 |
| sess_00006_80d9a4 | scn_00003_364d7e | real_provider_observed | 4 | 1 | CANONICAL:1, FAILED:3 | h3_max, nemotron_local, step_37 |
| sess_00006_97bc74 | scn_00003_364d7e | real_provider_observed | 4 | 0 | CANONICAL:1, READY:3 | h3_max, nemotron_local, step_37 |
| sess_00006_d3d0ee | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00006_f91c09 | scn_00003_364d7e | real_provider_observed | 7 | 0 | CANONICAL:2, INVALIDATED:2, READY:3 | h3_max, nemotron_local, step_37 |
| sess_00007_b1da61 | rainy_apartment | mixed | 9 | 1 | CANONICAL:2, FAILED:4, INVALIDATED:2, READY:1 | mock_video, nemotron_local, step_37 |
| sess_00012_654bef | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00018_0a81a7 | rainy_apartment | mixed | 3 | 0 | FAILED:1, READY:2 | mock_text, mock_video, step_37, step_5 |
| sess_00022_fb2272 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00025_e74624 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_5 |
| sess_00026_06c1dc | rainy_apartment | mixed | 3 | 1 | FAILED:1, READY:2 | mock_text, mock_video, step_37 |
| sess_00027_85e25d | scn_00003_364d7e | real_provider_observed | 1 | 0 | GENERATING:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00028_dc6cb4 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00041_0b4332 | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00049_9cfbcf | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00051_e8762c | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00073_f412f8 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00076_d08233 | rainy_apartment | mixed | 5 | 1 | CANONICAL:1, FAILED:4 | mock_video, nemotron_local, step_37 |
| sess_00082_a45ab4 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | h3_max, nemotron_local, runtime, step_37 |
| sess_00101_7db4d3 | scn_00003_364d7e | real_provider_observed | 15 | 1 | CANONICAL:4, FAILED:1, INVALIDATED:3, READY:7 | h3_max, nemotron_local, step_37 |
| sess_00109_ff6a3b | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_5 |
| sess_00117_dbef86 | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, runtime, step_37 |
| sess_00121_429d09 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | nemotron_local, step_37 |
| sess_00134_b8fc5a | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_5 |
| sess_00184_7d3e48 | rainy_apartment | mixed | 3 | 0 | READY:3 | mock_text, mock_video, step_37 |
| sess_00230_fede82 | rainy_apartment | mixed | 3 | 0 | READY:3 | mock_text, mock_video, step_37 |
| sess_00301_04498e | rainy_apartment | mixed | 3 | 0 | READY:3 | mock_text, mock_video, step_37 |
| sess_00610_fa931e | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00660_754715 | scn_00003_364d7e | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00722_5ab523 | scn_00003_364d7e | real_provider_observed | 4 | 0 | CANONICAL:1, READY:3 | h3_max, step_37, step_5 |
| sess_00811_59bde4 | rainy_apartment | real_provider_observed | 1 | 0 | FAILED:1 | step_37, step_5 |
| sess_00876_839552 | scn_00003_364d7e | real_provider_observed | 19 | 1 | CANONICAL:6, INVALIDATED:10, READY:3 | h3_max, step_37, step_5 |

## Provenance and completeness rules

- `real_provider_observed` means a persisted route/span names a configured real provider such as Nemotron, Step 3.7, Jev, or Fal H3; it does not prove that media completed or that a human drove the session.
- `mixed` combines real-provider records with mock/fixture records in the same source or session.
- `mock_or_fixture` is isolated from real-provider metrics. `unknown` means no provider marker was present.
- A failed branch or job is retained as historical evidence. It is not evidence that the current implementation still fails.
- Each source entry includes `complete: false` unless a future capture can prove a full causal chain. Exact before-state, full provider attempts, token counts, skill consideration labels, and canonical-after snapshots remain missing; they are not inferred from final state.
- Media binaries under `backend/data/media` remain in place and are intentionally not copied into this capture. Acceptance screenshots/video (348 files, 364,187,744 bytes) and trajectory screenshots (3 files, 280,337 bytes) are hash-indexed in `source_index.json`; no binary is duplicated.

## Reproduction / reconstruction

- Read-only source hashes and extracted IDs: [`source_index.json`](source_index.json). Each entry exposes `sessions`, `scenarios`, `turns`/`branches`, timestamp range, event types, provider provenance, strict `complete` status, failure count, and canonical-snapshot marker.
- Sanitized live DB metadata, span names/providers, and job rows: [`db_snapshot.json`](db_snapshot.json).
- Capture metadata, counts, and caveats: [`capture_metadata.json`](capture_metadata.json).
- Frozen research replay remains authoritative for before/after comparisons; use the current snapshot only to explain post-freeze additions.

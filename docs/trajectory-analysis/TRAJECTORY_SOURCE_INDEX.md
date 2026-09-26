# Trajectory Source Index

Start SHA: `c22d14bceea3930e2dd2c25eaaf449bc85fbbd0a`. Dataset capture: 2026-09-26T07:27:57.382538+00:00.

Read-only repeatable-read database capture plus 474 JSON/JSONL evidence sources. Exact paths, hashes, sessions, branch IDs, timestamps, event types, provenance and completeness are in [source_index.json](source_index.json). Domain IDs deduplicate repeated screenshots/checkpoints. `replay_sessions.json` freezes source state; `dataset.json` normalizes causal records.

**A session with real providers is not proof of a completed real-media E2E.** Mixed/mock/unknown data are separate; failed requests and text-mode recovery are retained. Sessions from evidence only are included once. No missing before-state, tokens or trigger labels are invented.

| Session | Scenario | Provenance | Branches | Player input events | Sources |
| --- | --- | --- | --- | --- | --- |
| sess_00003_0fb7c7 | rainy_apartment | mock_or_fixture | 9 | 1 | 1 |
| sess_00003_13fa29 | rainy_apartment | mixed | 7 | 4 | 1 |
| sess_00003_1f0161 | rainy_apartment | mock_or_fixture | 3 | 0 | 1 |
| sess_00003_25930d | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00003_3452cf | rainy_apartment | mixed | 4 | 0 | 1 |
| sess_00003_7e1bf3 | rainy_apartment | mixed | 8 | 3 | 1 |
| sess_00003_847a85 | rainy_apartment | unknown | 3 | 0 | 1 |
| sess_00003_a0ed4a | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00003_abf087 | rainy_apartment | mixed | 10 | 0 | 1 |
| sess_00003_b830d5 | rainy_apartment | mixed | 8 | 1 | 1 |
| sess_00003_e13d4c | rainy_apartment | mixed | 8 | 2 | 1 |
| sess_00003_e8a091 | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00003_ebe93c | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00003_fef0ad | rainy_apartment | mixed | 11 | 4 | 1 |
| sess_00004_b28f5d | rainy_apartment | real_provider_observed | 3 | 0 | 1 |
| sess_00006_6051ee | scn_00003_364d7e | real_provider_observed | 27 | 11 | 43 |
| sess_00006_80d9a4 | scn_00003_364d7e | real_provider_observed | 4 | 1 | 1 |
| sess_00006_97bc74 | scn_00003_364d7e | real_provider_observed | 4 | 0 | 5 |
| sess_00006_f91c09 | scn_00003_364d7e | real_provider_observed | 7 | 0 | 1 |
| sess_00007_b1da61 | rainy_apartment | mixed | 9 | 1 | 1 |
| sess_00009_0791da | scn_00009_1cba84 | real_provider_observed | 15 | 6 | 10 |
| sess_00012_654bef | scn_00003_364d7e | real_provider_observed | 1 | 0 | 3 |
| sess_00018_0a81a7 | rainy_apartment | mixed | 3 | 0 | 1 |
| sess_00025_e74624 | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00026_06c1dc | rainy_apartment | mixed | 3 | 1 | 1 |
| sess_00028_dc6cb4 | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00041_0b4332 | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00051_e8762c | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00073_f412f8 | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00076_d08233 | rainy_apartment | mixed | 5 | 1 | 1 |
| sess_00101_7db4d3 | scn_00003_364d7e | real_provider_observed | 15 | 1 | 1 |
| sess_00109_ff6a3b | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00121_429d09 | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00134_b8fc5a | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00184_7d3e48 | rainy_apartment | mixed | 3 | 0 | 1 |
| sess_00230_fede82 | rainy_apartment | mixed | 3 | 0 | 1 |
| sess_00301_04498e | rainy_apartment | mixed | 3 | 0 | 1 |
| sess_00610_fa931e | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00660_754715 | scn_00003_364d7e | real_provider_observed | 1 | 0 | 1 |
| sess_00722_5ab523 | scn_00003_364d7e | real_provider_observed | 4 | 0 | 1 |
| sess_00811_59bde4 | rainy_apartment | real_provider_observed | 1 | 0 | 1 |
| sess_00876_839552 | scn_00003_364d7e | real_provider_observed | 19 | 1 | 1 |


Historical failure classification is also recorded per source in source_index.json (failure_records_observed); changed/unavailable sources remain unknown. A failure in a historical capture does not imply the current branch/service is still failing.

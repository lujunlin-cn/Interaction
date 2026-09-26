# Context Analysis

Director `_scenario_brief` includes complete published player/NPC dictionaries with asset metadata as well as last four outcome texts and full presented narratives. Repeated asset URLs/version data are irrelevant to action planning. Inventory/relationships/location must be retained. Narrative has a restricted ScenePacket but its output_contract additionally receives full scenario_brief (including hidden truth); currently OpenAI text transport ignores output_contract, so this is a future transport leak risk, not demonstrated current disclosure.

Jev has the opposite defect: raw location ID and insufficient dramatic context. Context projection will be role-specific and lossless for state/rules, strips only presentation/asset metadata for Director, gives Narrative only authorized facts plus canonical possessions/location, and gives Jev a bounded readable situation. Character knowledge/secrets are not indiscriminately made public. Character presence constraints, rules, anchor events and negative intent must survive projection.

Context character counts are exactly measurable; tokens need an actual tokenizer/provider usage and cannot be inferred as chars/4. Live latency benefit remains unmeasured until text-only paired replay. No claim of fewer HTTP calls is justified merely by shorter prompts.

## Post-implementation evaluation

119 Director context blocks: 678125→635864 Unicode characters, -6.232%; required-field loss 0. This excludes new semantic packet overhead and is not a tokenizer estimate. Narrative now receives known_state and authorized_changes; two fixed-outcome text follow-ups show this does not eliminate phantom equipment or resolve old state/prose contradictions. No measured full-request token or Ready latency reduction.

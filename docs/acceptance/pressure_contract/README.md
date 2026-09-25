# Creator pressure contract regression

Date: 2026-09-25. **External paid media requests: 0** for this isolated regression.

The real Creator run exposed two bugs: Step 5 put the consequence in the pressure
driver column, and a later instruction returned a JSON array encoded as a string.
Both passed the former string-only validation. Standard editing then reused the
invalid third column. The original live evidence remains under
`../biohazard_full_e2e/creator_review/` (`drama_proposal.json`,
`pressure_instruction_result.json`, and their screenshots).

The shared backend pressure normalizer accepts the existing
`名称｜来源｜行动触发/故事时间推进` contract and repairs explicit equivalent English
driver names, identifiable object/array forms, and JSON strings. Reordered columns
retain their source and consequence wording. Missing, contradictory, negated, or
unsupported drivers are rejected; no trigger is inferred from vague urgency or
real elapsed time, and unknown object fields are never silently discarded.

Initial authoring, proposals and their suggestions, confirmation, natural-language
instructions, manual save, and publication use the same contract. Natural-language
instructions get at most one format repair request and do not partially apply a
failed batch. Historical drafts remain readable; only lossless repairs are applied
to read responses, and ambiguous drafts fail Publish Gate. Existing immutable
published versions are unchanged.

Standard editing no longer carries an invalid old tail or defaults an unknown
driver to actions. It preserves input and asks for the trigger when needed. Legacy
recognizable JSON is displayed as natural text, not raw schema.

Verification:

- `backend/tests/test_pressure_contract.py`: isolated memory services and ASGI
  route checks, no database or provider calls. Covers initial draft, projection,
  confirmation, instructions, saves, legacy reads, and Publish Gate.
- `frontend/tests/pressure_editing.mjs`: five real React browser cases on isolated
  Vite port 9002 with every API mocked and external origins blocked. 1920×1080,
  Standard Mode. Results in `browser.json`, with five screenshots.
- `npx tsc --noEmit`: passed.

These are regression checks, not real Provider or FULL E2E acceptance. The live
story must be reviewed and saved through Standard Creator after deployment.

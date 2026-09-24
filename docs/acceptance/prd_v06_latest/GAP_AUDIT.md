# Latest PRD UX — implementation audit before changes

Baseline: `881dd66cb8585b51c0a3c8ff5c47160a000c737c` (2026-09-25).
The initial pull found a local PRD identical byte-for-byte to origin/main; synchronized without changing its content. This is an implementation audit, not a runtime PASS report.

| Decision | Initial status | Evidence / actual gap |
|---|---|---|
| Q105 | MISSING | Creator overview generates then navigates straight to raw drama fields. No persisted current-understanding projection. |
| Q106 | MISSING | Drama tab is DRAMA_FIELDS textarea loop. No deepen/confirm workflow. |
| Q107 | MISSING | Authoring has draft/patch only, no contextual question proposals or user confirmation. |
| Q108 | BROKEN | Standard exposes fact keys, pressure driver and timed DSL. |
| Q109 | PARTIAL | Library and Creator share backend references but different UI field grouping. |
| Q110 | PARTIAL | Global create allows name without bio; optional scenario fields render as empty required-looking forms. |
| Q111 | BROKEN | Draft edits stay local, but publish creates latest global snapshot, ignoring pinned version and story overlay. Continue old version button actually updates version. |
| Q112 | MISSING | No character understanding proposal UI; ai-describe endpoint not connected. |
| Q113 | BROKEN | Standard mechanics renders checkbox plus raw JSON textarea. |
| Q114 | MISSING | No natural-language MechanicSpec proposal/validation; typed patch dict traversal fails mechanics paths. |
| Q115 | MISSING | No tutorial cards or adjustment workflow; configs not validated against skill permissions. |
| Q116 | MISSING | No PlayerShell fullscreen request. |
| Q117 | PARTIAL | Video/decisions/input exist; HUD occupies main toolbar. |
| Q118 | PARTIAL | Backend Ready/Lead gate exists; UI displays empty/pending recommendation noise. |
| Q119 | BROKEN | Free input hidden during TIMED, duplicate demand not guarded for entire generation. |
| Q120 | MISSING | Toolbar instead of hover/pin drawer; Standard shows precise relationship numbers. |
| Q121 | BROKEN | Inspector available in Standard; raw last_failed_action.error and toast exception shown. |
| Q122 | BROKEN | Scene title never fades; no browser Loading/Failed lifecycle; director prompt requests target_changes strings while schema expects dicts. |

FR-103/104: MISSING/BROKEN; FR-105/106: PARTIAL; FR-107: BROKEN;
FR-108/109/110: MISSING; FR-111: PARTIAL; FR-112: MISSING; FR-113/114: BROKEN.

Implementation boundaries: preserve state managers, scheduling, provider routing, reference resolver, video jobs and two-phase commits. Add validated authoring projections and presentation adapters, with targeted fixes for the broken paths above. Acceptance requires fresh API/browser evidence; source inspection alone never upgrades a status to PASS.

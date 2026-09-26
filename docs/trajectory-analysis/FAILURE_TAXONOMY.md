# Trajectory Failure Taxonomy

Counts are affected branch IDs, not independent users. Historical failures may already be fixed; hypotheses are not labeled confirmed defects.

| Class | Count | Examples |
| --- | --- | --- |
| director_schema | 3 | br_00016_fac3e6, br_00018_b9d23e, br_00020_bee161 |
| proposal_contract | 4 | br_00012_e5b104, br_00010_cb8111, br_00078_6edd5b, br_00404_de6f98 |
| jev_observation_not_in_director_prompt | 16 | br_00012_e5b104, br_00135_4d42ef, br_00078_d75c60, br_00010_cb8111, br_00010_262ca1, br_00010_a0a79c |
| evidence_without_clue_review_required | 4 | br_00135_4d42ef, br_00010_262ca1, br_00010_a0a79c, br_00156_bbf9cb |
| action_without_state_change_review_required | 6 | br_00078_d75c60, br_00010_262ca1, br_00049_f32ffd, br_00136_383b8e, br_00008_c24bb7, br_00078_c42ec2 |
| inventory_used_as_add | 2 | br_00010_cdc5e0, br_00335_aa08da |
| remove_unowned_item | 2 | br_00078_6edd5b, br_00404_de6f98 |
| character_reference | 2 | br_00051_df5199, opening_00078_51f227 |
| provider_billing | 5 | br_00333_7f9a00, br_00335_2a3d99, br_00337_18670d, br_00008_c24bb7, opening_00033_23675f |
| truth_guard_false_positive_historical | 3 | opening_00030_290f74, opening_00114_d85bd0, opening_00139_2e2c57 |


P0: contradictory inventory operations / invented possession; state and published identity must remain controlled. P1: evidence without gameplay updates, Jev context starvation, invisible skill execution, continuity/agency mismatch. P2: transport/schema recovery and character refs already addressed in earlier commits. Trace loss is a confirmed current infrastructure defect: DB spans=0, while 467 spans survive in evidence; `Tracer.emit` never called `persist`.

## Root causes, severity and disposition after implementation

| Family | Severity / evidence strength | Root cause | Implemented response / remaining gap |
|---|---|---|---|
| Intent routing loss | P1, code-confirmed; 16 FREE records use this route | Jev observation / confirmed strategy not included in actual Director messages | Versioned semantic packet now reaches planning; original input retained. Semantic compliance is still evaluated separately. |
| Unsafe mechanic proposal | P0, 2 concrete USED/add cases | Inventory adapter accepted contradictory stage/action; no joint validation | Reject and request one bounded Director repair. Cannot prevent unsupported prose with no proposal. |
| Conflicting / duplicate effects | P1, 4 recorded contract failures | Director generic operations and skill proposals overlap | Exact dedup + typed clue-envelope reconciliation; StateManager remains final gate. |
| Missed clue/progress | P1, 4 evidence/no-clue and 6 no-state-change review candidates | Text/evidence/typed effects have no semantic equivalence check | Not claimed solved; next study needs labeled evidence and progress contracts. |
| Recommendation starvation | P1, 4/11 OTHER > .5 | Jev lacks readable current scene, known state, relationships and pressures | Project context and retain OTHER. High OTHER alone does not prove recommendation failure. |
| Repeated scene / recovery | P1, user issue 7 and executable replay | Terminal branch can enter commit again; repeated regeneration creates duplicate tasks | Idempotent terminal guard; current receipt retry is safe, stale historical selection rejected. 31 recorded checkpoints tested. |
| Context pollution / missing context | P1, measured projection and 2 text counterexamples | Director carries media metadata; Narrative lacks possessions/location | Director projection + authorized ScenePacket state. Existing canonical/prose disagreement still needs adjudication. |
| Trace loss | P1, baseline DB=0 vs 467 recovered spans | Emit had no durable consumer; wrong Skill query prefix | Batched idempotent writer + corrected lookup + Observatory. No claim that lost historical spans were recovered fully. |
| Schema / provider recovery | P2, 3 schema / 5 billing branches | Provider output contract or account failures | Existing paths retained; model/context limits recorded separately from gameplay failures. |
| Reference / truth false positives | P1 historical, 2 refs / 3 truth-guard cases | Cast/reference contract; public names mistaken for secrets | Earlier fixes retained; no new visual validation this round. |

Counts overlap and cannot be added into a failure rate. P0 here describes consequence severity; it is not a claim of a new exploitable production incident. All current semantic contradictions and the two old-preferred FREE cases remain in the evaluation report.

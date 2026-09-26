"""Offline metrics only: proxies and incomplete observations are explicitly tagged."""
import json,statistics
from pathlib import Path
from collections import Counter
from itertools import combinations
from trajectory_schema import TrajectoryTurn
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/trajectory-analysis'
d=json.loads((OUT/'dataset.json').read_text())
for row in d['turns']:TrajectoryTurn.model_validate(row)
(OUT/'TRAJECTORY_TURN.schema.json').write_text(json.dumps(TrajectoryTurn.model_json_schema(),ensure_ascii=False,indent=2)+'\n')
(OUT/'schema_validation.json').write_text(json.dumps({'validated_records':len(d['turns']),'failures':0,'schema':'1.0.0','scope':'Typed envelope; raw historical nested payloads remain verbatim; runtime schemas remain authoritative.'},indent=2)+'\n')
real=[t for t in d['turns'] if t['provenance']=='real_provider_observed']
per_turn=[]
for t in real:
 spans=[s for s in d['spans'] if s.get('branch_id')==t['turn_id']]
 calls=[s for s in spans if s.get('name')=='provider.text']
 skills=t['skills']['triggered'];jobs=t['production']['jobs'];shots=t['production']['shots']
 per_turn.append({'turn_id':t['turn_id'],'session_id':t['session_id'],'kind':t['record_kind'],
 'provider_text_calls_observed':len(calls) if calls else None,
 'provider_roles_observed':dict(Counter(s.get('input',{}).get('role','unknown') for s in calls)),
 'routes_lower_bound':t['metrics']['route_count_lower_bound'],
 'skill_trigger_count':len(skills),'skill_span_count':len(t['skills']['spans']),
 'proposed_operations':len((t['state']['proposed_patch'] or {}).get('operations',[])),
 'canonical_commit_observed':bool(t['state']['canonical_event']),
 'job_records':len(jobs),'shot_records':len(shots),'branch_retry_counter':t['production']['retry'],
 'created_to_ready_ms':t['metrics']['created_to_ready_ms'],
 'created_to_canonical_ms':t['metrics']['created_to_canonical_ms'],
 'incomplete':True})
def observed(values):
 vals=[v for v in values if isinstance(v,(float,int)) and v>0]
 return {'n':len(vals),'median':statistics.median(vals) if vals else None,'min':min(vals) if vals else None,'max':max(vals) if vals else None}

def norm(s):return ''.join(c for c in s.casefold() if c.isalnum())
def bigrams(s):
 s=norm(s);return {s[n:n+2] for n in range(len(s)-1)}
def similar(labels):
 pairs=[]
 for a,b in combinations(labels,2):
  x,y=bigrams(a),bigrams(b);pairs.append({'a':a,'b':b,'character_bigram_jaccard':len(x&y)/len(x|y) if x|y else 0})
 return sorted(pairs,key=lambda p:p['character_bigram_jaccard'],reverse=True)
ranks=[]
for s in d['spans']:
 if s.get('name')!='decision.rank' or s.get('provider')!='jev':continue
 labels=s.get('input',{}).get('candidates',[])
 ranks.append({'span_id':s['id'],'session_id':s.get('session_id'),'candidate_count':len(labels),
 'top_lexical_pairs':similar(labels)[:3],'semantic_similarity':None,
 'scores':s.get('output',{}).get('ranked',{}),'note':'Lexical proxy only, not semantic diversity or precision.'})
summary={'real_branch_records':len(real),'acted_turns':sum(t['record_kind']=='player_turn' for t in real),
 'observed_ready_elapsed_ms':observed(t['created_to_ready_ms'] for t in per_turn),
 'observed_canonical_elapsed_ms':observed(t['created_to_canonical_ms'] for t in per_turn),
 'free_share_among_acted_records':sum(t['player']['free_input'] for t in real if t['record_kind']=='player_turn')/sum(t['record_kind']=='player_turn' for t in real),
 'free_canonical_count':sum(t['player']['free_input'] and t['branch']['status']=='CANONICAL' for t in real),
 'free_total':sum(t['player']['free_input'] for t in real),
 'latency_change_after':None,'llm_calls_change_after':None,'production_waste_seconds':None,
 'limitations':['Some branch routes are real inside mixed sessions; real does not mean human-operated.',
 'created-to-Ready includes media and waiting; no reliable Jev-to-visible timestamps.',
 'Failure recovery and user elapsed time are not separated from canonical latency.',
 'No ground-truth trigger labels; precision/recall cannot be computed.',
 'No complete HTTP-attempt-to-branch join; media waste ratio cannot be reliably computed.']}
(OUT/'gameplay_profile.json').write_text(json.dumps({'summary':summary,'turns':per_turn,'topk_lexical_screen':ranks},ensure_ascii=False,indent=2)+'\n')
text=['# Reconstructed FREE Turn Timelines','', 'Only recorded links are shown. Unknown trigger justification stays unknown. No synthetic canonical-after states.','']
for t in real:
 if not t['player']['free_input']:continue
 text += ['## '+t['turn_id'],f"Session: {t['session_id']}; final recorded status: {t['branch']['status']}",
 '','Player: '+t['player']['raw_input'],'', '| Timestamp (epoch ms) | Event / span | Status |','| --- | --- | --- |']
 for e in t['timeline']:
  text.append('| '+str(e.get('at'))+' | '+str(e.get('name') or e.get('type'))+' | '+str(e.get('status',''))+' |')
 text += ['', 'Recorded mechanic triggers: '+json.dumps(t['skills']['triggered'],ensure_ascii=False),
 '','Why triggered: '+('explicit Director proposal; historical model reasoning not persisted' if t['skills']['triggered'] else 'no trigger recorded; absence is not proof of no opportunity'),
 '','Canonical commit: '+('recorded branch_canonical event' if t['state']['canonical_event'] else 'not observed in recovered turn events'),'']
(OUT/'TURN_TIMELINES.md').write_text('\n'.join(text)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))

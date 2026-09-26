"""Aggregate measured outcomes without converting proxies into gameplay claims."""
import json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'docs/trajectory-analysis'
read=lambda p:json.loads(p.read_text())
off=read(P/'replay_results.json');rec=read(P/'recovery_replay.json');critics=[];reviews={}
for folder in [P/'pairwise',P/'pairwise_choices']:
 if not folder.exists():continue
 mapping={x['case_id']:x for x in read(folder/'blind_mapping.json')}
 for f in folder.rglob('*.json'):
  try:d=read(f)
  except ValueError:continue
  if isinstance(d,dict) and d.get('provider')=='step_5' and 'request_sha256' in d:
   critics.append({'file':str(f.relative_to(ROOT)),'successful':'result' in d,'model':d.get('model',d.get('configured_model')),
      'request_id':d.get('request_id'),'latency_ms':d.get('latency_ms'),'usage':d.get('usage'),'error':d.get('error')})
  if f.parent!=folder:continue
  for c in (d.get('result') or {}).get('cases',[]) if isinstance(d,dict) else []:
   m=mapping[c['case_id']];kind='choice' if '/choice_replay/' in m['source'] else 'free'
   if kind=='choice' and folder.name!='pairwise_choices':continue # unequal 5 vs 3 initial review excluded
   new=m['new_version'];old='B' if new=='A' else 'A';winner=c.get('winner')
   outcome='improved' if winner==new else 'regressed' if winner==old else 'neutral' if winner=='tie' else 'insufficient'
   reviews[c['case_id']]={'case_id':c['case_id'],'source':m['source'],'kind':kind,'outcome':outcome,
      'new_version':new,'old_fidelity':c.get('fidelity_'+old),'new_fidelity':c.get('fidelity_'+new),
      'old_diversity':c.get('choice_diversity_'+old),'new_diversity':c.get('choice_diversity_'+new),
      'evidence':c.get('evidence'),'limitations':c.get('limitations'),
      'review_file':str(f.relative_to(ROOT))}
text_calls=[]
for folder in ['text_replay','choice_replay','narrative_context_replay']:
 for f in (P/folder).glob('*.json'):
  d=read(f)
  for c in d.get('calls',[]):text_calls.append({**c,'source':str(f.relative_to(ROOT))})
failed=[]
for f in (P/'text_replay/infrastructure_failure').rglob('*.json'):
 try:d=read(f)
 except ValueError:continue
 if isinstance(d,dict):failed += [{**c,'source':str(f.relative_to(ROOT))} for c in d.get('calls',[]) if c.get('status')=='failed']
metrics={'dataset':read(P/'mining_summary.json'),
 'offline_policy':{'records_with_proposals':off['summary']['policy_outcomes_available'],
  'improved':sum(r['outcome']=='improved' for r in off['results']),
  'neutral':sum(r['outcome']=='neutral' and 'old_validation' in r for r in off['results']),
  'regressed':sum(r['outcome']=='regressed' for r in off['results']),
  'needs_review':sum(r['outcome']=='needs_review' for r in off['results']),
  'context_only_no_policy_score':sum('old_validation' not in r for r in off['results'])},
 'context':{'records':len(off['results']),'old_chars':off['summary']['old_context_chars'],'new_chars':off['summary']['new_context_chars'],
  'reduction_percent':100*(1-off['summary']['new_context_chars']/off['summary']['old_context_chars']),
  'lost_required_fields':off['summary']['lost_required_context'],'unit':'Unicode characters in Director context block, NOT tokens or full request size'},
 'recovery':rec['summary'],'pairwise':{},'critic_requests':critics,
 'text_calls':text_calls,'prior_harness_failed_calls':failed,
 'no_new_paid_media_requests':0,'ready_latency_improvement':None,'llm_calls_per_turn_improvement':None,
 'token_reduction':None,'trigger_precision':None,'trigger_recall':None,'reviews':list(reviews.values()),
 'limits':['Single blinded Step5 judge; temporal stored-vs-new comparison with reconstructed partial context, not causal randomized A/B.',
 'Initial unequal-size choice evaluations excluded; pairwise_choices compares equal Jev Top-K counts.',
 'No independent ground-truth mechanic labels; deterministic proposal safety is not semantic truth.',
 'Narrative context refinement is reported separately; it did not fix all phantom props or location conflicts.',
 'No new image or video generation; visual_focus correctness and film quality require later human/media validation.']}
for kind in ['free','choice']:
 rows=[r for r in reviews.values() if r['kind']==kind]
 metrics['pairwise'][kind]={'reviewed':len(rows),'outcomes':dict(collections.Counter(r['outcome'] for r in rows)),
  'old_fidelity':dict(collections.Counter(r['old_fidelity'] for r in rows)),
  'new_fidelity':dict(collections.Counter(r['new_fidelity'] for r in rows))}
metrics['usage_summary']={'successful_text_and_decision_calls':len(text_calls),
 'successful_calls_by_role':dict(collections.Counter(c['role'] for c in text_calls)),
 'step5_attempts':len(critics),'step5_successful_responses':sum(c['successful'] for c in critics),
 'prior_text_harness_failures_recorded':len(failed),'image_generation_requests':0,'image_edit_requests':0,'h3_jobs':0}
(P/'evaluation_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+chr(10))
print(json.dumps({k:metrics[k] for k in ['offline_policy','context','recovery','pairwise','usage_summary']},ensure_ascii=False,indent=2))

"""Injected retry at recorded canonical checkpoints; stop before persistence."""
import asyncio,json,sys
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
from replay_trajectories import baseline_engine,source_hashes
from app.runtime.engine import RuntimeEngine
from app.runtime.session_state import SessionState
OUT=ROOT/'docs/trajectory-analysis'
class StopBeforePersistence(Exception):pass
async def main():
 hashes=source_hashes();d=json.loads((OUT/'dataset.json').read_text())
 raw={r['session_id']:r['state'] for r in json.loads((OUT/'replay_sessions.json').read_text())};results=[]
 for t in d['turns']:
  if t['provenance']!='real_provider_observed' or t['branch']['status']!='CANONICAL':continue
  original=next(b for b in raw[t['session_id']]['branches'] if b['id']==t['turn_id'])
  if not original.get('commit_event'):continue
  old=baseline_engine();new=RuntimeEngine(None);record={'turn_id':t['turn_id'],'session_id':t['session_id']}
  for name,engine in [('old',old),('new',new)]:
   state=SessionState.model_validate(deepcopy(raw[t['session_id']]));b=state.branch(t['turn_id']);before=state.model_dump(mode='json');calls=[]
   async def stop(*a,**kw):calls.append('persist_attempt');raise StopBeforePersistence()
   engine._persist=stop
   try:await engine._commit_selected(state,b)
   except StopBeforePersistence:pass
   record[name]={'persist_attempts':len(calls),'status':b.status.value,'state_unchanged':state.model_dump(mode='json')==before}
  record['outcome']='improved' if record['old']['persist_attempts'] and not record['new']['persist_attempts'] and record['new']['state_unchanged'] else 'needs_review'
  results.append(record)
 summary={'recorded_canonical_checkpoints':len(results),'improved':sum(r['outcome']=='improved' for r in results),
   'regressed':sum(not r['new']['state_unchanged'] for r in results),'new_paid_media_requests':0,
   'scope':'Counterfactual duplicate commit injected into historical in-memory states, not a frequency estimate of real double-clicks.',
   'no_db_write':True,'sources_unchanged':source_hashes()==hashes}
 (OUT/'recovery_replay.json').write_text(json.dumps({'summary':summary,'results':results},ensure_ascii=False,indent=2)+chr(10));print(json.dumps(summary,indent=2))
if __name__=='__main__':asyncio.run(main())

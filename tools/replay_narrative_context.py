"""Bounded text-only verification of ScenePacket context repair, fixed outcomes."""
import asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'tools'))
from replay_trajectories import TextOnlyRouter,frozen_state,source_hashes
from app.runtime.engine import RuntimeEngine
from app.domain.schemas import Branch,BranchSource,OutcomeSpec,StatePatchProposal,PatchOperation
OUT=ROOT/'docs/trajectory-analysis'
async def main():
 d=json.loads((OUT/'dataset.json').read_text());rows={x['session_id']:x['state'] for x in json.loads((OUT/'replay_sessions.json').read_text())}
 folder=OUT/'narrative_context_replay';folder.mkdir(exist_ok=True);hashes=source_hashes()
 for bid in ['br_00010_262ca1','br_00012_e5b104']:
  path=folder/(bid+'.json')
  if path.exists():continue
  recorded=json.loads((OUT/'text_replay'/(bid+'.json')).read_text());turn=next(t for t in d['turns'] if t['turn_id']==bid)
  router=TextOnlyRouter();engine=RuntimeEngine(router);state,oldbranch=frozen_state(turn,rows,engine)
  outcome=OutcomeSpec.model_validate(recorded['new']['outcome'])
  b=Branch(id=bid,session_id=state.id,arc_id=oldbranch['arc_id'],source=BranchSource.FREE,
    intent=oldbranch['intent'],base_versions=oldbranch['base_versions'],label=recorded['raw_input'],
    summary=outcome.title,outcome=outcome,
    state_patch_proposal=StatePatchProposal(proposal_id='replay',base_version=state.world.version,
      operations=[PatchOperation.model_validate(op) for op in outcome.ops]))
  b.packet=engine._build_scene_packet(state,b);before=state.model_dump(mode='json')
  result={'turn_id':bid,'raw_input':recorded['raw_input'],'visible_before':recorded['visible_before'],
    'old':recorded['new'],'controlled_variable':'Narrative gets known_state and authorized_changes; identical Director outcome',
    'new_scene_packet':b.packet.model_dump(exclude={'forbidden_revelations'}),'paid_media_requests':0}
  try:
   await engine._narrate_branch(state,b)
   result['new']={'outcome':outcome.model_dump(),'narrative':b.narrative,'visual_focus':b.causal_presentation}
  except Exception as e:result['error']=type(e).__name__+': '+str(e)[:500]
  result['calls']=router.calls;result['state_unchanged']=before==state.model_dump(mode='json')
  path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10))
  print(bid,'recorded',len(router.calls),'narrative calls',flush=True)
 assert source_hashes()==hashes
if __name__=='__main__':asyncio.run(main())

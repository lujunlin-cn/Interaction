"""Restore the recorded real H3 cache into an isolated verification Session.
For HTTP-media fault injection and deterministic Lead/Ready replay only. Does not
claim a new model invocation. Never modifies the original Session. DATABASE_URL
must point to the acceptance DB, not production. Run with PYTHONPATH=backend.
"""
import asyncio,json,pathlib,time
from app.runtime.engine import RuntimeEngine
from app.runtime.session_state import SessionState,PlayerState
from app.domain.schemas import BranchStatus,RecommendationEpoch,now_ms,PhaseHint
OUT=pathlib.Path('docs/acceptance/prd_v06_latest')
async def main():
    raw=json.loads((OUT/'live_play_state.json').read_text());origin=raw['id']
    s=SessionState.model_validate(raw);s.id='acceptance_media_replay'
    recs=[b for b in s.branches if b.source.value=='recommendation'][:3]
    opening=next(b for b in s.branches if b.source.value=='opening')
    assert len(recs)==3 and all(b.artifact and b.artifact.media_type=='video' for b in recs)
    reads=recs[0].read_set
    for k,v in reads['world'].items():setattr(s.world,k,v)
    s.world.version=recs[0].base_versions.world;s.drama.revision=recs[0].base_versions.drama
    s.drama.phase=PhaseHint(reads['drama']['phase']);s.drama.plan_version=reads['drama']['plan_version']
    s.wish_seq=reads['wish']['seq'];s.ended=False;s.pending_freeform_id=None;s.text_mode=False
    s.branches=[opening,*recs];s.events=[e for e in s.events if e.at<=max(b.ready_at for b in recs)]
    s.turns=[t for t in s.turns if t.get('opening')];s.committed_keys=[]
    s.arcs=s.arcs[:1];s.arcs[0].status='ACTIVE';s.arcs[0].closed_at=None;s.arcs[0].ending_family=None
    s.timed.active=False;s.timed.deadline_ms=None
    for b in s.branches:b.session_id=s.id
    for b in recs:b.status=BranchStatus.READY;b.expires_at=now_ms()+3600000
    s.epoch=RecommendationEpoch(id=recs[0].epoch_id,k=3,target_k=3,branch_ids=[b.id for b in recs],ready_ids=[b.id for b in recs],published=True,status='READY')
    s.player=PlayerState(status='PLAYING',scene_title=opening.outcome.title,scene_text=opening.narrative,caption=opening.caption,
        video_url='/media/'+opening.artifact.assembled_path,branch_id=opening.id,duration=opening.artifact.duration,
        lead=opening.artifact.duration-2,decision_open_at=opening.artifact.duration-2,position_base=1,playing=False)
    s.budget.total=s.budget.used  # No new paid speculation during transport checks.
    engine=RuntimeEngine(None)
    assert engine.compute_fingerprint(s)==recs[0].fingerprint,'Replay must preserve recorded facts and refs'
    await engine._persist(s)
    (OUT/'media_replay_origin.json').write_text(json.dumps({'fixture_session':s.id,'origin_session':origin,'purpose':'real artifact replay plus HTTP transport fault injection; not new Provider generation','branch_ids':[b.id for b in recs],'initial_position':1,'decision_open_at':s.player.decision_open_at,'fingerprint':recs[0].fingerprint,'expiry_extended_for_paused_inspection':True},ensure_ascii=False,indent=2))
    print(s.id)
asyncio.run(main())

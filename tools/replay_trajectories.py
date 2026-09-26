"""Historical policy replay and opt-in TEXT ONLY counterfactuals.

Default is offline: no DB imports at execution seams, no HTTP, no media.
--text-replay permits only Director/Narrative chat completions, in memory.
Frozen sources are hashed before/after; no session is written or API Player invoked.
"""
from __future__ import annotations
import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
OUT=ROOT/'docs/trajectory-analysis'
BASELINE='c22d14bceea3930e2dd2c25eaaf449bc85fbbd0a'

def source_hashes():
    return {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest()
            for name in ('dataset.json','replay_sessions.json')}


def baseline_engine():
    source=subprocess.check_output(['git','show',BASELINE+':backend/app/runtime/engine.py'],cwd=ROOT,text=True)
    module=types.ModuleType('app.runtime._recorded_baseline')
    module.__package__='app.runtime'
    exec(compile(source,'baseline_engine.py','exec'),module.__dict__)
    return module.RuntimeEngine(None)


def frozen_state(record, rows, engine):
    from app.runtime.session_state import SessionState
    from app.domain.schemas import WorldState, DramaState, NarrativeMemory, PlayerPreferenceState
    sid=record['session_id'];b=next(b for b in rows[sid]['branches'] if b['id']==record['turn_id'])
    raw=deepcopy(rows[sid]);cut=b['created_at']
    read=deepcopy(b.get('read_set') or {})
    raw['world']={**read.get('world',{}),'version':b['base_versions']['world']}
    raw['world']['knowledge']=[]
    events=[e for e in raw.get('events',[]) if e.get('at',0)<=cut]
    committed={e.get('branch_id') for e in events if e['type']=='branch_canonical'}
    received={e.get('branch_id') for e in events if e['type']=='receipt_committed'}
    previous=[deepcopy(x) for x in raw['branches'] if x['id'] in committed and x['id']!=b['id']]
    for x in previous:
        x['status']='CANONICAL'
        if x['id'] in received:
            for ev in (x.get('outcome') or {}).get('evidence',[]):
                if ev not in raw['world']['knowledge']:raw['world']['knowledge'].append(ev)
    raw['branches']=previous;raw['events']=events
    raw['drama']={**read.get('drama',{}),'revision':b['base_versions']['drama']}
    raw['memory']=NarrativeMemory().model_dump();raw['preferences']=PlayerPreferenceState().model_dump()
    raw['wishes']=[w for w in raw.get('wishes',[]) if w.get('created_at',0)<=cut]
    raw['pressures']=[] # missing historical pressure snapshot, not today's pressure
    raw['epoch']=None;raw['committed_keys']=[];raw['ended']=False
    raw['arcs']=[{**a,'status':'ACTIVE','ending_family':None,'closed_at':None} for a in raw['arcs'] if a['id']==b['arc_id']]
    state=SessionState.model_validate(raw)
    return state,b


def offline():
    from app.skills.gameplay import arbitrate, mechanic_context, understand_action
    from app.skills.mechanic import invoke
    from app.runtime.engine import RuntimeEngine, state_manager
    from app.domain.schemas import StatePatchProposal, PatchOperation
    from app.domain.state_manager import ProposalRejected
    dataset=json.loads((OUT/'dataset.json').read_text());rows={r['session_id']:r['state'] for r in json.loads((OUT/'replay_sessions.json').read_text())}
    engine=RuntimeEngine(None);old=baseline_engine();results=[]
    for t in dataset['turns']:
        if t['provenance']!='real_provider_observed':continue
        state,b=frozen_state(t,rows,engine)
        oldctx=old._scenario_brief(state);newctx=engine._scenario_brief(state)
        original=(b.get('director_result') or {}).get('outcome')
        item={'turn_id':b['id'],'session_id':state.id,'record_kind':t['record_kind'],'raw_input':t['player']['raw_input'],
              'old_context_chars':len(json.dumps(oldctx,ensure_ascii=False)),'new_context_chars':len(json.dumps(newctx,ensure_ascii=False)),
              'lost_required_context':[k for k in ('inventory','clues','relationships','location','world_rules','world_constraints','authored_anchors','truth_model') if oldctx.get(k)!=newctx.get(k)],
              'outcome':'neutral','policy_replay_only':True,'media_requests':0}
        if original is not None:
            mechanics=state.scenario_snapshot.get('mechanics',{})
            context=mechanic_context(newctx,state.world.model_dump())
            old_ops=deepcopy(original.get('ops') or [])
            for tr in original.get('skill_triggers') or []:
                result=invoke(tr.get('skill',''),tr,oldctx,mechanics,b['id'],state.world.version,state.drama.revision)
                if result: old_ops.extend(result['proposal']['operations'])
            new=arbitrate(original,context,mechanics,b['id'],state.world.version,state.drama.revision)
            def validate(ops):
                try:
                    proposal=StatePatchProposal(proposal_id='replay',base_version=state.world.version,operations=[PatchOperation(**x) for x in ops])
                    w=state_manager.validate(state.world,proposal,[],locations=list(oldctx.get('locations',{})) or None)
                    return {'valid':True,'world':w.model_dump()}
                except (ProposalRejected,ValueError,TypeError) as error:return {'valid':False,'reason':str(error)}
            old_result=validate(old_ops)
            new_result={'valid':False,'reason':'; '.join(new.errors)} if new.errors else validate(new.operations)
            item.update(old_proposal=old_ops,new_proposal=new.operations,old_validation=old_result,new_validation=new_result,decisions=new.decisions)
            # Narrow safety labels; gameplay quality is evaluated independently by critic.
            unsafe_use=any(x.get('skill')=='inventory' and x.get('stage')=='USED' and x.get('action')=='add' for x in original.get('skill_triggers',[]))
            if unsafe_use and old_result['valid'] and not new_result['valid']:item['outcome']='improved';item['reason']='blocks observed acquisition while using an item'
            elif not old_result['valid'] and new_result['valid']:item['outcome']='improved';item['reason']='unambiguous duplicate envelope reconciled'
            elif old_result['valid'] and not new_result['valid']:item['outcome']='needs_review';item['reason']='new conservative rejection'
            elif old_result.get('world') != new_result.get('world') and old_result['valid'] and new_result['valid']:item['outcome']='needs_review';item['reason']='state delta changed'
        if b['source']=='free':
            observation=(t.get('jev',{}).get('calls') or [{}])[-1].get('output',{}).get('observation') or b.get('intent') or {}
            packet=understand_action(t['player']['raw_input'],observation)
            item['semantic_packet']=packet.model_dump()
            item['original_preserved']=packet.raw_input==t['player']['raw_input']
        results.append(item)
    summary={'baseline_sha':BASELINE,'historical_records':len(results),'outcomes':dict(Counter(r['outcome'] for r in results)),
        'policy_outcomes_available':sum('old_validation' in r for r in results),
        'old_context_chars':sum(r['old_context_chars'] for r in results),'new_context_chars':sum(r['new_context_chars'] for r in results),
        'lost_required_context':sum(bool(r['lost_required_context']) for r in results),'additional_llm_calls':0,'new_paid_media_requests':0,
        'limitations':['Recorded-output policy comparison is not new model inference.','Context bytes are not token counts.','Before state reconstructed from fingerprint and receipts; missing memory/pressure marked unknown.','No live Ready latency measured.']}
    (OUT/'replay_results.json').write_text(json.dumps({'summary':summary,'results':results},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return dataset,rows,results


class TextOnlyRouter:
    """No media adapters, no DB, and a strict role allowlist."""
    def __init__(self):self.calls=[]
    async def call_text(self,role,messages,output_contract=None,**kwargs):
        from app.config import settings
        from app.providers.real import OpenAICompatTextProvider
        from app.domain.schemas import ProviderRouteRecord
        if role not in ('director','narrative'):raise RuntimeError('replay refuses non-text role')
        if role=='director':
            provider=OpenAICompatTextProvider('nemotron_local',settings.local_llm_base_url,'',settings.local_llm_model)
        else:
            provider=OpenAICompatTextProvider('step_37',settings.step_base_url,settings.step_api_key,settings.step37_model)
        try:
            response=await provider.generate(messages,output_contract,budget=kwargs.get('budget'))
        except Exception as exc:
            response_body = getattr(getattr(exc, 'response', None), 'text', '')
            self.calls.append({'role':role, 'model':provider.model, 'status':'failed',
                               'error_type':type(exc).__name__, 'response_body':response_body[:1500]})
            raise
        self.calls.append({'role':role,'model':response.model,'request_id':response.request_id,'usage':response.usage,
                           'latency_ms':response.latency_ms,'input_chars':sum(len(m['content']) for m in messages)})
        return provider,ProviderRouteRecord(role=role,primary=provider.name,selected=provider.name,model=response.model,status="AVAILABLE"),response
    def __getattr__(self,name):raise RuntimeError('replay has no '+name)


async def text_replay(dataset,rows,limit):
    from app.runtime.engine import RuntimeEngine
    from app.domain.schemas import Branch, BranchSource, BranchStatus, OutcomeSpec
    from app.skills.gameplay import understand_action
    folder=OUT/'text_replay';folder.mkdir(exist_ok=True)
    # Fixed, preregistered historical cohort: 8 real FREE turns across two stories,
    # covering alternative strategy, investigation, rapport, resource conflict and ending.
    ids=['br_00012_e5b104','br_00078_d75c60','br_00010_262ca1','br_00010_a0a79c',
         'br_00335_aa08da','br_00078_6edd5b','br_00078_c42ec2','br_00010_040fd6'][:limit]
    for bid in ids:
        target=folder/(bid+'.json')
        if target.exists():print('reuse completed checkpoint',bid,flush=True);continue
        t=next(x for x in dataset['turns'] if x['turn_id']==bid)
        router=TextOnlyRouter();engine=RuntimeEngine(router);state,b=frozen_state(t,rows,engine)
        raw=t['player']['raw_input'];packet=understand_action(raw,b.get('intent') or {})
        branch=Branch(id=bid,session_id=state.id,arc_id=b['arc_id'],source=BranchSource.FREE,
            label=raw,intent=b['intent'],base_versions=b['base_versions'],action_semantics=packet.model_dump())
        state.branches.append(branch);engine.sessions[state.id]=state
        before=state.world.model_dump()
        result={'turn_id':bid,'raw_input':raw,'visible_before':engine._scenario_brief(state),
                'old':{'outcome':(b.get('director_result') or {}).get('outcome') or b.get('outcome'), 'narrative':b.get('narrative')},
                'provider_mode':'real_text_only','canonical_db_written':False,'paid_media_requests':0}
        try:
            output,rec=await engine._director_output([{'role':'user','content':
                f'raw_player_input: {packet.action}\naction_semantics: {packet.model_dump_json()}\nscenario_context: '+json.dumps(engine._scenario_brief(state),ensure_ascii=False)}],
                state.scenario_snapshot.get('mechanics',{}),state.id,bid)
            branch.director_result=output;branch.routes=[rec]
            await engine._plan_branch(state,branch)
            await engine._narrate_branch(state,branch)
            result['new']={'outcome':branch.outcome.model_dump(),'narrative':branch.narrative,'visual_focus':branch.causal_presentation.get('visual_focus'),'skill_decisions':branch.skill_decisions}
        except Exception as error:result['error']=type(error).__name__+': '+str(error)[:800]
        result['calls']=router.calls;result['canonical_state_unchanged']=state.world.model_dump()==before
        target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(bid,'PASS' if 'new' in result else result.get('error'),len(router.calls),'text calls',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--text-replay',action='store_true');parser.add_argument('--limit',type=int,default=8)
    args=parser.parse_args();before=source_hashes()
    try:
        dataset,rows,_=offline()
        if args.text_replay:asyncio.run(text_replay(dataset,rows,args.limit))
    finally:
        after=source_hashes()
        (OUT/'replay_isolation.json').write_text(json.dumps({'before':before,'after':after,
            'frozen_sources_unchanged':before==after,'media_adapter_instantiated':False,
            'player_api_called':False,'canonical_database_written':False,
            'scope':'Frozen sources and in-memory state; no live DB mutation attempted.'},indent=2)+'\n')
        assert before==after,'Replay altered frozen historical sources'

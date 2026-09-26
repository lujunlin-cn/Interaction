"""Generic regression cases derived from recorded turns; no media/network."""
import asyncio
import json
from types import SimpleNamespace
import pytest
from app.skills.gameplay import arbitrate, understand_action, director_context, choice_context, distinct_candidates
from app.runtime.engine import RuntimeEngine
from app.domain.schemas import Branch, BranchSource, BranchStatus

def test_inventory_use_never_creates_an_unowned_item():
    output={'skill_triggers':[{'skill':'inventory','target':'flare','action':'add','stage':'USED'}]}
    result=arbitrate(output,{'inventory':[]},{},'branch',1,1)
    assert result.errors and not result.operations
    assert 'inventory_use_cannot_acquire' in result.errors[0]

def test_duplicate_and_conflicting_proposals_have_explicit_dispositions():
    trig={'skill':'relationship','target':'partner','value':5}
    ctx={'npcs':[{'id':'partner'}],'relationships':{'partner':50}}
    result=arbitrate({'skill_triggers':[trig,trig]},ctx,{},'b',1,1)
    assert len(result.operations)==1
    assert result.decisions[1]['status']=='deduplicated'
    result=arbitrate({'skill_triggers':[trig,{**trig,'value':-5}]},ctx,{},'b',1,1)
    assert result.errors

def test_unknown_character_and_unowned_remove_do_not_default_to_first_npc():
    result=arbitrate({'skill_triggers':[{'skill':'relationship','value':3},{'skill':'inventory','target':'sample','action':'remove'}]},
        {'npcs':[{'id':'partner'}],'inventory':[]},{},'b',1,1)
    assert len(result.errors)==2 and not result.operations

def test_confirmed_semantics_override_observation_but_keep_original():
    packet=understand_action('攻击它',{'action':'与它交谈','strategy':'先退到门后','desire':'安全撤离','desire_source':'PLAYER_CONFIRMED'},'只压制，不追击')
    assert packet.raw_input=='攻击它' and packet.action=='只压制，不追击'
    assert packet.strategy=='先退到门后' and packet.quoted_constraints==['只压制，不追击']
    assert understand_action('先调查',{'action':'离开'}).action=='先调查'

def test_context_projection_keeps_semantics_removes_only_media_and_speculation():
    brief={'player':{'id':'p','knowledge':'saw the lock','assets':[{'url':'large'}]},'npcs':[],
        'inventory':['card'],'world_rules':'no teleportation','truth_model':'hidden cause','location':'hall',
        'locations':{'hall':'大厅'},'recent_canonical_beats':[{'title':'opened door','result':'open','presented_narrative':'same result'},{'title':'arrived','result':'arrived','presented_narrative':'new details'}]}
    projected=director_context(brief)
    assert projected['player']=={'id':'p','knowledge':'saw the lock'}
    assert projected['inventory']==['card'] and projected['world_rules']=='no teleportation'
    assert brief['player']['assets'] and 'presented_narrative' not in projected['recent_canonical_beats'][0]
    rank=choice_context(projected,{},[])
    assert rank['location_name']=='大厅' and 'truth_model' not in rank

def test_exact_choice_dedup_does_not_remove_meaningful_negation():
    c=[{'label':'检查门！'},{'label':'检查门'},{'label':'不检查门，离开'}]
    kept,removed=distinct_candidates(c)
    assert len(kept)==2 and len(removed)==1

@pytest.mark.asyncio
async def test_confirmed_intent_reaches_actual_director_prompt(monkeypatch):
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{})
    prompts=[]
    async def director(messages,*args):
        prompts.extend(messages)
        return {'outcome':{'title':'observe','text':'Observed','mode':'QUICK_ACK','ops':[]}},SimpleNamespace(selected='offline',model='offline')
    async def noop(*args,**kw): pass
    monkeypatch.setattr(engine,'_director_output',director)
    monkeypatch.setattr(engine,'_persist',noop);monkeypatch.setattr(engine,'_push',noop)
    await engine._plan_free_action(state,'原文',{'action':'确认后的行动','strategy':'不追击','desire_source':'PLAYER_CONFIRMED'},'确认后的行动')
    assert '确认后的行动' in json.dumps(prompts,ensure_ascii=False)
    assert '不追击' in json.dumps(prompts,ensure_ascii=False)

@pytest.mark.asyncio
async def test_canonical_commit_retry_is_idempotent_without_representing(monkeypatch):
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{})
    branch=Branch(id='b',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.FREE,
        status=BranchStatus.CANONICAL,commit_event='commit:b',base_versions=engine._branch_base_versions(state))
    state.branches.append(branch)
    before=state.model_dump(mode='json')
    async def forbidden(*a,**kw):raise AssertionError('terminal branch must not be committed again')
    monkeypatch.setattr(engine,'_persist',forbidden)
    await engine._commit_selected(state,branch)
    assert state.model_dump(mode='json')==before

@pytest.mark.asyncio
async def test_preview_prefills_without_executing_or_mutating_state(monkeypatch):
    class Router:
        async def call_decision(self, **kw):
            return None, SimpleNamespace(selected='offline'), SimpleNamespace(model='offline',details={'clarification_required':True,'confidence':.2,'impact':'HIGH'})
        async def call_text(self,*args,**kw):
            assert kw['output_contract']['purpose']=='intent_preview'
            return None,SimpleNamespace(selected='offline'),SimpleNamespace(model='offline',latency_ms=2,content=json.dumps({'action':'躲在门后观察','desire':'避免暴露','strategy':'先关灯，不主动攻击'}))
    engine=RuntimeEngine(Router());state=engine._bootstrap('v','s',{});engine.sessions[state.id]=state
    before=state.world.model_dump();called=[]
    async def noop(*a,**kw): pass
    async def forbidden(*a,**kw):called.append(1);raise AssertionError('preview cannot execute')
    monkeypatch.setattr(engine,'_persist',noop);monkeypatch.setattr(engine,'_push',noop)
    monkeypatch.setattr(engine,'_plan_free_action',forbidden)
    result=await engine.free_action(state.id,'躲在门后看看')
    assert result['status']=='CLARIFICATION_REQUIRED'
    assert state.pending_intent['desire']=='避免暴露'
    assert state.pending_intent['raw_text']=='躲在门后看看'
    assert not called and state.world.model_dump()==before
    await engine.confirm_intent(state.id,False)
    assert state.pending_intent is None and state.world.model_dump()==before

@pytest.mark.asyncio
async def test_double_pipeline_spawn_starts_only_one_coroutine():
    engine=RuntimeEngine(None);calls=[];gate=asyncio.Event()
    async def run(*a,**kw):calls.append(a);await gate.wait()
    engine._run_pipeline=run
    engine._spawn_pipeline('s','b');first=engine._pipeline_tasks['b']
    engine._spawn_pipeline('s','b');assert engine._pipeline_tasks['b'] is first
    await asyncio.sleep(0);assert len(calls)==1
    gate.set();await first

@pytest.mark.asyncio
async def test_double_regeneration_request_reuses_running_job(monkeypatch):
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{});engine.sessions[state.id]=state
    b=Branch(id='b',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.FREE,status=BranchStatus.CANONICAL,
             base_versions=engine._branch_base_versions(state),commit_event='commit:b')
    state.branches.append(b);state.player.branch_id='b'
    calls=[];gate=asyncio.Event()
    async def noop(*a,**kw):pass
    async def regenerate(*a,**kw):calls.append(a);await gate.wait()
    monkeypatch.setattr(engine,'_regenerate_presentation',regenerate)
    monkeypatch.setattr(engine,'_persist',noop);monkeypatch.setattr(engine,'_push',noop)
    await engine.player_command(state.id,'regenerate');await engine.player_command(state.id,'regenerate')
    await asyncio.sleep(0);assert len(calls)==1
    gate.set();await engine._pipeline_tasks['b']

def test_spent_canonical_choice_not_shown_again():
    from app.domain.schemas import RecommendationEpoch
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{})
    b=Branch(id='spent',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.RECOMMENDATION,
             status=BranchStatus.CANONICAL,base_versions=engine._branch_base_versions(state))
    state.branches.append(b)
    state.epoch=RecommendationEpoch(id='e',k=1,branch_ids=['spent'],ready_ids=['spent'],published=True,status='PUBLISHED')
    assert not engine.player_view(state)['recommendations']

def test_observatory_never_counts_uncommitted_proposal_as_applied():
    from app.runtime.skill_observatory import summarize
    spans=[{'id':'1','name':'skill.inventory','status':'success','branch_id':'unselected','at':1,'output':{'proposal':{'operations':[]}}},
           {'id':'2','name':'skill.inventory','status':'success','branch_id':'chosen','at':2,'duration_ms':10,'output':{'proposal':{'operations':[]}}},
           {'id':'3','name':'commit.canonical','status':'success','branch_id':'chosen','at':3}]
    result=summarize(spans+spans)
    metric=result['metrics'][0]
    assert metric['invocations']==2 and metric['proposal_count']==2
    assert metric['proposals_in_committed_branches']==1
    assert metric['trigger_recall'] is None and metric['average_latency_ms']==10

@pytest.mark.asyncio
async def test_trace_survives_new_tracer_instance(tmp_path,monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app import db
    from app.db_models import Base
    from app.runtime.tracer import Tracer
    engine=create_async_engine('sqlite+aiosqlite:///'+str(tmp_path/'trace.db'))
    async with engine.begin() as connection:await connection.run_sync(Base.metadata.create_all)
    sessions=async_sessionmaker(engine,expire_on_commit=False);monkeypatch.setattr(db,'SessionLocal',sessions)
    first=Tracer();span=await first.emit('skill.inventory','success',skill_id='inventory',skill_version='1.0.0',output={'proposal':{'operations':[]}})
    await first.flush();assert not first._pending
    # Simulate uncertain transaction outcome: retry the identical span.
    first._pending.append(span);await first.flush()
    second=Tracer()
    async with sessions() as connection:
        found=await second.spans_for_skill(connection,'inventory')
        assert [s.id for s in found]==[span.id]
    await engine.dispose()

@pytest.mark.asyncio
async def test_old_canonical_choice_cannot_be_reselected_after_progress():
    from app.runtime.engine import EngineError
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{});engine.sessions[state.id]=state
    old=Branch(id='old',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.RECOMMENDATION,
        status=BranchStatus.CANONICAL,commit_event='commit:old',base_versions=engine._branch_base_versions(state))
    state.branches.append(old);state.player.branch_id='current'
    before=state.model_dump(mode='json')
    with pytest.raises(EngineError,match='已失效'):
        await engine.select_branch(state.id,'old')
    assert state.model_dump(mode='json')==before

def test_scene_packet_projects_known_state_without_private_truth():
    from app.domain.schemas import OutcomeSpec,StatePatchProposal,PatchOperation
    engine=RuntimeEngine(None);state=engine._bootstrap('v','s',{})
    state.world.location='hall';state.world.inventory=['door_card'];state.world.truth={'hidden_cause':False}
    state.world.knowledge=['The terminal is fixed to the wall.']
    b=Branch(id='b',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.FREE,
        base_versions=engine._branch_base_versions(state),outcome=OutcomeSpec(title='Inspect',text='Read the terminal.'),
        state_patch_proposal=StatePatchProposal(proposal_id='p',base_version=state.world.version,
            operations=[PatchOperation(op='set',path='clues.timeline',value='DISCOVERED')]))
    packet=engine._build_scene_packet(state,b)
    assert packet.known_state['inventory']==['door_card']
    assert packet.known_state['location']=='hall'
    assert packet.authorized_changes[0]['path']=='clues.timeline'
    visible=packet.model_dump(exclude={'forbidden_revelations'})
    assert 'hidden_cause' not in json.dumps(visible)
    assert state.world.inventory==['door_card']

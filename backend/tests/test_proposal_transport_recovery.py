import asyncio
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.runtime.director_output import DirectorOperation
from app.domain.schemas import PatchOperation, StatePatchProposal, WorldState
from app.domain.state_manager import StateManager, ProposalRejected

def test_director_contract_rejects_aggregate_clue_replacement_before_media():
    with pytest.raises(ValidationError):
        DirectorOperation(op='set',path='clues',value=['record'])
    assert DirectorOperation(op='set',path='clues.record',value='DISCOVERED').path=='clues.record'

def test_planning_retry_drops_invalid_cached_director_output(monkeypatch):
    from app.runtime.engine import RuntimeEngine
    from app.domain.schemas import Branch,BranchStatus,BranchSource
    engine=RuntimeEngine(SimpleNamespace());state=engine._bootstrap('v','s',{})
    b=Branch(id='bad-plan',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.FREE,
        status=BranchStatus.FAILED,fail_stage='PLANNING',director_result={'invalid':'cached'},
        base_versions=engine._branch_base_versions(state))
    state.branches.append(b);state.player.status='FAILED_RECOVERABLE';engine.sessions[state.id]=state
    async def noop(*a):pass
    monkeypatch.setattr(engine,'_persist',noop);monkeypatch.setattr(engine,'_push',noop)
    monkeypatch.setattr(engine,'_spawn_pipeline',lambda *a:None)
    asyncio.run(engine.player_command(state.id,'retry'))
    assert b.director_result is None and b.status==BranchStatus.RETRYING

def test_rfc_object_assignment_and_redundant_clue_envelope_preserve_explicit_ops():
    world = WorldState(location='hall')
    proposal = StatePatchProposal(proposal_id='p', base_version=world.version, source='director',
        operations=[PatchOperation(op='add', path='/location', value='power'),
                    PatchOperation(op='add', path='/clues', value=['record']),
                    PatchOperation(op='set', path='clues.record', value='DISCOVERED')])
    after = StateManager().validate(world, proposal, [], locations=['hall','power'])
    assert after.location == 'power' and after.clues == {'record':'DISCOVERED'}
    assert world.location == 'hall' and world.clues == {}

@pytest.mark.parametrize('op', [
    PatchOperation(op='add',path='/truth/secret',value='revealed'),
    PatchOperation(op='add',path='/clues',value=['unproposed']),
    PatchOperation(op='set',path='/location',value='unknown'),
])
def test_transport_repair_never_invents_effects_or_bypasses_domains(op):
    w=WorldState(location='hall')
    p=StatePatchProposal(proposal_id='p',base_version=w.version,source='director',operations=[op])
    with pytest.raises(ProposalRejected):
        StateManager().validate(w,p,[],locations=['hall'])
    assert w.location == 'hall' and not w.clues

def test_commit_retry_reuses_media_without_replanning_or_generation(monkeypatch):
    from app.runtime.engine import RuntimeEngine
    from app.domain.schemas import Branch,BranchStatus,BranchSource,SceneArtifact
    engine=RuntimeEngine(SimpleNamespace())
    state=engine._bootstrap('v','s',{'world':{'locations':'hall｜大厅'}})
    b=Branch(id='b',session_id=state.id,arc_id=state.current_arc().id,source=BranchSource.FREE,
        status=BranchStatus.FAILED,fail_stage='COMMIT',base_versions=engine._branch_base_versions(state),
        fingerprint=engine.compute_fingerprint(state),artifact=SceneArtifact(id='a',branch_id='b',assembled_path='existing.mp4'))
    state.branches.append(b);state.pending_freeform_id=b.id;state.player.status='FAILED_RECOVERABLE';engine.sessions[state.id]=state
    calls=[]
    async def noop(*a): pass
    async def commit(s, branch): calls.append(('commit',branch.artifact.assembled_path))
    monkeypatch.setattr(engine,'_persist',noop);monkeypatch.setattr(engine,'_push',noop)
    monkeypatch.setattr(engine,'_commit_selected',commit)
    monkeypatch.setattr(engine,'_spawn_pipeline',lambda *a:calls.append(('pipeline',a)))
    asyncio.run(engine.player_command(state.id,'retry'))
    assert calls == [('commit','existing.mp4')]

"""AT77–90 offline contract tests. Not real-provider acceptance evidence."""
import json
import pytest
from app.domain.schemas import ScenarioDraft
from app.runtime.director_output import normalize_director_output
from app.runtime.scenario_service import ScenarioService

def test_director_shape_repair_preserves_facts():
    raw = {"outcome": {"title": "灯塔", "text": "门没有打开", "ops": [], "evidence": []}, "directive": {"target_changes": ["发现门被锁住"]}}
    out = normalize_director_output(json.dumps(raw))
    assert out["outcome"] == raw["outcome"]
    assert out["directive"]["target_changes"] == [{"description": "发现门被锁住"}]
    raw["directive"]["target_changes"] = 42
    with pytest.raises(ValueError): normalize_director_output(json.dumps(raw))

def test_mechanic_permission_and_lock_boundary():
    svc = ScenarioService(None)
    d = ScenarioDraft(id="bound", locks=["mechanics.relationship"])
    for path, after in [("mechanics.relationship", {"enabled": True, "config": {}}), ("mechanics.shell", {"enabled": True, "config": {"command": "true"}})]:
        assert not svc._apply_typed_patch(d, [{"path": path, "after": after}], "instruct")
    assert svc._apply_typed_patch(d, [{"path": "mechanics.inventory", "after": {"enabled": True, "config": {"capacity": 4}}}], "confirmed_ai")
    assert d.mechanics['inventory'].state_patch_contract == ['addItem', 'removeItem']
    assert not svc._apply_typed_patch(d, [{"path": "mechanics.inventory.config.capacity", "after": -1}], "instruct")
    assert d.mechanics['inventory'].config['capacity'] == 4

def test_projection_confirmation_and_stale_guard(client):
    d = client.post('/api/scenarios', json={"idea": "灯塔谜案"}).json()
    sid = d['id']; url = f'/api/scenarios/{sid}'
    response = client.post(url + '/understanding', json={'scope': 'drama'})
    assert response.status_code == 200, response.text
    p = response.json()
    assert any(len(i['suggestions']) >= 3 for i in p['items'] if i['question'])
    assert client.get(url).json()['drama'] == d['drama']
    r = client.post(url + '/understanding/confirm', json={'projection_id': p['id'], 'answers': {'drama.core_question': '谁在守护灯塔？'}})
    assert r.status_code == 200, r.text
    changed = r.json()
    assert changed['changes'][-1]['before'] == d['drama']['core_question']
    assert changed['changes'][-1]['source'] == 'confirmed_ai'
    changed['drama']['central_conflict'] = '人工新修改'
    client.put(url, json=changed)
    assert client.post(url + '/understanding/confirm', json={'projection_id': p['id'], 'answers': {'drama.central_conflict': '旧值'}}).status_code == 409

def test_mechanics_compiles_to_runtime(client):
    from app.skills.mechanic import invoke
    d = client.post('/api/scenarios', json={'idea': '失踪的灯塔看守'}).json()
    url = f"/api/scenarios/{d['id']}"
    r = client.post(url + '/understanding', json={'scope': 'mechanics', 'instruction': '主要调查和询问角色，角色记得我是否撒谎，追逐时要快速决定'})
    assert r.status_code == 200, r.text
    p = r.json()
    r = client.post(url + '/understanding/confirm', json={'projection_id': p['id'], 'answers': {i['path']: i['value'] for i in p['items']}})
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ['relationship', 'clue-system', 'qte']: assert d['mechanics'][key]['enabled']
    assert not d['mechanics']['inventory']['enabled']
    result = invoke('relationship', {'target': 'keeper', 'value': 8}, {}, d['mechanics'], 'br', 1, 1)
    assert result['proposal']['operations'][0]['path'] == 'relationships.keeper'
    assert client.post(url + '/publish', json={'reviewed': True}).status_code == 200

def test_pinned_overlay_and_explicit_promote(client):
    from app.runtime.character_service import CharacterAssetService
    from app.main import provider_router
    service = CharacterAssetService(provider_router)
    g = client.post('/api/characters', json={'name': '林岚', 'bio': '灯塔维修员'}).json()
    version = client.get(f"/api/characters/{g['id']}/versions").json()['items'][0]
    client.patch(f"/api/characters/{g['id']}", json={'bio': '全局新定义'})
    async def snapshot():
        return await service.snapshot_for_scenario('ver_overlay_contract', g['id'], version=version['version'], overrides={'desire': '寻找姐姐', 'secrets': '知道暗门', 'visual_state': '黄色雨衣'})
    snap = client.portal.call(snapshot)
    assert snap.frozen_identity['bio'] == '灯塔维修员'
    current = next(c for c in client.get('/api/characters').json()['items'] if c['id'] == g['id'])
    assert current.get('default_desire', '') != '寻找姐姐'
    promoted = client.post(f'/api/character-snapshots/{snap.id}/promote').json()
    assert promoted['identity_spec']['default_desire'] == '寻找姐姐'
    assert promoted['identity_spec']['default_secrets'] == '知道暗门'
    assert promoted['identity_spec']['appearance'] == '黄色雨衣'
    assert promoted['version'] > current['version']
    assert client.portal.call(service.list_snapshots, 'ver_overlay_contract')[0].character_version == version['version']

def test_character_ai_generation_uses_configured_resolution(client, monkeypatch):
    """Exercise the real API seam so generation settings cannot regress to a NameError."""
    from app.config import settings
    from app.main import provider_router

    character = client.post('/api/characters', json={
        'name': '配置回归角色', 'bio': '验证角色生图参数贯通'}).json()
    seen = {}

    class FakeImageProvider:
        name = 'nano_banana_2'

        async def generate(self, request):
            seen.update(request)
            return {
                'images': [{'url': 'https://example.invalid/candidate.png'}],
                'model': 'test-image-model',
                'resolution': request['resolution'],
                'aspect_ratio': request['aspect_ratio'],
            }

    monkeypatch.setitem(provider_router.registry, 'nano_banana_2', FakeImageProvider())
    previous_resolution = settings.image_generation_resolution
    previous_ratio = settings.generation_aspect_ratio
    settings.image_generation_resolution = '4K'
    settings.generation_aspect_ratio = '16:9'
    try:
        response = client.post(f"/api/characters/{character['id']}/ai-generate",
                               json={'prompt': '测试角色', 'num_images': 1})
    finally:
        settings.image_generation_resolution = previous_resolution
        settings.generation_aspect_ratio = previous_ratio

    assert response.status_code == 200, response.text
    assert seen['resolution'] == '4K'
    assert seen['aspect_ratio'] == '16:9'
    assert response.json()['items'][0]['provenance']['resolution'] == '4K'

def test_safe_player_error_preserves_dev_evidence(client):
    from app.main import runtime_engine
    from app.domain.schemas import Branch, BranchSource, BranchStatus, ResolvedIntent
    sid = client.post('/api/sessions', json={'version_id': 'ver_rainy_1_0_0'}).json()['session_id']
    async def inject():
        async with runtime_engine._lock(sid):
            state = await runtime_engine.load_session(sid)
            b = Branch(id='br_schema_injected', trace_id='t', session_id=sid, arc_id=state.current_arc().id, base_versions=runtime_engine._branch_base_versions(state), source=BranchSource.FREE, status=BranchStatus.FAILED, label='推开门', intent=ResolvedIntent(raw_text='推开门'), last_error='Pydantic ValidationError https://errors.pydantic.dev')
            state.branches.append(b); state.pending_freeform_id = b.id; state.player.status = 'FAILED_RECOVERABLE'
            await runtime_engine._persist(state)
            return runtime_engine.player_view(state)
    view = client.portal.call(inject)
    assert 'Pydantic' not in json.dumps(view)
    dev = client.get(f'/api/dev/sessions/{sid}/state').json()
    assert 'Pydantic' in json.dumps(dev)
    assert view['presentation']['recovery_actions'] == ['retry', 'modify', 'text_continue', 'exit']
    assert client.post(f'/api/sessions/{sid}/player', json={'command': 'text_continue'}).status_code == 200
    assert client.get(f'/api/dev/sessions/{sid}/state').json()['world'] == dev['world']

def test_public_reference_url_is_not_double_prefixed():
    from app.providers.real import FalH3MaxProvider
    from app.config import settings
    p = FalH3MaxProvider(api_key='offline')
    refs = p._adapt_references({'references': [{'path': '/files/assets/portrait.png', 'type': 'image'}]})
    assert refs['reference_image_urls'] == [settings.public_base_url.rstrip('/') + '/files/assets/portrait.png']

def test_director_schema_retry_is_bounded_and_recoverable(client, monkeypatch):
    from app.main import runtime_engine, provider_router
    from app.providers.base import TextResponse
    provider = provider_router.registry['mock_text']
    original = provider.generate
    attempts = []
    async def malformed(messages, output_contract=None, tools=None, budget=None):
        if (output_contract or {}).get('purpose') == 'director_plan' and any('raw_player_input: 我绕到后院查看暗门' in m.get('content','') for m in messages):
            attempts.append(1)
            return TextResponse(content='{"outcome":{"title":"门","text":"门关着"},"directive":{"target_changes":42}}', model='injected-invalid-schema', provider='mock_text')
        return await original(messages, output_contract, tools, budget)
    sid = client.post('/api/sessions', json={'version_id':'ver_rainy_1_0_0'}).json()['session_id']
    monkeypatch.setattr(provider, 'generate', malformed)
    r = client.post(f'/api/sessions/{sid}/action', json={'text':'我绕到后院查看暗门'})
    assert r.status_code == 200 and r.json()['status'] == 'FAILED_RECOVERABLE'
    assert len(attempts) == 2
    view = client.get(f'/api/sessions/{sid}/view').json()
    assert view['last_failed_action']['raw_text'] == '我绕到后院查看暗门'
    assert 'pydantic' not in json.dumps(view).lower()
    state = client.get(f'/api/dev/sessions/{sid}/state').json()
    assert state['world']['version'] == 1
    assert any(b['fail_stage'] == 'PLANNING' and 'validation' in (b['last_error'] or '').lower() for b in state['branches'])
    assert client.post(f'/api/sessions/{sid}/player', json={'command':'text_continue'}).status_code == 200

def test_opening_ready_is_never_a_recommendation():
    from app.main import runtime_engine
    from app.seed.rainy_apartment import rainy_apartment
    from app.domain.schemas import Branch, BranchSource, BranchStatus, RecommendationEpoch, SceneArtifact
    s = runtime_engine._bootstrap('v', 'rainy_apartment', rainy_apartment().model_dump())
    b = Branch(id='opening_race', trace_id='t', session_id=s.id, arc_id=s.current_arc().id,
               source=BranchSource.OPENING, status=BranchStatus.READY,
               base_versions=runtime_engine._branch_base_versions(s),
               fingerprint=runtime_engine.compute_fingerprint(s),
               artifact=SceneArtifact(id='a', branch_id='opening_race', quality_status='READY'))
    s.branches.append(b)
    s.epoch = RecommendationEpoch(id='e', published=True, ready_ids=[b.id])
    assert runtime_engine.player_view(s)['recommendations'] == []

def test_empty_video_exception_is_failure_not_assembly_success(client, monkeypatch):
    import time
    from app.main import runtime_engine
    attempts = []
    target = {"session_id": None}
    original = runtime_engine._generate_branch_media
    async def empty_failure(*args):
        if args[0] != target["session_id"]:
            return await original(*args)
        attempts.append(1)
        raise TimeoutError()  # str(error) is empty; it must still fail the phase.
    monkeypatch.setattr(runtime_engine, '_generate_branch_media', empty_failure)
    sid = client.post('/api/sessions', json={'version_id':'ver_rainy_1_0_0'}).json()['session_id']
    target["session_id"] = sid
    deadline = time.time() + 10
    while time.time() < deadline:
        state = client.get(f'/api/dev/sessions/{sid}/state').json()
        if state['player']['status'] == 'FAILED_RECOVERABLE': break
        time.sleep(.1)
    assert state['player']['status'] == 'FAILED_RECOVERABLE'
    branch = state['branches'][0]
    assert branch['fail_stage'] == 'GENERATING'
    assert 'TimeoutError' in branch['last_error']
    assert branch['artifact'] is None
    assert len(attempts) == 2

def test_timed_window_waits_for_server_decision_lead(client):
    import asyncio
    from app.main import runtime_engine
    from app.seed.rainy_apartment import rainy_apartment
    from app.domain.schemas import Branch, BranchSource, BranchStatus, RecommendationEpoch, SceneArtifact
    from app.runtime.session_state import TimedState
    async def run():
        s=runtime_engine._bootstrap('v','rainy_apartment',rainy_apartment().model_dump())
        runtime_engine.sessions[s.id]=s
        s.player.status='PLAYING';s.player.duration=10;s.player.decision_open_at=8;s.player.position_base=1;s.player.playing=False
        b=Branch(id='timed_lead',trace_id='t',session_id=s.id,arc_id=s.current_arc().id,source=BranchSource.TIMED,status=BranchStatus.READY,base_versions=runtime_engine._branch_base_versions(s),fingerprint=runtime_engine.compute_fingerprint(s),artifact=SceneArtifact(id='a',branch_id='timed_lead',quality_status='READY'))
        s.branches.append(b);s.epoch=RecommendationEpoch(id='e',branch_ids=[b.id],timed=True);s.timed=TimedState(active=True,timeout_seconds=5)
        await runtime_engine._maybe_publish(s)
        assert s.timed.deadline_ms is None and not s.timed.selection_open
        assert runtime_engine.player_view(s)['recommendations']==[]
        s.player.position_base=8
        await asyncio.sleep(.35)
        assert s.timed.deadline_ms and s.timed.selection_open
        assert runtime_engine.player_view(s)['recommendations']
        runtime_engine._cancel_timed(s)
    client.portal.call(run)

def test_ending_promotes_to_full_scene_and_reuses_director_plan(client, monkeypatch):
    import time
    from app.main import runtime_engine
    from app.domain.schemas import ProviderRouteRecord
    calls=[]
    original=runtime_engine._director_output
    text='验收：我决定退出当前矛盾并离开'
    async def plan(messages, mechanics, session_id, branch_id=None):
        if any(text in m.get('content','') for m in messages):
            calls.append(1)
            return {'outcome':{'title':'离开','text':'你离开这场矛盾。','mode':'QUICK_ACK','ending':'voluntary_departure','ops':[],'evidence':[]},'directive':{'primary_function':'CLOSE_CURRENT_ARC'}},ProviderRouteRecord(role='director',primary='mock_text',selected='mock_text',status='healthy')
        return await original(messages,mechanics,session_id,branch_id)
    monkeypatch.setattr(runtime_engine,'_director_output',plan)
    sid=client.post('/api/sessions',json={'version_id':'ver_rainy_1_0_0'}).json()['session_id']
    opening_deadline=time.time()+20
    while time.time()<opening_deadline:
        if client.get(f'/api/sessions/{sid}/view').json()['player']['video_url']:break
        time.sleep(.2)
    r=client.post(f'/api/sessions/{sid}/action',json={'text':text})
    assert r.json()['status']=='GENERATING',r.text
    deadline=time.time()+30
    while time.time()<deadline:
        s=client.get(f'/api/dev/sessions/{sid}/state').json()
        if s['ended']:break
        time.sleep(.2)
    assert s['ended']
    assert len(calls)==1
    assert s['arcs'][-1]['ending_family']=='voluntary_departure'

def test_text_recovery_closes_accepted_ending_once(client):
    from app.main import runtime_engine
    from app.domain.schemas import Branch, BranchSource, BranchStatus, OutcomeSpec, ResolvedIntent
    from app.seed.rainy_apartment import rainy_apartment
    async def arrange():
        s=runtime_engine._bootstrap('v','rainy_apartment',rainy_apartment().model_dump())
        runtime_engine.sessions[s.id]=s
        b=Branch(id='text_recover_ending',session_id=s.id,arc_id=s.current_arc().id,source=BranchSource.FREE,status=BranchStatus.FAILED,
                 label='离开',intent=ResolvedIntent(raw_text='离开'),base_versions=runtime_engine._branch_base_versions(s),
                 fingerprint=runtime_engine.compute_fingerprint(s),outcome=OutcomeSpec(title='告别',text='你离开这场矛盾。',ending='voluntary_departure'),narrative='你离开这场矛盾。',last_error='video provider unavailable')
        s.branches.append(b);s.pending_freeform_id=b.id;s.player.status='FAILED_RECOVERABLE'
        await runtime_engine._persist(s)
        return s.id
    sid=client.portal.call(arrange)
    response=client.post(f'/api/sessions/{sid}/player',json={'command':'text_continue'})
    assert response.status_code==200,response.text
    s=client.get(f'/api/dev/sessions/{sid}/state').json()
    assert s['ended'] and s['arcs'][-1]['status']=='CLOSED'
    assert s['branches'][0]['artifact']['media_type']=='text'
    assert s['player']['video_url']==''
    assert client.get(f'/api/sessions/{sid}/view').json()['recommendations']==[]
    assert client.post(f'/api/sessions/{sid}/player',json={'command':'text_continue'}).status_code==200
    after=client.get(f'/api/dev/sessions/{sid}/state').json()
    assert after['world']==s['world'] and after['drama']==s['drama']
    assert len([e for e in after['events'] if e['type']=='branch_canonical'])==1

def test_natural_relationships_commit_without_requiring_numeric_dsl():
    from app.main import runtime_engine
    from app.skills.mechanic import invoke
    from app.domain.schemas import WorldState, StatePatchProposal
    from app.domain.state_manager import StateManager
    snapshot = {'player_character': 'detective', 'characters': [
        {'id': 'detective', 'relationship': ''},
        {'id': 'keeper', 'relationship': '与调查员是旧识'},
        {'id': 'explicit', 'relationship': '对玩家信任 42 / 100'}]}
    fresh = runtime_engine._bootstrap('v', 'lighthouse', snapshot)
    assert fresh.world.relationships == {'keeper': 50, 'explicit': 42}
    # Existing Sessions keep their facts; the first change is only a proposal.
    legacy = WorldState()
    result = invoke('relationship', {'target': 'keeper', 'value': 5},
                    {'npcs': [{'id': 'keeper'}], 'relationships': legacy.relationships},
                    {'relationship': {'enabled': True, 'config': {}}}, 'branch', 1, 1)
    assert legacy.relationships == {}
    changed = StateManager().validate(legacy, StatePatchProposal.model_validate(result['proposal']), [], drama_revision=1)
    assert changed.relationships == {'keeper': 55} and legacy.relationships == {}
    again = invoke('relationship', {'target': 'keeper', 'value': 5},
                   {'npcs': [{'id': 'keeper'}], 'relationships': changed.relationships},
                   {'relationship': {'enabled': True, 'config': {}}}, 'next', 2, 1)
    changed = StateManager().validate(changed, StatePatchProposal.model_validate(again['proposal']), [], drama_revision=1)
    assert changed.relationships == {'keeper': 60}


def test_rejected_commit_is_recoverable_without_state_mutation(client):
    from app.main import runtime_engine
    from app.domain.schemas import Branch, BranchSource, BranchStatus, OutcomeSpec, StatePatchProposal, PatchOperation
    from app.seed.rainy_apartment import rainy_apartment
    async def run():
        state = runtime_engine._bootstrap('v', 'rainy_apartment', rainy_apartment().model_dump())
        state.text_mode = True
        before = state.world.model_dump()
        b = Branch(id='rejected_commit_recovery', session_id=state.id, arc_id=state.current_arc().id,
                   source=BranchSource.FREE, status=BranchStatus.READY, label='坏提案', narrative='原行动仍保留。',
                   base_versions=runtime_engine._branch_base_versions(state), outcome=OutcomeSpec(title='行动',text='原行动仍保留。'),
                   state_patch_proposal=StatePatchProposal(proposal_id='bad',base_version=1,source='test',
                       operations=[PatchOperation(op='increment',path='objects.missing',value=1)]))
        state.branches.append(b);state.pending_freeform_id=b.id;state.player.status='GENERATING_NEXT'
        await runtime_engine._text_artifact(state, b)
        await runtime_engine._commit_selected(state,b)
        assert state.world.model_dump()==before
        assert b.status==BranchStatus.FAILED and b.fail_stage=='COMMIT'
        assert state.player.status=='FAILED_RECOVERABLE'
        assert runtime_engine.player_view(state)['presentation']['recovery_actions']
    client.portal.call(run)

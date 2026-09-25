from app.runtime.engine import RuntimeEngine


def test_truncated_director_retry_preserves_source_without_reinjecting_draft(monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    from app.runtime.tracer import tracer
    calls = []
    truncated = '{"outcome":{"text":"' + 'untrusted draft ' * 2000
    valid = json.dumps({'outcome': {'title': 'Reviewed', 'text': 'Observed',
                       'ops': [], 'evidence': [], 'skill_triggers': []},
                       'directive': {'primary_function': 'RESPOND_TO_PLAYER_ACTION'}})
    async def call(role, **kwargs):
        calls.append(kwargs['messages'])
        if len(calls) == 2:
            assert all(truncated not in m['content'] for m in kwargs['messages'])
            assert any(m['content'] == 'Authoritative source' for m in kwargs['messages'])
            assert sum(len(m['content']) for m in kwargs['messages']) < sum(len(m['content']) for m in calls[0]) + 800
        return None, SimpleNamespace(selected='nemotron_local'), SimpleNamespace(content=truncated if len(calls) == 1 else valid, model='local')
    async def emit(*a, **kw): pass
    monkeypatch.setattr(tracer, 'emit', emit)
    engine = RuntimeEngine(SimpleNamespace(call_text=call))
    result, _ = asyncio.run(engine._director_output([{'role': 'user', 'content': 'Authoritative source'}], {}, 's'))
    assert result['outcome']['text'] == 'Observed'
    assert len(calls) == 2


def test_director_brief_keeps_authored_opening_player_and_world_constraints():
    engine = RuntimeEngine(None)
    snapshot = {
        'title': 'Generic Observatory',
        'description': 'An investigation under a failing dome.',
        'player_character': 'investigator',
        'characters': [{'id': 'investigator', 'identity': 'Field investigator', 'knowledge': 'Only visible evidence'},
                       {'id': 'operator', 'identity': 'Remote operator'}],
        'world': {'rules': 'Travel requires connected corridors.', 'constraints': 'No teleportation'},
        'drama': {'anchors': 'The investigator arrives with a partner; the operator speaks only by radio.',
                  'forbidden_outcomes': 'Do not reveal the hidden cause at arrival.'},
    }
    state = engine._bootstrap('context-version', 'context-story', snapshot)
    brief = engine._scenario_brief(state)
    assert brief['authored_anchors'] == snapshot['drama']['anchors']
    assert brief['player']['id'] == 'investigator'
    assert brief['player']['knowledge'] == 'Only visible evidence'
    assert brief['world_rules'] == snapshot['world']['rules']
    assert brief['world_constraints'] == snapshot['world']['constraints']
    assert brief['forbidden_outcomes'] == snapshot['drama']['forbidden_outcomes']
    assert brief['premise'] == snapshot['description']


def test_director_recent_context_contains_only_committed_beats():
    from app.domain.schemas import Branch, BranchSource, BranchStatus, OutcomeSpec
    engine=RuntimeEngine(None)
    state=engine._bootstrap('v','s',{})
    for status,title in [(BranchStatus.CANONICAL,'Observed record'),(BranchStatus.READY,'Unchosen secret')]:
        state.branches.append(Branch(id=title,session_id=state.id,arc_id=state.current_arc().id,
            base_versions=engine._branch_base_versions(state),
            source=BranchSource.FREE,status=status,outcome=OutcomeSpec(title=title,text=title)))
    context=engine._scenario_brief(state)
    assert [b['title'] for b in context['recent_canonical_beats']]==['Observed record']

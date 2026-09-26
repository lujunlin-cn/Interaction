import asyncio
import json
from types import SimpleNamespace

import httpx

from app.providers.real import OpenAICompatTextProvider
from test_runtime_media_readiness import fixture_engine


def test_production_constraints_reach_local_decoder(monkeypatch):
    engine, state, branch, route = fixture_engine(monkeypatch)
    state.scenario_snapshot['characters'][1]['id'] = 'actor_random_42'
    for asset in state.asset_manifest:
        if asset['entity'] == 'beta':
            asset['entity'] = 'actor_random_42'
    original = httpx.AsyncClient
    captured = []

    async def respond(request):
        payload = json.loads(request.content)
        captured.append(payload)
        contract = payload['response_format']
        assert contract['type'] == 'json_schema'
        shot = contract['json_schema']['schema']['properties']['shots']
        assert shot['minItems'] == shot['maxItems'] == 1
        ids = shot['items']['properties']['cast']['items']['enum']
        assert 'actor_random_42' in ids
        assert 'beta' not in ids
        return httpx.Response(200, json={'id': 'local-request-42', 'model': 'test-local', 'choices': [{'message': {'content': json.dumps({
            'shots': [{'title': 'Arrival', 'prompt': 'Two people arrive.', 'subtitle': 'Arrival',
                       'duration': 5, 'cast': ['alpha', 'actor_random_42']}]
        })}}]})

    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    provider = OpenAICompatTextProvider('nemotron_local', 'http://127.0.0.1:8001/v1', '', 'test-local')

    async def text(role, **kw):
        response = await provider.generate(kw['messages'], kw['output_contract'])
        assert response.request_id == 'local-request-42'
        return provider, route, response

    from types import SimpleNamespace
    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._shoot_branch(state, branch))
    assert len(captured) == 1
    assert {r['entity'] for r in branch.shots[0].references} == {'alpha', 'actor_random_42'}
    assert branch.jobs == []


def test_production_repairs_identity_mismatch_before_reference_binding(monkeypatch):
    """A model cast typo must not send Victor's reference for a Leon shot."""
    from app.providers.base import TextResponse
    engine, state, branch, route = fixture_engine(monkeypatch)
    chars = state.scenario_snapshot["characters"]
    chars[0].update(id="leon", identity="李昂·S·肯尼迪（Leon S. Kennedy）", global_character_id="g-leon")
    chars[1].update(id="claire", identity="克莱尔·雷德菲尔德（Claire Redfield）", global_character_id="g-claire")
    chars[2].update(id="victor", identity="Dr. Victor Hale", global_character_id="g-victor")
    state.asset_manifest = [
        {"id": "leon-front", "entity": "leon", "role": "front", "path": "https://example.invalid/leon.png", "type": "image"},
        {"id": "claire-front", "entity": "claire", "role": "front", "path": "https://example.invalid/claire.png", "type": "image"},
        {"id": "victor-front", "entity": "victor", "role": "front", "path": "https://example.invalid/victor.png", "type": "image"},
    ]

    async def text(*args, **kwargs):
        return None, route, TextResponse(content=json.dumps({"shots": [{
            "title": "突围", "prompt": "Leon S. Kennedy and Claire Redfield run through a corridor.",
            "subtitle": "突围", "duration": 5, "cast": ["victor", "claire"]
        }]}))

    engine.router = SimpleNamespace(call_text=text)
    asyncio.run(engine._shoot_branch(state, branch))
    assert branch.shots[0].params["cast"] == ["leon", "claire"]
    assert {ref["entity"] for ref in branch.shots[0].references} == {"leon", "claire"}

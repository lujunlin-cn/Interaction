import asyncio
import json

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

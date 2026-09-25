"""Character scope contracts. Uploaded fixtures never call a media provider."""
import base64
import copy

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aB3sAAAAASUVORK5CYII=')


def upload(client, url, name, mime='image/png'):
    response = client.post(url, files={'file': (name, PNG, mime)})
    assert response.status_code == 200, response.text
    return response.json()['id']


def get_character(client, cid):
    return next(c for c in client.get('/api/characters').json()['items'] if c['id'] == cid)


def setup_scope(client):
    g = client.post('/api/characters', json={'name': 'Alice', 'bio': 'Facilities researcher'}).json()
    url = f"/api/characters/{g['id']}"
    assets = {name: upload(client, url + '/assets', name + '.png') for name in ['front', 'raincoat', 'standing', 'sitting', 'leaning']}
    for name, mime in [('walk', 'video/mp4'), ('run', 'video/mp4'), ('voice_a', 'audio/wav'), ('voice_b', 'audio/wav')]:
        assets[name] = upload(client, url + '/assets', name, mime)
    default = client.post(url + '/outfits', json={'name': 'Default'}).json()
    yellow = client.post(url + '/outfits', json={'name': 'Yellow Raincoat', 'description': 'Waterproof yellow coat'}).json()
    response = client.patch(url + f"/outfits/{yellow['id']}", json={'reference_slots': {'front': assets['raincoat'], 'additional': []}})
    assert response.status_code == 200, response.text
    assert response.json()['reference_assets'] == [assets['raincoat']]
    response = client.patch(url, json={
        'ref_front_asset': assets['front'],
        'ref_pose_assets': [assets[x] for x in ['standing', 'sitting', 'leaning']],
        'ref_motion_assets': [assets['walk'], assets['run']],
        'ref_voice_asset': assets['voice_a'], 'alternate_voice_assets': [assets['voice_b']],
    })
    assert response.status_code == 200, response.text
    g = response.json()
    d = client.post('/api/scenarios', json={'idea': 'A researcher investigates a sealed facility'}).json()
    sc = dict(id='alice', identity='Alice', global_character_id=g['id'], global_character_version=g['version'],
              outfit_id=yellow['id'], pose_refs=[assets['standing'], assets['leaning']],
              motion_refs=[assets['walk']], voice_id=assets['voice_b'],
              overlay_sources={'outfit': 'OVERRIDE', 'pose': 'OVERRIDE', 'motion': 'OVERRIDE', 'voice': 'OVERRIDE'})
    d['characters'] = [sc]
    d['player_character'] = 'alice'
    return g, d, assets, default, yellow


def test_publish_freezes_all_overlay_modules_and_promote_creates_new_version(client, monkeypatch):
    from app.main import runtime_engine
    g, d, assets, default, yellow = setup_scope(client)
    original = copy.deepcopy(g)
    url = f"/api/scenarios/{d['id']}"
    response = client.put(url, json=d)
    assert response.status_code == 200, response.text
    saved = client.get(url).json()
    assert saved['characters'][0]['pose_refs'] == [assets['standing'], assets['leaning']]
    assert get_character(client, g['id']) == original
    published = client.post(url + '/publish', json={'reviewed': True}).json()
    snapshots = client.get(f"/api/scenarios/{published['version_id']}/character-snapshots").json()['items']
    snap = snapshots[0]
    assert snap['character_version'] == g['version']
    assert snap['frozen_asset_refs']['outfit'] == [assets['raincoat']]
    assert snap['frozen_asset_refs']['pose'] == [assets['standing'], assets['leaning']]
    assert snap['frozen_asset_refs']['motion'] == [assets['walk']]
    assert snap['frozen_asset_refs']['voice'] == assets['voice_b']
    resolved = client.post(f"/api/character-snapshots/{snap['id']}/resolve-references",
                           json={'scene_or_shot_id': 'scope-check'}).json()
    assert assets['raincoat'] in resolved['selected_image_refs']
    assert resolved['voice_ref'] == assets['voice_b']
    assert resolved['motion_ref'] == assets['walk']

    # Session construction consumes uploaded refs without starting generation.
    async def no_opening(*args):
        pass
    monkeypatch.setattr(runtime_engine, '_start_opening', no_opening)
    sid = client.post('/api/sessions', json={'version_id': published['version_id']}).json()['session_id']
    state = client.get(f'/api/dev/sessions/{sid}/state').json()
    manifest = {a['id']: a for a in state['asset_manifest']}
    for name in ['front', 'raincoat', 'standing', 'leaning', 'walk', 'voice_b']:
        assert manifest[assets[name]]['entity'] == 'alice'
    assert assets['sitting'] not in manifest
    assert assets['run'] not in manifest
    assert assets['voice_a'] not in manifest
    assert manifest[assets['walk']]['type'] == 'video'
    assert manifest[assets['voice_b']]['type'] == 'voice'
    # Uploading a new, unselected story reference must not erase frozen refs or
    # silently insert it into an already-published session's production input.
    response = client.post(url + '/assets', data={'entity': 'alice', 'binding': 'alice', 'role': 'pose'},
                           files={'file': ('unused.png', PNG, 'image/png')})
    assert response.status_code == 200, response.text
    refreshed = client.get(f'/api/dev/sessions/{sid}/state').json()['asset_manifest']
    assert {a['id'] for a in refreshed} == set(manifest)

    promoted = client.post(url + '/characters/alice/promote')
    assert promoted.status_code == 200, promoted.text
    promoted = promoted.json()
    assert promoted['version'] > g['version']
    assert promoted['canonical_voice_ref'] == assets['voice_b']
    assert assets['voice_a'] in promoted['alternate_voice_refs']
    assert promoted['pose_refs'] == [assets['standing'], assets['leaning']]
    assert promoted['motion_refs'] == [assets['walk']]
    assert next(o for o in promoted['outfits'] if o['is_default'])['id'] == yellow['id']
    assert client.get(url).json()['characters'][0]['global_character_version'] == g['version']
    assert client.get(f"/api/scenarios/{published['version_id']}/character-snapshots").json()['items'][0] == snap


def test_local_refs_and_empty_override_do_not_leak_or_reinherit(client):
    g, d, assets, default, yellow = setup_scope(client)
    url = f"/api/scenarios/{d['id']}"
    local = upload(client, url + '/assets', 'local-pose.png')
    ch = d['characters'][0]
    ch.update(local_outfits=[{'id': 'story_only', 'name': 'Work clothes', 'reference_slots': {'front': local}}],
              outfit_id='story_only', pose_refs=[local], motion_refs=[], voice_id=None,
              reference_overrides={'front': local, 'other': []})
    ch['overlay_sources']['reference'] = 'OVERRIDE'
    assert client.put(url, json=d).status_code == 200
    assert get_character(client, g['id']) == g
    published = client.post(url + '/publish', json={'reviewed': True}).json()
    snap = client.get(f"/api/scenarios/{published['version_id']}/character-snapshots").json()['items'][0]
    refs = snap['frozen_asset_refs']
    assert refs['front'] == local and refs['outfit'] == [local]
    assert refs['pose'] == [local] and refs['motion'] == [] and refs['voice'] is None
    promoted = client.post(f"/api/character-snapshots/{snap['id']}/promote").json()
    assert promoted['canonical_voice_ref'] is None
    assert promoted['motion_refs'] == []
    assert promoted['canonical_asset_refs']['front'] == local
    assert next(o for o in promoted['outfits'] if o['is_default'])['id'] == 'story_only'
    assert local in [a['id'] for a in client.get(f"/api/characters/{g['id']}/assets").json()['items']]
    assert client.get(url).json()['characters'][0]['global_character_version'] == g['version']


def test_pinned_inheritance_ignores_latest_library_until_explicit_update(client):
    g, d, assets, default, yellow = setup_scope(client)
    sc = d['characters'][0]
    sc['overlay_sources'] = {k: 'INHERIT' for k in ['outfit', 'pose', 'motion', 'voice']}
    url = f"/api/scenarios/{d['id']}"
    assert client.put(url, json=d).status_code == 200
    latest = client.patch(f"/api/characters/{g['id']}", json={'ref_pose_assets': [], 'ref_motion_assets': [], 'ref_voice_asset': assets['voice_b']}).json()
    first = client.post(url + '/publish', json={'reviewed': True}).json()
    snap = client.get(f"/api/scenarios/{first['version_id']}/character-snapshots").json()['items'][0]
    assert len(snap['frozen_asset_refs']['pose']) == 3
    assert len(snap['frozen_asset_refs']['motion']) == 2
    assert snap['frozen_asset_refs']['voice'] == assets['voice_a']
    d = client.get(url).json()
    d['characters'][0]['global_character_version'] = latest['version']
    assert client.put(url, json=d).status_code == 200
    second = client.post(url + '/publish', json={'reviewed': True}).json()
    updated = client.get(f"/api/scenarios/{second['version_id']}/character-snapshots").json()['items'][0]
    assert updated['frozen_asset_refs']['pose'] == []
    assert updated['frozen_asset_refs']['voice'] == assets['voice_b']
    assert client.get(f"/api/scenarios/{first['version_id']}/character-snapshots").json()['items'][0] == snap


def test_malformed_scenario_returns_safe_422_without_changing_draft(client):
    d = client.post('/api/scenarios', json={'idea': 'A foggy lighthouse'}).json()
    url = f"/api/scenarios/{d['id']}"
    bad = copy.deepcopy(d)
    bad['characters'][0]['pose_refs'] = {'unexpected': 'object'}
    response = client.put(url, json=bad)
    assert response.status_code == 422
    assert 'pydantic' not in response.text.lower()
    assert client.get(url).json() == d

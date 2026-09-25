"""Character Library duplicate hints, durable create retries and archival."""
from concurrent.futures import ThreadPoolExecutor


def test_concurrent_creation_token_commits_one_character_and_version(client):
    payload = {"name": "Concurrent Identity", "bio": "parallel retry",
               "creation_idempotency_key": "concurrent-operation"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: client.post("/api/characters", json=payload), range(8)))
    assert [r.status_code for r in responses] == [200] * 8
    ids = {r.json()["id"] for r in responses}
    assert len(ids) == 1
    cid = ids.pop()
    assert all(r.json().get("current_version_id") for r in responses)
    assert len(client.get(f"/api/characters/{cid}/versions").json()["items"]) == 1
    conflict = client.post("/api/characters", json={**payload, "name": "Different person"})
    assert conflict.status_code == 409


def test_duplicate_alias_and_unicode_normalization(client):
    original = client.post("/api/characters", json={"name": "林岚（Lin Lan）", "bio": "bilingual",
                         "aliases": ["Archivist Lin"]}).json()
    for name in ["ＬＩＮ ＬＡＮ", "林·岚", "archivist-lin"]:
        response = client.get("/api/characters/duplicates", params={"name": name})
        assert original["id"] in {c["id"] for c in response.json()["items"]}

def test_duplicate_name_is_advisory_and_idempotency_is_durable(client):
    first = client.post("/api/characters", json={
        "name": "Claire · Redfield", "bio": "first", "creation_idempotency_key": "dup-test-1",
    })
    assert first.status_code == 200
    first_id = first.json()["id"]

    # A same-key retry must return the original object, even though the name
    # would otherwise trigger the duplicate advisory.
    retry = client.post("/api/characters", json={
        "name": "Claire · Redfield", "bio": "first", "creation_idempotency_key": "dup-test-1",
    })
    assert retry.status_code == 200
    assert retry.json()["id"] == first_id

    hint = client.post("/api/characters", json={"name": " Claire-Redfield ", "bio": "second"})
    assert hint.status_code == 409
    detail = hint.json()["detail"]
    assert detail["code"] == "DUPLICATE_CHARACTER"
    assert any(item["id"] == first_id for item in detail["candidates"])

    explicit = client.post("/api/characters", json={
        "name": " Claire-Redfield ", "bio": "second", "confirm_duplicate": True,
        "creation_idempotency_key": "dup-test-2",
    })
    assert explicit.status_code == 200
    assert explicit.json()["id"] != first_id


def test_archived_character_hidden_but_history_resolvable(client):
    created = client.post("/api/characters", json={"name": "Archive Me", "bio": "history"}).json()
    cid = created["id"]
    snapshot_response = client.post(f"/api/scenarios/archive-history/character-snapshots/{cid}",
                                    json={"character_version": 1})
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    versions_before = client.get(f"/api/characters/{cid}/versions").json()
    archived = client.post(f"/api/characters/{cid}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    active = client.get("/api/characters").json()["items"]
    assert cid not in {item["id"] for item in active}
    all_items = client.get("/api/characters?include_archived=true").json()["items"]
    assert next(item for item in all_items if item["id"] == cid)["status"] == "ARCHIVED"
    assert client.get(f"/api/scenarios/archive-history/character-snapshots").json()["items"] == [snapshot]
    assert client.get(f"/api/characters/{cid}/versions").json() == versions_before
    resolved = client.post(f"/api/character-snapshots/{snapshot['id']}/resolve-references", json={"scene_context": {}})
    assert resolved.status_code == 200

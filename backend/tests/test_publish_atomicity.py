"""Publication and pinned character snapshots commit as one isolated transaction.

These tests use a temporary SQLite database and the real publish route. They do
not start the application lifespan, create media, or touch the live database.
"""
import copy
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes import build_api
from app.db import Base
from app.db_models import ScenarioCharacterSnapshotRow, ScenarioVersionRow
from app.domain.schemas import ScenarioCharacter
from app.runtime import character_service, scenario_service
from app.seed.rainy_apartment import rainy_apartment


@pytest_asyncio.fixture
async def publication(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'publication.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(scenario_service, "SessionLocal", sessions)
    monkeypatch.setattr(character_service, "SessionLocal", sessions)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    played = []

    async def create_session(version_id):
        played.append(version_id)
        return SimpleNamespace(id="unexpected_session")

    scenarios = scenario_service.ScenarioService(None)
    characters = scenario_service.CharacterService()
    assets = character_service.CharacterAssetService(None)
    bound = []
    for name in ("Alice", "Morgan"):
        character = await characters.create({"name": name, "bio": f"{name} investigates the facility"})
        version = await assets._new_version(character["id"], "IDENTITY")
        bound.append(ScenarioCharacter(
            id=name.lower(), identity=name,
            global_character_id=character["id"], global_character_version=version.version,
            visual_state="Original story appearance", overlay_sources={"appearance": "OVERRIDE"}))
    draft = rainy_apartment()
    draft.id = "atomic_publication"
    draft.status = "DRAFT"
    draft.version = "0.1.0"
    draft.reviewed = False
    draft.characters = bound
    draft.player_character = "alice"
    await scenarios.save_draft(draft)
    app = FastAPI()
    app.include_router(build_api(SimpleNamespace(create_session=create_session), None))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                                base_url="http://isolated") as client:
        yield SimpleNamespace(client=client, scenarios=scenarios, characters=characters,
                              assets=assets, sessions=sessions, draft=draft, played=played)
    await engine.dispose()


async def stored_publication(sessions):
    async with sessions() as db:
        versions = (await db.execute(select(ScenarioVersionRow))).scalars().all()
        snapshots = (await db.execute(select(ScenarioCharacterSnapshotRow))).scalars().all()
        return ({row.id: copy.deepcopy(row.snapshot) for row in versions},
                {row.id: copy.deepcopy(row.data) for row in snapshots})


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_publication", [False, True])
@pytest.mark.parametrize("fail_after_snapshot", [1, 2])
async def test_snapshot_failure_rolls_back_version_draft_and_all_snapshots(
        publication, monkeypatch, existing_publication, fail_after_snapshot):
    p = publication
    endpoint = f"/api/scenarios/{p.draft.id}/publish"
    if existing_publication:
        response = await p.client.post(endpoint, json={"reviewed": True})
        assert response.status_code == 200, response.text
    before_draft = (await p.scenarios.get(p.draft.id)).model_dump(mode="json")
    before_records = await stored_publication(p.sessions)
    original = character_service.CharacterAssetService.snapshot_for_scenario
    calls = 0

    async def fail_snapshot(self, *args, **kwargs):
        nonlocal calls
        snapshot = await original(self, *args, **kwargs)
        calls += 1
        # Force SQL writes before failure, including the previous snapshot.
        if kwargs.get("db") is not None:
            await kwargs["db"].flush()
        if calls == fail_after_snapshot:
            raise RuntimeError("injected snapshot persistence failure")
        return snapshot

    monkeypatch.setattr(character_service.CharacterAssetService, "snapshot_for_scenario", fail_snapshot)
    response = await p.client.post(endpoint, json={"reviewed": True, "play": True})
    assert response.status_code == 500
    assert calls == fail_after_snapshot
    assert await stored_publication(p.sessions) == before_records, "partial published version or snapshots survived failure"
    assert (await p.scenarios.get(p.draft.id)).model_dump(mode="json") == before_draft
    assert p.played == [], "Play must not start after an incomplete publication"

    monkeypatch.setattr(character_service.CharacterAssetService, "snapshot_for_scenario", original)
    retry = await p.client.post(endpoint, json={"reviewed": True})
    assert retry.status_code == 200, retry.text
    result = retry.json()
    assert result["version"] == ("0.2.0" if existing_publication else "0.1.0")
    versions, snapshots = await stored_publication(p.sessions)
    assert len(versions) == len(before_records[0]) + 1
    assert len(snapshots) == len(before_records[1]) + 2
    assert set(result["character_snapshots"]) == {sid for sid, snap in snapshots.items()
                                                if snap["scenario_version_id"] == result["version_id"]}


@pytest.mark.asyncio
async def test_post_commit_draft_edit_cannot_change_published_snapshot_pin(publication, monkeypatch):
    p = publication
    original_draft = (await p.scenarios.get(p.draft.id)).model_dump(mode="json")
    character_id = p.draft.characters[0].global_character_id
    await p.characters.update(character_id, {"bio": "Changed later library definition"})
    latest = await p.assets._new_version(character_id, "IDENTITY")
    assert latest.version > p.draft.characters[0].global_character_version
    publish = scenario_service.ScenarioService.publish

    async def publish_then_edit(self, scenario_id, reviewed=False):
        result = await publish(self, scenario_id, reviewed=reviewed)
        # A real saved draft edit occurring immediately after version commit must
        # affect only the next publication, never the just-created snapshots.
        newer = await self.get(scenario_id)
        newer.characters[0].global_character_version = latest.version
        newer.characters[0].visual_state = "Later draft appearance"
        await self.save_draft(newer)
        return result

    monkeypatch.setattr(scenario_service.ScenarioService, "publish", publish_then_edit)
    response = await p.client.post(f"/api/scenarios/{p.draft.id}/publish", json={"reviewed": True})
    assert response.status_code == 200, response.text
    result = response.json()
    versions, snapshots = await stored_publication(p.sessions)
    frozen_draft = versions[result["version_id"]]
    assert frozen_draft["characters"] == original_draft["characters"]
    for snapshot in snapshots.values():
        expected = next(c for c in original_draft["characters"] if c["global_character_id"] == snapshot["global_character_id"])
        assert snapshot["character_version"] == expected["global_character_version"], "pin drifted from immutable ScenarioVersion"
        assert snapshot["local_overrides"] == expected
    current_draft = await p.scenarios.get(p.draft.id)
    assert current_draft.characters[0].global_character_version == latest.version
    assert current_draft.characters[0].visual_state == "Later draft appearance"
    assert (await p.assets.get_character(character_id))["version"] == latest.version
    assert p.played == []


@pytest.mark.asyncio
async def test_missing_pin_during_snapshot_rolls_back_and_returns_safe_gate_error(publication, monkeypatch):
    p = publication
    before_draft = (await p.scenarios.get(p.draft.id)).model_dump(mode="json")
    before_records = await stored_publication(p.sessions)

    async def missing_version(self, *args, **kwargs):
        assert kwargs.get("db") is not None
        await kwargs["db"].flush()
        raise KeyError("private_character_version_identifier")

    monkeypatch.setattr(character_service.CharacterAssetService, "snapshot_for_scenario", missing_version)
    response = await p.client.post(f"/api/scenarios/{p.draft.id}/publish", json={"reviewed": True, "play": True})
    assert response.status_code == 422
    assert response.json()["detail"] == "角色版本暂时不可用，请刷新后重新审阅。"
    assert "private_character_version_identifier" not in response.text
    assert await stored_publication(p.sessions) == before_records
    assert (await p.scenarios.get(p.draft.id)).model_dump(mode="json") == before_draft
    assert p.played == []


@pytest.mark.asyncio
async def test_standalone_snapshot_api_remains_compatible(publication):
    p = publication
    character_id = p.draft.characters[0].global_character_id
    original_version = p.draft.characters[0].global_character_version
    await p.characters.update(character_id, {"bio": "New library biography"})
    latest = await p.assets._new_version(character_id, "IDENTITY")
    response = await p.client.post(f"/api/scenarios/standalone_version/character-snapshots/{character_id}")
    assert response.status_code == 200, response.text
    snapshot = response.json()
    assert snapshot["character_version"] == latest.version
    assert snapshot["frozen_identity"]["bio"] == "New library biography"
    assert snapshot["local_overrides"] == {}
    listed = await p.client.get("/api/scenarios/standalone_version/character-snapshots")
    assert listed.json()["items"] == [snapshot]
    pinned = await p.assets.snapshot_for_scenario("explicit_pin_version", character_id, version=original_version)
    assert pinned.character_version == original_version
    assert pinned.frozen_identity["bio"] == "Alice investigates the facility"
    assert p.played == []

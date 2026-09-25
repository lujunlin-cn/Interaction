"""No-network, no-DB regression for confirmed location-gated QTE."""
import asyncio
import json
from types import SimpleNamespace

import pytest


def timed_state(location="entry", after=1, locations=None):
    from app.runtime.engine import RuntimeEngine
    engine = RuntimeEngine(None)
    state = engine._bootstrap("location-version", "location-scenario", {
        "title": "Generic Facility",
        "world": {"locations": "entry｜入口\nvault｜储藏室\ncontrol｜控制室"},
        "mechanics": {"qte": {"enabled": True, "config": {
            "trigger_after_actions": after, "trigger_location_ids": locations or ["vault", "control"]}}},
        "drama": {"timed_interactions": "pursuit｜qte｜10｜错过封锁门，必须绕路"},
    })
    state.world.location = location
    state.turns = [{"arc_seq": state.current_arc().seq, "opening": False}]
    return engine, state


def test_qte_waits_for_canonical_location_after_action_threshold():
    engine, state = timed_state()
    assert engine._next_timed_node(state) is None
    # A speculative outcome mentioning the target cannot open the QTE.
    state.messages.append({"text": "投机分支可能前往储藏室"})
    assert engine._next_timed_node(state) is None
    state.world.location = "vault"
    assert engine._next_timed_node(state)["id"] == "pursuit"
    state.world.location = "control"
    assert engine._next_timed_node(state)["id"] == "pursuit"


def test_location_match_does_not_bypass_action_threshold_or_fired_node():
    engine, state = timed_state(location="vault", after=2)
    assert engine._next_timed_node(state) is None
    state.turns.append({"arc_seq": state.current_arc().seq, "opening": False})
    assert engine._next_timed_node(state)
    state.timed.fired_nodes.append("pursuit")
    assert engine._next_timed_node(state) is None


def test_empty_location_filter_preserves_legacy_behavior():
    from app.domain.mechanic_spec import QteConfig
    config = QteConfig().model_dump()
    assert config["trigger_location_ids"] == []
    engine, state = timed_state()
    state.scenario_snapshot["mechanics"]["qte"]["config"] = config
    assert engine._next_timed_node(state)


def test_typed_location_references_validated_against_scenario():
    from app.domain.schemas import ScenarioDraft, WorldSpec
    from app.runtime.scenario_service import ScenarioService
    draft = ScenarioDraft(id="validate-locations", world=WorldSpec(locations="entry｜入口\nvault｜储藏室"))
    valid = {"enabled": True, "config": {"trigger_location_ids": ["vault"]}}
    result = ScenarioService.validate_patch(draft, "mechanics.qte", valid)
    assert result.mechanics["qte"].config["trigger_location_ids"] == ["vault"]
    with pytest.raises(ValueError, match="地点"):
        ScenarioService.validate_patch(draft, "mechanics.qte", {"enabled": True, "config": {"trigger_location_ids": ["invented"]}})
    with pytest.raises(ValueError, match="地点"):
        ScenarioService.validate_patch(result, "world.locations", "entry｜入口")


def test_mechanics_compiler_receives_locations_and_preserves_confirmed_ids(monkeypatch):
    from app.domain.mechanic_spec import CONFIGS
    from app.domain.schemas import ScenarioDraft, WorldSpec
    from app.providers.base import TextResponse
    from app.runtime.creator_projection import _propose_once
    from app.runtime.scenario_service import ScenarioService
    draft = ScenarioDraft(id="compiler-location", title="A generic facility", world=WorldSpec(locations="entry｜入口\nvault｜储藏室"))
    requested = {}

    async def text(role, **kwargs):
        requested.update(json.loads(kwargs["messages"][1]["content"]))
        result = {"summary": "仅进入储藏室才触发追逐", "mechanics": {
            k: {"enabled": k == "qte", "config": c().model_dump(), "tutorial": "按确认规则运行"} for k, c in CONFIGS.items()},
            "timed_event": {"id": "pursuit", "kind": "qte", "timeout_seconds": 10, "fallback": "绕路继续"}}
        result["mechanics"]["qte"]["config"]["trigger_location_ids"] = ["vault"]
        return None, SimpleNamespace(selected="offline-authoring"), TextResponse(content=json.dumps(result), model="offline")

    service = ScenarioService(SimpleNamespace(call_text=text))

    async def get(sid):
        return draft

    async def save(value):
        return value

    monkeypatch.setattr(service, "get", get)
    monkeypatch.setattr(service, "save_draft", save)
    proposal = asyncio.run(_propose_once(service, draft.id, "mechanics", "只有进入储藏室后才触发追逐"))
    assert requested["story"]["locations"] == {"entry": "入口", "vault": "储藏室"}
    qte = next(item for item in proposal["items"] if item["path"] == "mechanics.qte")
    assert qte["value"]["config"]["trigger_location_ids"] == ["vault"]
    assert "trigger_location_ids" in requested["rules"]


def test_timed_epoch_has_three_candidates_plus_one_declared_fallback(monkeypatch):
    from app.config import settings
    from app.domain.schemas import BranchSource
    engine, state = timed_state(location="vault")
    monkeypatch.setattr(settings, "target_k", 3)
    monkeypatch.setattr(settings, "shots_per_branch", 1)
    monkeypatch.setattr(settings, "developer_test_override_enabled", False)
    spawned = []

    async def candidates(*args):
        return [{"label": f"Action {index}", "summary": "Possible action", "confidence": .8} for index in range(3)]

    async def noop(*args):
        pass

    monkeypatch.setattr(engine, "candidate_actions", candidates)
    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_spawn_pipeline", lambda sid, bid: spawned.append(bid))
    asyncio.run(engine.prepare_recommendations(state))
    assert len(state.epoch.branch_ids) == state.epoch.k == 3
    assert len(spawned) == 4
    assert sum(branch.source == BranchSource.FALLBACK for branch in state.branches) == 1

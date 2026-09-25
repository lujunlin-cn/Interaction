"""Continue creates an Arc; only a subsequent player action starts new media."""
import asyncio
import json
from types import SimpleNamespace


def test_continue_preserves_world_without_auto_media_then_accepts_free_action(monkeypatch):
    from app.domain.schemas import Branch, BranchSource, BranchStatus, ProviderRouteRecord
    from app.providers.base import DecisionAnswer, TextResponse
    from app.runtime.engine import RuntimeEngine

    calls = {"authoring": 0, "prepare": 0, "intent": 0, "pipelines": []}
    route = ProviderRouteRecord(role="director", primary="offline", selected="offline", status="success")

    async def text(role, **kwargs):
        assert role == "authoring"
        calls["authoring"] += 1
        return None, route, TextResponse(content=json.dumps({"question": "如何安置获救的人？", "conflict": "补给有限"}))

    async def decision(**kwargs):
        calls["intent"] += 1
        return None, route, DecisionAnswer(details={"confidence": .95, "impact": "MEDIUM"})

    engine = RuntimeEngine(SimpleNamespace(call_text=text, call_decision=decision))
    state = engine._bootstrap("continuation-version", "continuation-story", {
        "title": "Generic continuation",
        "world": {"locations": "shelter｜避难处"},
        "drama": {"ending_families": "rescued｜救援完成"},
    })
    state.world.inventory = ["医疗箱"]
    state.world.relationships = {"partner": 72}
    state.world.knowledge = ["facility_evidence"]
    state.world.clues = {"facility_evidence": "VERIFIED"}
    state.world.truth = {"rescued": "幸存者已离开设施"}
    old_arc = state.current_arc()
    discarded = Branch(id="unselected", session_id=state.id, arc_id=old_arc.id,
                       source=BranchSource.RECOMMENDATION, label="没有发生的未来",
                       status=BranchStatus.READY, base_versions=engine._branch_base_versions(state))
    state.branches.append(discarded)
    engine._close_arc(state, "rescued")
    world_before = state.world.model_dump(mode="json")
    ending_before = old_arc.model_dump(mode="json")
    engine.sessions[state.id] = state

    async def noop(*args, **kwargs):
        pass

    async def prepare(*args):
        calls["prepare"] += 1

    async def director(*args, **kwargs):
        return {"outcome": {"mode": "FULL_BEAT", "title": "检查下一段路线"}}, route

    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_push", noop)
    monkeypatch.setattr(engine, "_safe_prepare", prepare)
    monkeypatch.setattr(engine, "_director_output", director)
    monkeypatch.setattr(engine, "_spawn_pipeline", lambda sid, bid: calls["pipelines"].append(bid))

    async def run():
        result = await engine.continue_world(state.id)
        await asyncio.sleep(0)  # Observe any accidental background scheduling.
        assert result == {"status": "CONTINUED", "arc": 2}
        assert calls == {"authoring": 1, "prepare": 0, "intent": 0, "pipelines": []}
        assert state.world.model_dump(mode="json") == world_before
        assert state.arcs[0].model_dump(mode="json") == ending_before
        assert state.arcs[0].status == "CLOSED"
        assert state.current_arc().seq == 2
        assert discarded.status == BranchStatus.READY
        assert state.player.status == "WAITING_DECISION"
        assert not engine.player_view(state)["action_pending"]
        assert engine.player_view(state)["recommendations"] == []

        action = await engine.free_action(state.id, "和同伴一起检查避难处附近的路线")
        assert action["status"] == "GENERATING"
        branch = state.branch(action["branch_id"])
        assert branch.arc_id == state.current_arc().id
        assert branch.source == BranchSource.FREE
        assert calls["intent"] == 1
        assert calls["pipelines"] == [branch.id]
        assert calls["prepare"] == 0
        assert state.world.model_dump(mode="json") == world_before

    asyncio.run(run())

"""生成等待期承接（问题6）：effects 兜底、player_view pending_* 字段、间奏追加。"""
import asyncio
import json
from types import SimpleNamespace


def _engine_and_state():
    from app.domain.schemas import ProviderRouteRecord
    from app.runtime.engine import RuntimeEngine

    route = ProviderRouteRecord(role="director", primary="offline",
                                selected="offline", status="success")

    async def noop(*args, **kwargs):
        pass

    engine = RuntimeEngine(SimpleNamespace(call_text=None, call_decision=None))
    state = engine._bootstrap("pending-fx-version", "pending-fx-story", {
        "title": "Pending effects",
        "world": {"locations": "shelter｜避难处"},
        "drama": {"ending_families": "rescued｜救援完成"},
    })
    engine.sessions[state.id] = state
    return engine, state, route, noop


def test_plan_branch_fallback_effects_and_player_view(monkeypatch):
    """Director 不给 effects 时 FULL_BEAT 兜底一句；player_view 透出 pending_*。"""
    from app.domain.schemas import Branch, BranchSource, BranchStatus

    engine, state, route, noop = _engine_and_state()
    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_push", noop)

    async def director(*args, **kwargs):
        return {"outcome": {"mode": "FULL_BEAT", "title": "检查路线",
                            "text": "你查看路线。", "effects": []},
                "directive": {}}, route

    branch = Branch(id="b1", session_id=state.id,
                    arc_id=state.current_arc().id,
                    source=BranchSource.FREE, label="检查避难处附近",
                    status=BranchStatus.PLANNING,
                    base_versions=engine._branch_base_versions(state))
    state.branches.append(branch)

    async def run():
        monkeypatch.setattr(engine, "_director_output", director)
        await engine._plan_branch(state, branch)
        assert branch.outcome is not None
        # FULL_BEAT + 空 effects → 兜底句
        assert branch.outcome.effects == ["你开始检查避难处附近。"]
        # player_view 透出
        state.pending_freeform_id = branch.id
        state.player.status = "GENERATING_NEXT"
        view = engine.player_view(state)
        assert view["pending_effects"] == ["你开始检查避难处附近。"]
        assert view["pending_phase"] == "PLANNING"
        assert view["pending_label"] == "检查避难处附近"
        assert view["action_pending"] is True

    asyncio.run(run())


def test_interstitial_appends_effects(monkeypatch):
    """_interstitial_effects 在 GENERATING 期间向 effects 追加间奏句。"""
    from app.domain.schemas import (Branch, BranchSource, BranchStatus,
                                    OutcomeSpec, ProviderRouteRecord)
    from app.providers.base import TextResponse
    from app.runtime.engine import RuntimeEngine

    engine, state, route, noop = _engine_and_state()
    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_push", noop)

    branch = Branch(id="b2", session_id=state.id,
                    arc_id=state.current_arc().id,
                    source=BranchSource.FREE, label="撬开门",
                    status=BranchStatus.GENERATING,
                    outcome=OutcomeSpec(title="撬门", text="...",
                                        effects=["你开始撬开门。"]),
                    base_versions=engine._branch_base_versions(state))
    state.branches.append(branch)

    async def text(role, **kwargs):
        assert role == "narrative"
        return None, route, TextResponse(
            content=json.dumps({"lines": ["门锁发出轻响。", "走廊尽头有脚步声靠近。"]}))

    engine.router = SimpleNamespace(call_text=text)

    async def run():
        await engine._interstitial_effects(state.id, branch.id)
        assert branch.outcome.effects[:1] == ["你开始撬开门。"]
        assert "门锁发出轻响。" in branch.outcome.effects
        assert "走廊尽头有脚步声靠近。" in branch.outcome.effects
        assert len(branch.outcome.effects) <= 6

    asyncio.run(run())


def test_interstitial_silent_on_failure_and_non_generating(monkeypatch):
    """间奏失败或非 GENERATING/ASSEMBLING 状态静默返回，不抛错不改 effects。"""
    from app.domain.schemas import (Branch, BranchSource, BranchStatus,
                                    OutcomeSpec)
    from app.runtime.engine import RuntimeEngine

    engine, state, route, noop = _engine_and_state()
    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_push", noop)

    # 分支已到 READY，间奏不应改动
    branch = Branch(id="b3", session_id=state.id,
                    arc_id=state.current_arc().id,
                    source=BranchSource.FREE, label="x",
                    status=BranchStatus.READY,
                    outcome=OutcomeSpec(title="t", text="x", effects=["e"]),
                    base_versions=engine._branch_base_versions(state))
    state.branches.append(branch)

    async def boom(role, **kwargs):
        raise RuntimeError("provider down")

    engine.router = SimpleNamespace(call_text=boom)

    async def run():
        await engine._interstitial_effects(state.id, branch.id)  # 不抛
        assert branch.outcome.effects == ["e"]

    asyncio.run(run())

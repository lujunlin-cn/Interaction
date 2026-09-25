import asyncio
from types import SimpleNamespace

from app.config import settings
from app.domain.schemas import Branch, BranchSource, BranchStatus, RecommendationEpoch
from app.runtime.engine import RuntimeEngine


def test_player_view_exposes_locked_jev_labels_before_media_ready():
    engine = RuntimeEngine(SimpleNamespace())
    state = engine._bootstrap("v", "s", {"world": {"locations": "hall｜大厅"}})
    state.player.status = "WAITING_DECISION"
    branches = []
    for i in range(3):
        branch = Branch(id=f"b{i}", session_id=state.id, arc_id=state.current_arc().id,
                        source=BranchSource.RECOMMENDATION, status=BranchStatus.PLANNING,
                        label=f"建议{i}", summary="可选方向",
                        base_versions=engine._branch_base_versions(state),
                        fingerprint=engine.compute_fingerprint(state))
        state.branches.append(branch)
        branches.append(branch.id)
    state.epoch = RecommendationEpoch(id="epoch", branch_ids=branches,
                                      options_exposed=True)
    view = engine.player_view(state)
    assert [x["label"] for x in view["recommendations"]] == ["建议0", "建议1", "建议2"]
    assert all(x["media_ready"] is False for x in view["recommendations"])


def test_player_view_exposes_options_while_pre_generation_is_still_running(monkeypatch):
    """Jev options are a decision result; H3 readiness must not gate them."""
    engine = RuntimeEngine(SimpleNamespace())
    state = engine._bootstrap("v", "s", {"world": {"locations": "hall｜大厅"}})
    state.player.status = "WAITING_DECISION"
    branch = Branch(
        id="planning", session_id=state.id, arc_id=state.current_arc().id,
        source=BranchSource.RECOMMENDATION, status=BranchStatus.PRODUCTION,
        label="先调查", summary="检查现场证据",
        base_versions=engine._branch_base_versions(state),
        fingerprint=engine.compute_fingerprint(state),
    )
    state.branches.append(branch)
    state.epoch = RecommendationEpoch(
        id="epoch", branch_ids=[branch.id], options_exposed=True,
    )
    monkeypatch.setattr(settings, "pre_generate_recommendation_media", True)
    view = engine.player_view(state)
    assert view["recommendations"] == [{
        "branch_id": "planning", "label": "先调查", "summary": "检查现场证据",
        "confidence": 0.0, "source": "recommendation", "media_ready": False,
    }]


def test_recommendation_media_setting_is_explicit():
    assert hasattr(settings, "pre_generate_recommendation_media")


def test_recommendation_pipeline_can_publish_before_h3(monkeypatch):
    engine = RuntimeEngine(SimpleNamespace())
    state = engine._bootstrap("v", "s", {"world": {"locations": "hall｜大厅"}})
    branch = Branch(id="deferred", session_id=state.id, arc_id=state.current_arc().id,
                    source=BranchSource.RECOMMENDATION, status=BranchStatus.PREDICTED,
                    label="调查", summary="调查现场",
                    base_versions=engine._branch_base_versions(state),
                    fingerprint=engine.compute_fingerprint(state))
    state.branches.append(branch)
    engine.sessions[state.id] = state
    async def noop(*args, **kwargs):
        return None
    async def plan(*args):
        branch.outcome = SimpleNamespace(title="调查", text="发现记录", evidence=[],
                                         ending=None, kind="investigation", ops=[])
        branch.packet = None
    async def narrate(*args):
        branch.narrative = "发现记录"
        branch.caption = "调查"
    async def shoot(*args):
        branch.shots = [SimpleNamespace(duration=5)]
    async def must_not_generate(*args):
        raise AssertionError("speculative H3 must not be submitted")
    monkeypatch.setattr(engine, "_persist", noop)
    monkeypatch.setattr(engine, "_push", noop)
    monkeypatch.setattr(engine, "_phase_sleep", noop)
    monkeypatch.setattr(engine, "_plan_branch", plan)
    monkeypatch.setattr(engine, "_narrate_branch", narrate)
    monkeypatch.setattr(engine, "_shoot_branch", shoot)
    monkeypatch.setattr(engine, "_generate_branch_media", must_not_generate)
    old = settings.pre_generate_recommendation_media
    settings.pre_generate_recommendation_media = False
    try:
        asyncio.run(engine._pipeline_inner(state.id, branch.id, False))
    finally:
        settings.pre_generate_recommendation_media = old
    assert branch.status == BranchStatus.READY
    assert branch.artifact and branch.artifact.quality_status == "DEFERRED"

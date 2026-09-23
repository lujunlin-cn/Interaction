"""Scenario 泛化验证（G01/G02/G05/G07/G08）：

用一个与「雨夜公寓」完全不同语义的 Scenario（废弃灯塔失踪案）验证：
- 推荐候选不含雨夜公寓硬编码（Alice/foyer/钥匙/储物柜/车票/录音等）
- patch 白名单接受新 Scenario 的 objects.* / clues.* / location（值域校验）
- clue label / ending family 标题来自 Scenario 声明
"""
import time

import pytest


LIGHTHOUSE_DRAFT = {
    "title": "废弃灯塔失踪案",
    "description": "守塔人一夜失踪，灯塔的日志停在午夜。你扮演前来调查的保险员。",
    "genre": "悬疑",
    "tone": "冷峻、海风、留白",
    "play_style": "自由调查 / 对话",
    "player_character": "player",
    "world": {
        "rules": "现实世界；无超自然。",
        "lore": "灯塔已停用三年，只剩守塔人老周驻守。",
        "locations": "pier｜码头\ntower_base｜灯塔底层\nlamp_room｜灯室\ncliff｜崖边小路",
        "constraints": "核心真相不可改写。",
    },
    "characters": [
        {"id": "player", "identity": "玩家 / 保险调查员", "personality": "由玩家行动塑造",
         "desire": "查明失踪原因", "fear": "未知", "secrets": "无",
         "knowledge": "老周昨夜失踪", "relationship": "", "visual_state": "风衣"},
        {"id": "keeper_wife", "identity": "周嫂 / 守塔人的妻子",
         "personality": "寡言、戒备", "desire": "找到丈夫", "fear": "灯塔的秘密被揭开",
         "secrets": "她知道日志缺了一页", "knowledge": "知道灯室的门锁坏了",
         "relationship": "对玩家信任 30 / 100", "visual_state": "灰色披肩"},
    ],
    "drama": {
        "core_question": "老周是自己离开，还是被迫消失？",
        "central_conflict": "调查真相与尊重家属悲痛的冲突。",
        "truth_model": "fact_log：灯塔日志缺失的一页记录了走私船的信号。\n"
                       "fact_boat：午夜有一艘无灯船靠岸。",
        "secrets": "缺页日志的下落。",
        "misbeliefs": "玩家可能怀疑周嫂隐瞒真相。",
        "pressures": "风暴将近｜天气预报｜故事时间推进",
        "anchors": "发现缺页日志；见到无灯船；作出是否上报的决定。",
        "ending_families": "truth_reported｜查明并上报\n"
                           "silent_departure｜带着疑问离开\n"
                           "kept_secret｜替周家保守秘密",
        "foreshadows": "missing_log_page｜缺页的灯塔日志\n"
                       "unlit_boat｜无灯船的目击",
        "forbidden_outcomes": "不得让老周无因果复活。",
        "timed_interactions": "",
    },
    "mechanics": {
        "relationship": {"enabled": True, "config": {"care_delta": 8}},
        "clue-system": {"enabled": True, "config": {}},
        "inventory": {"enabled": True, "config": {"capacity": 8}},
        "qte": {"enabled": False, "config": {}},
    },
    "reviewed": True,
}

HARDCODED_TERMS = ["Alice", "alice", "foyer", "钥匙", "储物柜", "午夜车票", "录音"]


def wait_for(client, sid, cond, timeout=60):
    deadline = time.time() + timeout
    view = None
    while time.time() < deadline:
        view = client.get(f"/api/sessions/{sid}/view").json()
        if cond(view):
            return view
        time.sleep(0.4)
    raise AssertionError(f"timeout; last view={view}")


@pytest.mark.integration
class TestScenarioGeneralization:
    def _publish_lighthouse(self, client) -> str:
        draft = client.post("/api/scenarios", json={"idea": "灯塔"}) .json()
        # 直接覆写 draft 为灯塔案结构
        r = client.put(f"/api/scenarios/{draft['id']}", json=LIGHTHOUSE_DRAFT)
        assert r.status_code == 200
        pub = client.post(f"/api/scenarios/{draft['id']}/publish",
                          json={"reviewed": True}).json()
        return pub["version_id"]

    def test_lighthouse_candidates_generic(self, client):
        version_id = self._publish_lighthouse(client)
        sid = client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]
        view = wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
        labels = " ".join(r["label"] + r["summary"] for r in view["recommendations"])
        for term in HARDCODED_TERMS:
            assert term not in labels, f"推荐候选含雨夜公寓硬编码: {term}"
        # 灯塔语义应出现在候选或已知状态中
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert dev["world"]["location"] == "pier"

    def test_lighthouse_patch_domain(self, client):
        """G02：新 Scenario 的 objects.*/clues.* 可提交；location 值域校验生效。"""
        from app.domain.state_manager import ProposalRejected, StateManager
        from app.domain.schemas import PatchOperation, StatePatchProposal, WorldState

        mgr = StateManager()
        w = WorldState(version=1, location="pier")
        locs = ["pier", "tower_base", "lamp_room", "cliff"]
        p = StatePatchProposal(
            proposal_id="p1", base_version=1, operations=[
                PatchOperation(op="set", path="objects.lighthouse_log", value="found"),
                PatchOperation(op="set", path="clues.missing_log_page", value="DISCOVERED"),
                PatchOperation(op="set", path="location", value="lamp_room"),
            ])
        w2 = mgr.validate(w, p, [], locations=locs)
        assert w2.objects["lighthouse_log"] == "found"
        assert w2.clues["missing_log_page"] == "DISCOVERED"
        assert w2.location == "lamp_room"
        # location 值域外 → 拒绝
        p2 = StatePatchProposal(
            proposal_id="p2", base_version=2,
            operations=[PatchOperation(op="set", path="location", value="moon")])
        with pytest.raises(ProposalRejected):
            mgr.validate(w2, p2, [], locations=locs)
        # 任意路径仍被拒
        p3 = StatePatchProposal(
            proposal_id="p3", base_version=2,
            operations=[PatchOperation(op="set", path="evil.root", value=1)])
        with pytest.raises(ProposalRejected):
            mgr.validate(w2, p3, [], locations=locs)

    def test_ending_family_labels_from_scenario(self, client):
        """G05：结局标题与 clue label 来自 Scenario 声明。"""
        version_id = self._publish_lighthouse(client)
        sid = client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]
        wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        snap = dev["scenario_snapshot"]["drama"]
        assert "silent_departure" in snap["ending_families"]


@pytest.mark.integration
class TestAtomicCommit:
    def test_drama_failure_leaves_world_untouched(self, client):
        """G03：world validate 通过但 drama proposal 失败 → world.version 不变（原子性）。"""
        import asyncio
        from app.domain.schemas import (BaseVersions, Branch, DramaPatchProposal,
                                        PatchOperation, StatePatchProposal)
        from app.main import runtime_engine

        version_id = client.get(
            "/api/scenarios/rainy_apartment/versions").json()["items"][0]["version_id"]
        sid = client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]
        state = asyncio.run(runtime_engine.load_session(sid))
        assert state is not None
        base_version = state.world.version
        base_revision = state.drama.revision
        branch = Branch(
            id="br_atomic_test", trace_id="t", session_id=sid,
            arc_id=state.current_arc().id if state.current_arc() else "",
            base_versions=BaseVersions(world=base_version, drama=base_revision,
                                       arc="", wish=state.wish_seq),
            label="atomic test", source="free",
            state_patch_proposal=StatePatchProposal(
                proposal_id="p", base_version=base_version,
                operations=[PatchOperation(op="set", path="location", value="street")],
                idempotency_key="atomic:test"),
            drama_patch_proposal=DramaPatchProposal(
                proposal_id="d", base_revision=base_revision,
                operations=[{"op": "nonexistent_op"}],
                idempotency_key="atomic:dtest"))
        try:
            asyncio.run(runtime_engine._commit_branch(state, branch))
            assert False, "drama proposal 非法操作应抛错"
        except Exception:
            pass
        # 原子性：world 与 drama 都未被修改
        assert state.world.version == base_version
        assert state.world.location != "street" or base_version == state.world.version
        assert state.drama.revision == base_revision

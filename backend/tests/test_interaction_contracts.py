"""交互契约回归测试（PRD 差距清单 A–M 的后端侧）。

覆盖：TIMED 限时互动（I02/I03/AT-23）、意图回显与确认（FR-046/AT-30）、
MERGED_TRANSITION（FR-048）、取消生成、Skill 禁用阻塞、Profile 切换（AT-56）、
ScenePacket 泄密拦截（FR-068/AT-48）、Scenario 复制/删除、素材 replace/remove、
全局角色库种子。
"""
from __future__ import annotations

import io
import time

import pytest


def wait_for(client, sid, cond, timeout=60):
    deadline = time.time() + timeout
    view = None
    while time.time() < deadline:
        view = client.get(f"/api/sessions/{sid}/view").json()
        if cond(view):
            return view
        time.sleep(0.3)
    raise AssertionError(f"timeout waiting for condition; last view={view}")


def new_session(client):
    version_id = client.get("/api/scenarios/rainy_apartment/versions") \
        .json()["items"][0]["version_id"]
    return client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]


def commit_first_rec(client, sid):
    view = wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
    bid = view["recommendations"][0]["branch_id"]
    response = client.post(f"/api/sessions/{sid}/select", json={"branch_id": bid})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANONICAL"
    client.post(f"/api/sessions/{sid}/player", json={"command": "skip"})
    client.post(f"/api/sessions/{sid}/receipt")


@pytest.mark.integration
class TestInteractionContracts:
    # ------------------------------------------------------------- FR-046
    def test_intent_echo_and_confirm(self, client):
        sid = new_session(client)
        commit_first_rec(client, sid)  # 推进一拍，避开开场
        r = client.post(f"/api/sessions/{sid}/action", json={"text": "我悄悄跟着她"})
        body = r.json()
        assert body["status"] == "INTENT_ECHO"
        echo = body["echo"]
        assert echo["raw_text"] == "我悄悄跟着她"
        assert "action" in echo and 0 < echo["confidence"] < 0.75
        # 视图里也能看到待确认意图（刷新页面后卡片区可恢复）
        view = client.get(f"/api/sessions/{sid}/view").json()
        assert view["pending_intent"]["raw_text"] == "我悄悄跟着她"
        # 玩家修改理解后确认
        r = client.post(f"/api/sessions/{sid}/intent/confirm",
                        json={"approved": True, "desire": "想确认她要去哪里"})
        assert r.json()["status"] == "GENERATING"
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        branch = next(b for b in dev["branches"] if b["source"] == "free")
        assert branch["intent"]["desire"] == "想确认她要去哪里"
        assert branch["intent"]["desire_source"] == "PLAYER_CONFIRMED"
        assert branch["intent"]["raw_text"] == "我悄悄跟着她"   # 原文保留

    def test_intent_reject(self, client):
        sid = new_session(client)
        r = client.post(f"/api/sessions/{sid}/action", json={"text": "我悄悄跟着她"})
        assert r.json()["status"] == "INTENT_ECHO"
        r = client.post(f"/api/sessions/{sid}/intent/confirm", json={"approved": False})
        assert r.json()["status"] == "CANCELLED"
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert not any(b["source"] == "free" for b in dev["branches"])
        assert dev["pending_intent"] is None

    def test_clarification_required(self, client):
        sid = new_session(client)
        r = client.post(f"/api/sessions/{sid}/action", json={"text": "彻底解决她"})
        body = r.json()
        assert body["status"] == "CLARIFICATION_REQUIRED"
        assert body["question"]
        # 可编辑澄清后照常生成
        r = client.post(f"/api/sessions/{sid}/intent/confirm",
                        json={"approved": True, "action": "把录音交给警方"})
        assert r.json()["status"] == "GENERATING"

    # ------------------------------------------------------------- FR-048
    def test_merged_transition(self, client):
        sid = new_session(client)
        for text in ("检查桌子", "检查柜子", "检查窗户"):
            r = client.post(f"/api/sessions/{sid}/action", json={"text": text})
            assert r.json()["status"] == "QUICK_ACK"
        assert r.json()["merged"] is True
        view = client.get(f"/api/sessions/{sid}/view").json()
        kinds = [m["kind"] for m in view["messages"]]
        assert "ack" in kinds and "merged" in kinds

    # ------------------------------------------------------------- I02/I03
    def test_timed_timeout_fallback(self, client):
        sid = new_session(client)
        commit_first_rec(client, sid)   # 完成一个关键行动后，下一批推荐触发限时节点
        view = wait_for(client, sid,
                        lambda v: v.get("timed") and v["timed"]["active"]
                        and v["timed"]["selection_open"], timeout=90)
        assert view["timed"]["fallback_hint"]
        assert view["timed"]["remaining_ms"] > 0
        # 不选择，等服务器倒计时兜底
        deadline = time.time() + 25
        fired = False
        while time.time() < deadline:
            dev = client.get(f"/api/dev/sessions/{sid}/state").json()
            if any(e["type"] == "timed_fallback_executed" for e in dev["events"]):
                fired = True
                break
            time.sleep(0.4)
        assert fired, "timed fallback not executed"
        view = client.get(f"/api/sessions/{sid}/view").json()
        assert not (view.get("timed") and view["timed"]["active"])
        assert view["player"]["scene_text"]

    def test_timed_select_cancels_countdown(self, client):
        sid = new_session(client)
        commit_first_rec(client, sid)
        view = wait_for(client, sid,
                        lambda v: v.get("timed") and v["timed"]["selection_open"]
                        and len(v["recommendations"]) >= 1, timeout=90)
        bid = view["recommendations"][0]["branch_id"]
        response = client.post(f"/api/sessions/{sid}/select", json={"branch_id": bid})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "CANONICAL"
        view = client.get(f"/api/sessions/{sid}/view").json()
        assert not (view.get("timed") and view["timed"]["active"])

    # ------------------------------------------------------------- 取消生成
    def test_cancel_generation(self, client):
        sid = new_session(client)
        # 开场推荐在后台生成：立刻取消
        r = client.post(f"/api/sessions/{sid}/cancel")
        assert r.json()["status"] in ("CANCELLED", "NOTHING_TO_CANCEL")
        if r.json()["status"] == "CANCELLED":
            dev = client.get(f"/api/dev/sessions/{sid}/state").json()
            assert any(b["status"] == "CANCELLED" for b in dev["branches"])
        # 取消后系统会重新准备推荐，会话可继续
        view = wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1, timeout=90)
        assert view["recommendations"]

    # ------------------------------------------------------------- Skill 开关
    def test_skill_disable_blocks_generation(self, client):
        sid = new_session(client)
        wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
        r = client.post("/api/skills/h3-production/toggle", json={"enabled": False})
        assert r.status_code == 200
        try:
            client.post(f"/api/sessions/{sid}/action", json={"text": "我绕到后院去看看"})
            deadline = time.time() + 30
            failed = False
            while time.time() < deadline:
                dev = client.get(f"/api/dev/sessions/{sid}/state").json()
                if any(b["source"] == "free" and b["status"] == "FAILED"
                       and "阻塞" in (b.get("last_error") or "") for b in dev["branches"]):
                    failed = True
                    break
                time.sleep(0.4)
            assert failed, "禁用 h3-production 后生成未被阻塞"
        finally:
            client.post("/api/skills/h3-production/toggle", json={"enabled": True})

    # ------------------------------------------------------------- Profile
    def test_profile_switch(self, client, monkeypatch):
        from app.main import provider_router

        async def unavailable():
            return False

        monkeypatch.setattr(provider_router.registry["sol_h3_local"], "health", unavailable)
        r = client.get("/api/dev/profile")
        assert r.json()["profile"] == "AGENT_LOCAL_PROFILE"
        assert r.json()["state"] == "ACTIVE"
        # 显式模拟 Sol-H3 不健康，验证健康检查失败后的回滚（AT-56）。
        r = client.post("/api/dev/profile/switch",
                        json={"target": "VIDEO_LOCAL_PROFILE"})
        body = r.json()
        assert body["ok"] is False and body["restored"] is True
        assert "sol_h3_local" in body["failed_health"]
        assert client.get("/api/dev/profile").json()["profile"] == "AGENT_LOCAL_PROFILE"
        # 同 Profile 切换是幂等 no-op
        r = client.post("/api/dev/profile/switch",
                        json={"target": "AGENT_LOCAL_PROFILE"})
        assert r.json()["ok"] is True

    # ------------------------------------------------------------- FR-068
    def test_narrative_leak_rejected(self, client):
        client.post("/api/dev/fixtures", json={"key": "leak_secret", "value": True})
        try:
            sid = new_session(client)
            deadline = time.time() + 40
            blocked = False
            while time.time() < deadline:
                dev = client.get(f"/api/dev/sessions/{sid}/state").json()
                if any(e["type"] == "narrative_blocked" for e in dev["events"]):
                    blocked = True
                    break
                time.sleep(0.5)
            assert blocked, "泄密叙事未被拦截"
            dev = client.get(f"/api/dev/sessions/{sid}/state").json()
            # 所有泄密分支都应失败，不允许 READY
            assert not any("举报" in (b.get("narrative") or "") and b["status"] == "READY"
                           for b in dev["branches"])
        finally:
            client.post("/api/dev/fixtures", json={"key": "leak_secret", "value": False})

    # ------------------------------------------------------------- Scenario 管理
    def test_scenario_duplicate_and_delete(self, client):
        clone = client.post("/api/scenarios/rainy_apartment/duplicate").json()
        assert clone["id"] != "rainy_apartment"
        assert clone["title"].endswith("（副本）")
        assert clone["status"] == "DRAFT"
        assert client.delete(f"/api/scenarios/{clone['id']}").json()["ok"]
        assert client.get(f"/api/scenarios/{clone['id']}").status_code == 404

    # ------------------------------------------------------------- 素材链
    def test_asset_replace_and_remove(self, client):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        r = client.post("/api/scenarios/rainy_apartment/assets",
                        files={"file": ("alice_ref.png", io.BytesIO(png), "image/png")},
                        data={"role": "identity", "entity": "alice"})
        asset = r.json()
        assert asset["id"]
        r = client.put(f"/api/scenarios/rainy_apartment/assets/{asset['id']}",
                       files={"file": ("alice_ref_v2.png", io.BytesIO(png), "image/png")})
        assert r.json()["version"] == 2
        r = client.delete(f"/api/scenarios/rainy_apartment/assets/{asset['id']}")
        assert r.json()["ok"]
        items = client.get("/api/scenarios/rainy_apartment/assets").json()["items"]
        assert not any(a["id"] == asset["id"] for a in items)

    # ------------------------------------------------------------- 角色库种子
    def test_global_character_seeded(self, client):
        items = client.get("/api/characters").json()["items"]
        alice = next((c for c in items if c["id"] == "chr_alice"), None)
        assert alice is not None
        assert "Alice" in alice["name"]

    # ------------------------------------------------------------- 视图增强
    def test_player_view_enriched(self, client):
        sid = new_session(client)
        view = wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
        assert view["scenario"]["title"] == "雨夜公寓"
        assert view["arc"]["seq"] == 1
        assert "lead" in view["player"]
        assert "known" in view and "relationships" in view["known"]
        assert isinstance(view["hint_chips"], list) and view["hint_chips"]
        assert isinstance(view["messages"], list)

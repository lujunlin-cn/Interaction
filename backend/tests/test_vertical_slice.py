"""端到端集成测试：Vertical Slice（推荐→选择→提交→自由输入→结局→续杯）。

使用 SQLite + Mock Provider（Mock 只替换 Provider，不替换业务 Runtime）。
client fixture 见 conftest.py（session 级共享）。
"""
import time

import pytest


def wait_for(client, sid, cond, timeout=60):
    deadline = time.time() + timeout
    view = None
    while time.time() < deadline:
        view = client.get(f"/api/sessions/{sid}/view").json()
        if cond(view):
            return view
        time.sleep(0.4)
    raise AssertionError(f"timeout waiting for condition; last view={view}")


@pytest.mark.integration
class TestVerticalSlice:
    def test_full_flow(self, client):
        # 种子与发布版本
        scenarios = client.get("/api/scenarios").json()["items"]
        rainy = next(s for s in scenarios if s["id"] == "rainy_apartment")
        assert rainy["status"] == "PUBLISHED"
        version_id = client.get("/api/scenarios/rainy_apartment/versions").json()["items"][0]["version_id"]

        # 创建会话 → 推荐就绪（I05：只显示 READY）
        sid = client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]
        view = wait_for(client, sid, lambda v: len(v["recommendations"]) >= 1)
        recs = view["recommendations"]
        assert 1 <= len(recs) <= 3
        for r in recs:
            assert r["label"] and r["summary"]

        # 选择 → CANONICAL → 播放
        bid = recs[0]["branch_id"]
        assert client.post(f"/api/sessions/{sid}/select",
                           json={"branch_id": bid}).json()["status"] == "CANONICAL"
        view = client.get(f"/api/sessions/{sid}/view").json()
        assert view["player"]["status"] in ("PLAYING", "READY")
        assert view["player"]["video_url"].startswith("/media/scenes/")

        # 重复选择已消费的分支应失败（已 INVALIDATED/CANONICAL）
        r = client.post(f"/api/sessions/{sid}/select", json={"branch_id": bid})
        assert r.status_code == 409

        # 播放完成 + receipt
        client.post(f"/api/sessions/{sid}/player", json={"command": "skip"})
        assert client.post(f"/api/sessions/{sid}/receipt").json()["ok"]

        # 自由输入：QUICK_ACK
        r = client.post(f"/api/sessions/{sid}/action", json={"text": "检查桌子"})
        assert r.json()["status"] == "QUICK_ACK"

        # 自由输入：完整分支（自动播放）
        r = client.post(f"/api/sessions/{sid}/action",
                        json={"text": "我绕到后院去看看"})
        assert r.json()["status"] == "GENERATING"
        view = wait_for(client, sid,
                        lambda v: "后院" in (v["player"]["scene_text"] or ""))
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert dev["world"]["location"] == "backyard"

        # 自由输入：不可能的尝试 → QUICK_ACK 且状态不被污染
        v_before = dev["world"]["version"]
        r = client.post(f"/api/sessions/{sid}/action", json={"text": "我用激光炮打开后门"})
        assert r.json()["status"] == "QUICK_ACK"
        dev2 = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert dev2["world"]["location"] == "backyard"
        assert dev2["world"]["version"] == v_before

        # 结局 → 续杯
        client.post(f"/api/sessions/{sid}/player", json={"command": "skip"})
        client.post(f"/api/sessions/{sid}/receipt")
        r = client.post(f"/api/sessions/{sid}/action",
                        json={"text": "我决定离城，不再参与这场矛盾"})
        assert r.json()["status"] == "GENERATING"
        view = wait_for(client, sid, lambda v: v["ended"], timeout=90)
        assert view["ended"]
        r = client.post(f"/api/sessions/{sid}/continue")
        assert r.json()["status"] == "CONTINUED"
        view = wait_for(client, sid, lambda v: not v["ended"])
        dev3 = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert len(dev3["arcs"]) == 2

    def test_wish_lifecycle(self, client):
        version_id = client.get("/api/scenarios/rainy_apartment/versions").json()["items"][0]["version_id"]
        sid = client.post("/api/sessions", json={"version_id": version_id}).json()["session_id"]
        w = client.post(f"/api/sessions/{sid}/wishes",
                        json={"text": "希望 Alice 平安"}).json()
        assert w["status"] == "ACTIVE"
        client.delete(f"/api/sessions/{sid}/wishes/{w['id']}")
        dev = client.get(f"/api/dev/sessions/{sid}/state").json()
        assert dev["wishes"][0]["status"] == "WITHDRAWN"

    def test_scenario_authoring_and_publish(self, client):
        draft = client.post("/api/scenarios",
                            json={"idea": "一座灯塔里的失踪案"}).json()
        assert draft["title"]
        assert draft["drama"]["truth_model"]
        r = client.post(f"/api/scenarios/{draft['id']}/publish").json()
        assert r["version_id"]
        versions = client.get(f"/api/scenarios/{draft['id']}/versions").json()["items"]
        assert len(versions) == 1

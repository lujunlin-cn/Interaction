"""Authoring pressure contract: deterministic, no database or external provider."""
import json
from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.domain.schemas import ScenarioDraft
from app.runtime.scenario_service import ScenarioService, _row_to_draft


CANONICAL = "封锁逼近｜安全系统逐步断电｜故事时间推进"
STRUCTURED = [{"name": "封锁逼近", "source": "安全系统逐步断电", "trigger_type": "故事时间推进"}]


@pytest.mark.parametrize("value", [STRUCTURED, STRUCTURED[0], json.dumps(STRUCTURED),
    {"pressures": STRUCTURED}, {"封锁逼近": {"source": "安全系统逐步断电", "driver": "FICTION_TIME"}},
    "封锁逼近|安全系统逐步断电|FICTION_TIME"])
def test_patch_normalizes_identifiable_representations(value):
    candidate = ScenarioService.validate_patch(ScenarioDraft(id="s"), "drama.pressures", value)
    assert candidate.drama.pressures == CANONICAL


def test_misordered_columns_retain_source_and_consequence():
    value = "供电恶化｜设施损毁与故事时间推进｜安全门与系统权限随电力减少而失效"
    candidate = ScenarioService.validate_patch(ScenarioDraft(id="s"), "drama.pressures", value)
    assert candidate.drama.pressures == "供电恶化｜设施损毁与故事时间推进；安全门与系统权限随电力减少而失效｜故事时间推进"


@pytest.mark.parametrize("value", [
    "危机｜天气恶化｜路线关闭", "危机｜未知｜倒计时", "危机｜行动触发和故事时间推进｜失去路线",
    [{"name": "危机", "source": "天气", "trigger_type": "REAL_TIME"}],
    "危机｜非行动触发｜道路关闭", "危机｜天气｜不是故事时间推进",
    "危机｜故事时间推进｜行动触发",
    [{"name": "危机", "source": "天气", "trigger_type": "ACTION", "unsupported": "不能悄悄丢弃"}],
])
def test_ambiguous_pressure_is_rejected(value):
    with pytest.raises(ValueError):
        ScenarioService.validate_patch(ScenarioDraft(id="s"), "drama.pressures", value)


def test_existing_valid_seed_and_empty_draft_remain_valid():
    from app.seed.rainy_apartment import rainy_apartment
    d = rainy_apartment()
    assert ScenarioService.validate_patch(d, "drama.pressures", d.drama.pressures).drama.pressures == d.drama.pressures
    assert ScenarioService.validate_patch(ScenarioDraft(id="s"), "drama.pressures", "").drama.pressures == ""


def test_read_repairs_json_without_mutating_persisted_row():
    raw = ScenarioDraft(id="s").model_dump(mode="json")
    raw["drama"]["pressures"] = json.dumps(STRUCTURED)
    row = SimpleNamespace(draft=raw)
    assert _row_to_draft(row).drama.pressures == CANONICAL
    assert row.draft["drama"]["pressures"].startswith("[")


def test_invalid_legacy_draft_stays_readable_but_cannot_publish():
    d = ScenarioDraft(id="s", drama={"pressures": "旧的含糊压力"})
    assert _row_to_draft(SimpleNamespace(draft=d.model_dump())).drama.pressures == "旧的含糊压力"
    check = next(c for c in ScenarioService(None).publish_checklist(d) if c["id"] == "pressures")
    assert not check["ok"]


@pytest.mark.asyncio
async def test_invalid_pressure_save_rejected_before_database():
    with pytest.raises(ValueError, match="压力"):
        await ScenarioService(None).save_draft(ScenarioDraft(id="s", drama={"pressures": "未知格式"}))


class MemoryService(ScenarioService):
    def __init__(self, responses):
        self.calls = 0
        self.draft = ScenarioDraft(id="s", title="原题", drama={"pressures": CANONICAL})
        self.saves = 0
        async def call_text(*args, **kwargs):
            result = responses[min(self.calls, len(responses) - 1)]
            self.calls += 1
            return None, SimpleNamespace(selected="test"), SimpleNamespace(content=json.dumps(result, ensure_ascii=False), model="test", latency_ms=0)
        super().__init__(SimpleNamespace(call_text=call_text))

    async def get(self, scenario_id):
        return self.draft.model_copy(deep=True)

    async def save_draft(self, draft):
        self.saves += 1
        self.draft = draft.model_copy(deep=True)
        return draft


@pytest.mark.asyncio
async def test_instruction_repairs_once_without_partial_mutation():
    service = MemoryService([
        {"patches": [{"path": "title", "after": "不应部分保存"}, {"path": "drama.pressures", "after": "危机｜暴雨｜道路封闭"}]},
        {"patches": [{"path": "drama.pressures", "after": json.dumps(STRUCTURED)}]},
    ])
    result = await service.apply_instruction("s", "规范压力格式")
    assert service.calls == 2
    assert result.title == "原题"
    assert result.drama.pressures == CANONICAL
    assert result.changes[-1]["after"] == CANONICAL
    assert service.saves == 1


@pytest.mark.asyncio
async def test_instruction_stops_after_one_failed_schema_retry():
    service = MemoryService([{"patches": [{"path": "drama.pressures", "after": "危机｜天气｜道路关闭"}]}])
    with pytest.raises(ValueError):
        await service.apply_instruction("s", "规范压力格式")
    assert service.calls == 2
    assert service.saves == 0
    assert service.draft.drama.pressures == CANONICAL


@pytest.mark.asyncio
async def test_projection_and_accept_store_normalized_value():
    from app.runtime.creator_projection import propose, accept
    service = MemoryService([{"summary": "压力理解", "items": [{"path": "drama.pressures", "summary": "安全系统逐步断电", "value": STRUCTURED}]}])
    proposal = await propose(service, "s", "drama")
    assert proposal["items"][0]["value"] == CANONICAL
    result = await accept(service, "s", proposal["id"], {"drama.pressures": json.dumps(STRUCTURED)})
    assert result.drama.pressures == CANONICAL
    assert result.changes[-1]["after"] == CANONICAL


@pytest.mark.asyncio
async def test_projection_ambiguous_pressure_triggers_one_repair():
    from app.runtime.creator_projection import propose
    service = MemoryService([
        {"summary": "压力理解", "items": [{"path": "drama.pressures", "summary": "错误", "value": "危机｜天气｜道路关闭"}]},
        {"summary": "压力理解", "items": [{"path": "drama.pressures", "summary": "修复", "value": STRUCTURED}]},
    ])
    proposal = await propose(service, "s", "drama")
    assert service.calls == 2
    assert proposal["items"][0]["value"] == CANONICAL


@pytest.mark.asyncio
async def test_initial_draft_uses_same_pressure_contract():
    content = ScenarioDraft(id="discard", title="新故事", description="调查封锁", player_character="p",
        world={"rules": "事实保持", "locations": "start｜入口"}, characters=[{"id": "p", "identity": "玩家"}],
        drama={"core_question": "能否找到出路", "truth_model": "fact_1：门已关闭", "pressures": CANONICAL, "ending_families": "escape｜逃离"}).model_dump(mode="json")
    content["drama"]["pressures"] = STRUCTURED
    service = MemoryService([content])
    result = await service.create_from_idea("调查地下设施")
    assert result.drama.pressures == CANONICAL
    assert service.calls == 1


def test_legacy_projection_values_and_stale_before_are_normalized_together():
    raw = ScenarioDraft(id="s").model_dump(mode="json")
    raw["drama"]["pressures"] = json.dumps(STRUCTURED)
    raw["creator_projection"] = {"drama:": {"items": [{"path": "drama.pressures", "before": json.dumps(STRUCTURED), "value": STRUCTURED, "suggestions": [{"value": STRUCTURED}]}]}}
    loaded = _row_to_draft(SimpleNamespace(draft=raw))
    item = loaded.creator_projection["drama:"]["items"][0]
    assert loaded.drama.pressures == item["before"] == item["value"] == item["suggestions"][0]["value"] == CANONICAL


def test_normalized_read_is_idempotent_and_does_not_change_revision():
    raw = ScenarioDraft(id="s", updated_at=42).model_dump(mode="json")
    raw["drama"]["pressures"] = json.dumps(STRUCTURED)
    first = _row_to_draft(SimpleNamespace(draft=raw)).model_dump(mode="json")
    second = _row_to_draft(SimpleNamespace(draft=first)).model_dump(mode="json")
    assert first == second
    assert first["updated_at"] == 42


@pytest.mark.asyncio
async def test_save_and_instruct_route_natural_errors_without_database(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api import routes
    memory = MemoryService([{"patches": [{"path": "drama.pressures", "after": "危机｜来源｜结果"}]}])
    monkeypatch.setattr(routes, "ScenarioService", lambda _: memory)
    application = FastAPI()
    application.include_router(routes.build_api(SimpleNamespace(), SimpleNamespace()))
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        draft = memory.draft.model_dump(mode="json")
        draft["drama"]["pressures"] = "危机｜来源｜结果"
        response = await client.put("/api/scenarios/s", json=draft)
        assert response.status_code == 422
        assert "压力" in response.json()["detail"]
        response = await client.post("/api/scenarios/s/instruct", json={"instruction": "修正格式"})
        assert response.status_code == 422
        assert "触发" in response.json()["detail"]
        assert "pydantic" not in response.text.lower()
    assert memory.saves == 0

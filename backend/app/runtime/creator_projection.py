"""AI authoring projections: proposals are persisted separately and explicitly accepted.
The existing ScenarioDraft remains the only runtime definition.
"""
from __future__ import annotations
import json
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from ..domain.schemas import now_ms
from ..domain.ids import uid
from ..domain.mechanic_spec import CONFIGS, validate_mechanics
from .tracer import tracer
from .structured_output import decode_object

class Suggestion(BaseModel):
    label: str
    value: Any

class Understanding(BaseModel):
    path: str
    summary: str
    value: Any
    question: str = ""
    evidence_quote: str = ""
    suggestions: list[Suggestion] = Field(default_factory=list)

class Projection(BaseModel):
    summary: str
    items: list[Understanding] = Field(min_length=1)

DRAMA_PATHS = ["drama." + x for x in (
    "core_question", "central_conflict", "truth_model", "secrets", "misbeliefs",
    "pressures", "anchors", "ending_families", "forbidden_outcomes", "foreshadows", "timed_interactions")]
CHAR_FIELDS = ("identity", "personality", "desire", "fear", "secrets", "knowledge", "relationship", "visual_state")

def allowed_paths(draft, scope, character_id):
    if scope == "drama":
        return DRAMA_PATHS
    if scope == "mechanics":
        return ["mechanics." + k for k in CONFIGS] + ["drama.timed_interactions"]
    if scope == "character":
        index = next((i for i, c in enumerate(draft.characters) if c.id == character_id), None)
        if index is None:
            raise ValueError("请先选择故事角色")
        return [f"characters[{index}].{k}" for k in CHAR_FIELDS]
    raise ValueError("未知创作模块")

async def propose(service, scenario_id, scope, instruction="", character_id=""):
    try:
        return await _propose_once(service, scenario_id, scope, instruction, character_id)
    except (ValueError, TypeError, KeyError) as error:
        await tracer.emit("authoring.projection_schema", "failed", input_={"scenario_id": scenario_id, "scope": scope}, output={"error": str(error), "attempt": 1})
        return await _propose_once(service, scenario_id, scope, instruction, character_id,
                                   "上次输出校验失败，请完整输出 summary 和非空 items 数组。仅修复格式：" + str(error))

async def _propose_once(service, scenario_id, scope, instruction="", character_id="", retry_hint=""):

    draft = await service.get(scenario_id)
    if draft is None:
        raise KeyError(scenario_id)
    paths = allowed_paths(draft, scope, character_id)
    schemas = {k: v.model_json_schema() for k, v in CONFIGS.items()}
    prompt = {
        "task": "帮助创作者深化故事，输出 JSON。所有 summary/label/question 必须是自然中文，不含字段名、ID、DSL。",
        "scope": scope, "instruction": instruction, "schema_retry": retry_hint,
        "original_story": draft.authoring_intent or draft.description,
        "draft": draft.model_dump(exclude={"changes", "creator_projection"}),
        "allowed_paths": paths, "output_schema": Projection.model_json_schema(),
        "rules": [
            "先给当前理解。只对原始描述和人工确认均未明确的高影响内容提问，最多三个问题。",
            "原文已经明确的真相、冲突、压力不重复提问；evidence_quote 必须逐字摘自 original_story/instruction。",
            "每个待确认问题给出3到4个与本故事人物地点相关的具体方案，每个方案有 label 和对应 typed value。",
            "其余条目作为可接受/修改/删除的当前理解。不能创建白名单以外的路径，不得修改 locks。",
            "drama 值都是字符串，truth_model 每行 fact_key：事实；pressures 名称｜来源｜行动触发/故事时间推进；ending_families id｜描述。",
            "角色值都是自然语言字符串，未说明的动机不当成已确认事实。",
            "mechanics 值为 {enabled:bool, config:{...}, tutorial:中文}；使用下方 config schema。",
            "四种玩法都明确 enabled；不要的设为 false。skill/version/trigger/permissions 由服务端绑定。",
            "启用 qte 时提供 drama.timed_interactions: id｜qte｜秒｜自然语言超时结果（使用已经建立的危险，不能凭空改真相）。",
        ], "mechanic_config_schemas": schemas if scope == "mechanics" else {},
    }
    if scope == "mechanics":
        # A narrow compiler result avoids asking the model to construct UI paths
        # or legacy timed DSL. The adapter below projects validated typed data.
        prompt = {
            "task": "为当前故事编译玩法提案。仅返回 JSON，所有四个已安装玩法都给出 enabled/config/tutorial。不要额外字段。tutorial 60字内，只描述实际支持的行为，不许声称永久记忆、组合物品等没有的能力。",
            "story": {"title": draft.title, "description": draft.description, "characters": [c.identity for c in draft.characters]},
            "intent": instruction, "schema_retry": retry_hint,
            "output_example": {"summary": "对玩法的中文理解", "mechanics": {
                k: {"enabled": False, "config": c().model_dump(), "tutorial": "按故事语境写具体玩法教程"}
                for k, c in CONFIGS.items()},
                "timed_event": {"id": "urgent_choice", "kind": "qte", "timeout_seconds": 10, "fallback": "没有及时选择，错过眼前的机会"}},
            "rules": "config 只能用示例里的键及类型。relationship 增减信任，clue-system 调查和核实线索，inventory 保存物品，qte 限时选择。不要发明技能或配置键。没有道具需求则关闭 inventory。启用 qte 必须给 timed_event；kind 必须是 qte 或 urgent_dialogue，timeout_seconds 在1到120之间。其余时候 timed_event=null。不要改变已确认的故事事实。"
        }
    _, rec, resp = await service.router.call_text("authoring", messages=[
        {"role": "system", "content": "你是故事创作助手。严格按输出 schema 返回 JSON，不要 Markdown。"},
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)}],
        output_contract={"purpose": "mechanic_projection" if scope == "mechanics" else "creator_projection"}, budget={"max_tokens": 8192, "reasoning_effort": "low"})
    content = decode_object(resp.content)
    if scope == "mechanics":
        from ..domain.mechanic_spec import CONTRACTS
        mechanics = validate_mechanics(content.get("mechanics") or {})
        if set(mechanics) != set(CONFIGS):
            raise ValueError("mechanics 必须包含 relationship/clue-system/inventory/qte 四项，未启用的设 enabled=false")
        items = [{"path": "mechanics." + k, "summary": m.tutorial,
                  "value": m.model_dump()} for k, m in mechanics.items()]
        event = content.get("timed_event")
        if mechanics["qte"].enabled:
            if not isinstance(event, dict) or event.get("kind") not in ("qte", "urgent_dialogue") or not isinstance(event.get("timeout_seconds"), int) or not 1 <= event["timeout_seconds"] <= 120 or not str(event.get("fallback", "")).strip():
                raise ValueError("timed_event 需要 id、kind=qte 或 urgent_dialogue、timeout_seconds=1..120、fallback=中文超时结果")
            event_id = str(event.get("id", "urgent_choice"))
            if "｜" in event_id or "\n" in event_id or "｜" in str(event["fallback"]) or "\n" in str(event["fallback"]):
                raise ValueError("限时事件标识和结果必须是单行文字")
            items.append({"path": "drama.timed_interactions", "summary": f"{event['timeout_seconds']} 秒内决定；超时：{event['fallback']}",
                          "value": f"{event_id}｜{event['kind']}｜{event['timeout_seconds']}｜{event['fallback']}"})
        content = {"summary": content.get("summary", ""), "items": items}
    projection = Projection.model_validate(content)
    original = (draft.authoring_intent or draft.description) + "\n" + instruction
    items = []
    seen = set()
    for item in projection.items:
        if item.path not in paths or item.path in seen:
            raise ValueError("AI 建议包含不允许或重复的字段")
        seen.add(item.path)
        # Explicit source and already-confirmed fields never become a question again.
        confirmed = any(c.get("path") == item.path and c.get("source") in ("manual", "confirmed_ai") for c in draft.changes)
        if (item.evidence_quote and item.evidence_quote in original) or confirmed:
            item.question = ""
        if item.question and not 3 <= len(item.suggestions) <= 4:
            raise ValueError("AI 追问需要三个到四个具体建议，请重试")
        for value in [item.value] + [s.value for s in item.suggestions]:
            service.validate_patch(draft, item.path, value)
        items.append({**item.model_dump(), "before": service._get_path(draft, item.path)})
    if scope == "mechanics":
        values = {item["path"]: item["value"] for item in items}
        if values.get("mechanics.qte", {}).get("enabled") and not values.get("drama.timed_interactions", draft.drama.timed_interactions).strip():
            raise ValueError("启用紧张时刻必须同时提供非空的 drama.timed_interactions：id｜qte｜秒｜超时结果。")
    key = f"{scope}:{character_id}"
    saved = {"id": uid("projection"), "summary": projection.summary, "items": items,
             "scope": scope, "character_id": character_id, "instruction": instruction,
             "provider": rec.selected, "model": resp.model, "created_at": now_ms(),
             "accepted": []}
    latest = await service.get(scenario_id)
    if latest is None:
        raise KeyError(scenario_id)
    latest.creator_projection[key] = saved
    await service.save_draft(latest)
    await tracer.emit("authoring.projection", "success", input_={"scenario_id": draft.id, "scope": scope},
                      output=saved, provider=rec.selected or "", model=resp.model,
                      skill_id="scenario-authoring", skill_version="1.0.0")
    return saved

async def accept(service, scenario_id, projection_id, answers):
    draft = await service.get(scenario_id)
    if draft is None:
        raise KeyError(scenario_id)
    projection = next((p for p in draft.creator_projection.values() if p.get("id") == projection_id), None)
    if not projection:
        raise ValueError("建议已更新，请重新打开当前理解")
    items = {i["path"]: i for i in projection["items"]}
    patches = []
    for path, value in answers.items():
        if any(path == lock or path.startswith(lock + ".") or path.startswith(lock + "[") for lock in draft.locks):
            raise ValueError("这项内容已锁定，未应用修改。")
        if path not in items:
            raise ValueError("无法应用不属于本次建议的字段")
        if path in projection["accepted"]:
            continue
        if service._get_path(draft, path) != items[path]["before"]:
            raise ValueError("内容已被修改，请重新生成建议")
        service.validate_patch(draft, path, value)
        patches.append({"path": path, "after": value, "reason": "用户确认 AI 当前理解"})
    applied = service._apply_typed_patch(draft, patches, "confirmed_ai")
    for change in applied:
        item = items[change["path"]]
        item["value"] = change["after"]
        item["summary"] = next((s["label"] for s in item.get("suggestions", []) if s["value"] == change["after"]), str(change["after"]) if isinstance(change["after"], str) else change["after"].get("tutorial", item["summary"]))
    projection["accepted"].extend(c["path"] for c in applied)
    if projection["scope"] == "mechanics" and draft.mechanics.get("qte") and draft.mechanics["qte"].enabled and not draft.drama.timed_interactions.strip():
        raise ValueError("请同时确认紧张时刻的限时事件与超时结果。")
    if projection["scope"] == "mechanics" and applied:
        draft.mechanic_authoring_intent = projection["instruction"]
    await service.save_draft(draft)
    await tracer.emit("authoring.confirm", "success", input_={"projection_id": projection_id},
                      output={"changes": applied}, provider="runtime",
                      skill_id="scenario-authoring", skill_version="1.0.0")
    return draft

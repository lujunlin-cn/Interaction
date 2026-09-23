"""Skills 注册表：平台 Skills + 玩法机制。

原则（PRD Q23）：Skills 只产生 Proposal，不直接改 Canonical State；
每次调用都可在 Inspector 审计（skill_id / version / 输入 / 输出）。
"""
from __future__ import annotations

from typing import Any

PLATFORM_SKILLS: list[dict[str, Any]] = [
    {
        "id": "scenario-authoring", "version": "1.0.0", "kind": "platform",
        "title": "Scenario Authoring",
        "description": "从创作想法生成完整 Scenario 草案，或对已有草案应用自然语言修改。",
        "produces": ["ScenarioDraft", "draft_patch"],
        "writes_state": False,
        "used_by": ["Creator"],
    },
    {
        "id": "intent-reconciliation", "version": "1.0.0", "kind": "platform",
        "title": "Intent Reconciliation",
        "description": "调和玩家输入、愿望与戏剧目标，产出 ResolvedIntent 与澄清请求。",
        "produces": ["ResolvedIntent"],
        "writes_state": False,
        "used_by": ["Director"],
    },
    {
        "id": "visual-continuity", "version": "1.0.0", "kind": "platform",
        "title": "Visual Continuity",
        "description": "维护角色/场景视觉连续性：参考图选择、形象状态描述、镜头提示约束。",
        "produces": ["ShotPlan.references", "visual_state_patch_proposal"],
        "writes_state": False,
        "used_by": ["Production"],
    },
    {
        "id": "h3-production", "version": "1.0.0", "kind": "platform",
        "title": "H3 Production",
        "description": "把 ShotPlan 转成视频 Provider 请求，并跟踪 GenerationJob 状态。",
        "produces": ["GenerationJob"],
        "writes_state": False,
        "used_by": ["Production"],
    },
    {
        "id": "video-assembly", "version": "1.0.0", "kind": "platform",
        "title": "Video Assembly",
        "description": "确定性装配：镜头拼接、字幕、时长校验，产出 SceneArtifact。",
        "produces": ["SceneArtifact"],
        "writes_state": False,
        "used_by": ["Assembly (deterministic runtime)"],
    },
]

MECHANIC_SKILLS: list[dict[str, Any]] = [
    {
        "id": "relationship", "version": "1.0.0", "kind": "mechanic",
        "title": "关系变化", "user_facing": "关系变化",
        "description": "跟踪角色间信任/关系变化，产出 relationships.* 增量提案。",
        "produces": ["StatePatchProposal(relationships.*)"],
    },
    {
        "id": "clue-system", "version": "1.0.0", "kind": "mechanic",
        "title": "线索调查", "user_facing": "线索调查",
        "description": "线索生命周期 DISCOVERED → VERIFIED → USED，产出 clues.* 提案。",
        "produces": ["StatePatchProposal(clues.*)"],
    },
    {
        "id": "inventory", "version": "1.0.0", "kind": "mechanic",
        "title": "道具系统", "user_facing": "道具系统",
        "description": "物品持有与容量约束，产出 addItem / removeItem 提案。",
        "produces": ["StatePatchProposal(addItem/removeItem)"],
    },
    {
        "id": "qte", "version": "1.0.0", "kind": "mechanic",
        "title": "限时互动", "user_facing": "限时互动",
        "description": "限时决策窗口与确定性超时回退。",
        "produces": ["TimedInteractionRequest"],
    },
]


def registry() -> dict[str, Any]:
    """带启用状态的注册表视图。禁用是运行时行为，不写回静态定义。"""
    return {
        "platform": [{**s, "enabled": s["id"] not in _disabled} for s in PLATFORM_SKILLS],
        "mechanics": [{**s, "enabled": s["id"] not in _disabled} for s in MECHANIC_SKILLS],
    }


# 进程级开关（PRD FR-020 / 原型 Prototype Controls：禁用 Skill 后相关生成被阻塞）
_disabled: set[str] = set()


def is_enabled(skill_id: str) -> bool:
    return skill_id not in _disabled


def set_enabled(skill_id: str, enabled: bool) -> bool:
    known = {s["id"] for s in PLATFORM_SKILLS} | {s["id"] for s in MECHANIC_SKILLS}
    if skill_id not in known:
        return False
    if enabled:
        _disabled.discard(skill_id)
    else:
        _disabled.add(skill_id)
    return True

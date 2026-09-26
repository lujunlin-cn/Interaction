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
        "id": "intent-reconciliation", "version": "2.0.0", "kind": "platform",
        "title": "理解自由行动 · Understand Free Action",
        "description": "组合 Jev 观察与玩家确认，保留原文、目标、方式和否定约束；需要澄清时由 AI 预填理解。",
        "produces": ["ActionSemanticPacket", "IntentPreview"],
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


PLATFORM_SKILLS.extend([
    {"id": "choice-evaluation", "version": "1.0.0", "kind": "platform",
     "title": "评估行动选择 · Evaluate Choices", "description": "基于玩家已知情境生成具体行动与目的，经 Jev 排序，保留 OTHER 不确定性并移除精确重复。",
     "produces": ["RankedChoices", "RankingEvidence"], "writes_state": False, "used_by": ["Director", "Jev"]},
    {"id": "mechanic-arbitration", "version": "1.0.0", "kind": "platform",
     "title": "协调玩法提案 · Reconcile Mechanics", "description": "结合持有物、角色和线索阶段检查提案；矛盾退回 Director 修正一次，不伪造结果。",
     "produces": ["ArbitrationResult", "StatePatchProposal"], "writes_state": False, "used_by": ["Director", "StateManager"]},
])

CAPABILITY_CONTRACTS = {
    "intent-reconciliation": {"when_to_use": "Player FREE action or ambiguous input confirmation", "input": "RawInput + Jev observation + player-confirmed edits + visible context",
        "output": "ActionSemanticPacket v2 / editable IntentPreview", "failure_modes": ["ambiguous referent", "preview provider unavailable"],
        "fallback": "Preserve original; optional confirmation fields; never invent execution", "dependencies": ["Jev", "Director only for preview"],
        "evaluation": "raw/confirmed fidelity; blind trajectory pairwise; no factual side effects"},
    "choice-evaluation": {"when_to_use": "New canonical decision epoch", "input": "Known state, current beat, recent canonical actions, preferences, candidate actions",
        "output": "Concrete actions with plain-language purposes + Jev ranking + OTHER", "failure_modes": ["candidate provider unavailable", "Jev unavailable", "high OTHER"],
        "fallback": "Existing generic grounded candidates; no recursive regeneration", "dependencies": ["Director", "Jev"],
        "evaluation": "choice relevance/diversity, duplicate rate, knowledge boundary, Ready latency"},
    "mechanic-arbitration": {"when_to_use": "Director outcome before Narrative/Production", "input": "Director proposals + projected canonical state + enabled mechanics",
        "output": "Deduplicated proposals, per-trigger decisions and conflicts", "failure_modes": ["unowned removal", "use-as-acquisition", "unknown NPC", "clue regression", "conflicting target"],
        "fallback": "One Director correction; otherwise recoverable planning failure before media", "dependencies": ["inventory", "clue-system", "relationship", "StateManager"],
        "evaluation": "unsafe proposal acceptance, labeled trigger precision/recall, zero canonical mutation while planning"},
}
for definition in PLATFORM_SKILLS + MECHANIC_SKILLS:
    definition["implementation_kind"] = "deterministic_tool" if definition["id"] == "video-assembly" else "agent_capability" if definition["id"] in CAPABILITY_CONTRACTS else "existing_capability"
    if definition["id"] in CAPABILITY_CONTRACTS:
        definition["contract"] = {**CAPABILITY_CONTRACTS[definition["id"]], "side_effects": "Trace and proposals only; no canonical commit",
            "allowed_state_access": "Read-only projected state; StateManager retains commit authority", "metrics": ["invocations", "outcome", "latency_ms", "fallback", "proposal_disposition"]}


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

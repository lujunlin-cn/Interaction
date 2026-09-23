"""Mechanic Skills：触发→Proposal→确定性校验→提交的显式闭环（PRD SK-06 / FR-028 / G26）。

每个 mechanic 是纯函数：输入「触发 + 版本化上下文 + skill 配置」，输出
`StatePatchProposal` 形 dict（operations + skill_version + input 摘要），
由 Runtime 走与普通 outcome.ops 相同的 state_manager.validate → commit 管线，
并 emit `skill.{id}` trace span。Skill 不直接写状态、不绕过 Proposal 校验。
"""
from __future__ import annotations

from typing import Any

from ..domain.ids import uid
from .registry import MECHANIC_SKILLS, is_enabled

_VERSION = {s["id"]: s["version"] for s in MECHANIC_SKILLS}


def skill_version(skill_id: str) -> str:
    return _VERSION.get(skill_id, "0.0.0")


def _enabled(mechanics: dict, skill_id: str) -> bool:
    if not is_enabled(skill_id):
        return False
    cfg = (mechanics or {}).get(skill_id)
    if cfg is None:
        return True            # Scenario 未声明 → 默认启用（向后兼容）
    return bool(cfg.get("enabled", False))


def invoke(skill_id: str, trigger: dict, context: dict, mechanics: dict,
           branch_id: str, base_version: int, base_drama_revision: int) -> dict | None:
    """按 skill_id 分发到具体机制实现。返回 None 表示 skill 禁用/不处理该触发。

    context: {"npcs":[{id,identity}], "locations":{}, "location":str}
    trigger: director 返回的 {"skill": skill_id, "action":..., "target":..., "value":...}
    """
    if not _enabled(mechanics, skill_id):
        return None
    fn = _DISPATCH.get(skill_id)
    if fn is None:
        return None
    ops = fn(trigger, context, mechanics or {})
    if not ops:
        return None
    return {
        "skill_id": skill_id,
        "skill_version": skill_version(skill_id),
        "input": {"trigger": trigger, "npc": (context.get("npcs") or [{}])[0].get("id")},
        "proposal": {
            "proposal_id": uid("mprop"),
            "base_version": base_version,
            "base_drama_revision": base_drama_revision,
            "source": f"skill:{skill_id}:{branch_id}",
            "operations": ops,
            "idempotency_key": f"skill:{skill_id}:{branch_id}",
        },
    }


def _relationship(trigger: dict, context: dict, mechanics: dict) -> list[dict]:
    """关系变化：一次行动 → 目标 NPC 的 relationships.* 增量。"""
    npcs = context.get("npcs") or []
    target = trigger.get("target") or (str(npcs[0].get("id")) if npcs else "")
    if not target:
        return []
    delta = trigger.get("value")
    if delta is None:
        delta = int((mechanics.get("relationship", {}).get("config") or {})
                    .get("care_delta", 9))
    return [{"op": "increment", "path": f"relationships.{target}", "value": int(delta)}]


def _clue(trigger: dict, context: dict, mechanics: dict) -> list[dict]:
    """线索生命周期：DISCOVERED → VERIFIED → USED。"""
    clue_id = trigger.get("target") or trigger.get("clue")
    if not clue_id:
        return []
    stage = str(trigger.get("stage") or "DISCOVERED").upper()
    if stage not in ("DISCOVERED", "VERIFIED", "USED"):
        stage = "DISCOVERED"
    return [{"op": "set", "path": f"clues.{clue_id}", "value": stage}]


def _inventory(trigger: dict, context: dict, mechanics: dict) -> list[dict]:
    """道具持有：add / remove。"""
    item = trigger.get("target") or trigger.get("item")
    if not item:
        return []
    action = str(trigger.get("action") or "add").lower()
    return [{"op": "addItem" if action != "remove" else "removeItem", "value": item}]


_DISPATCH = {
    "relationship": _relationship,
    "clue-system": _clue,
    "inventory": _inventory,
}

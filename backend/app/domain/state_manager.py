"""StateManager —— World Hard State 的确定性管理器（PRD 07.3 / 13 / Q13 / Q52）。

- 模型与 Skill 只有提案权；这里是唯一可信写入接口。
- 校验：白名单路径、前置条件、数值合法性、base version、幂等键。
- 所有 apply 先在副本上执行，失败不污染原状态（事务语义由 CommitCoordinator 保证）。
"""
from __future__ import annotations

from typing import Any, Optional

from .schemas import PatchOperation, StatePatchProposal, WorldState

# 允许写入的世界路径白名单（不含 truth —— 核心真相不可由行动改写）
ALLOWED_PATCH_PATHS = {
    "location",
    "fiction_minutes",
    "health",
    "objects.back_door",
    "objects.recording",
    "objects.alice_alive",
    "objects.alice_visual",
    "objects.alice_departure",
}
ALLOWED_PREFIXES = ("relationships.", "clues.")


class ProposalRejected(Exception):
    def __init__(self, reason: str, duplicate: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.duplicate = duplicate


def _get_path(obj: Any, path: str) -> Any:
    cur: Any = obj
    for key in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            cur = getattr(cur, key, None)
    return cur


def _set_path(obj: Any, path: str, value: Any) -> None:
    keys = path.split(".")
    if any(k in ("__proto__", "constructor", "prototype") for k in keys):
        raise ProposalRejected(f"forbidden path segment: {path}")
    cur: Any = obj
    for key in keys[:-1]:
        if isinstance(cur, dict):
            cur = cur.setdefault(key, {})
        else:
            cur = getattr(cur, key)
    last = keys[-1]
    if isinstance(cur, dict):
        cur[last] = value
    else:
        setattr(cur, last, value)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def path_allowed(path: str) -> bool:
    return path in ALLOWED_PATCH_PATHS or any(path.startswith(p) for p in ALLOWED_PREFIXES)


def apply_operations(
    world: WorldState,
    ops: list[PatchOperation],
    *,
    inventory_capacity: int = 8,
) -> WorldState:
    """在副本上应用操作，返回新世界；任何非法操作抛 ProposalRejected，原世界不被修改。"""
    w = world.model_copy(deep=True)
    for op in ops:
        if op.op == "addItem":
            if not isinstance(op.value, str):
                raise ProposalRejected("addItem value must be string")
            if op.value not in w.inventory:
                if len(w.inventory) >= inventory_capacity:
                    raise ProposalRejected("inventory capacity exceeded")
                w.inventory.append(op.value)
        elif op.op == "removeItem":
            if op.value not in w.inventory:
                raise ProposalRejected(f"item not owned: {op.value}")
            w.inventory = [x for x in w.inventory if x != op.value]
        elif op.op == "inspect":
            if op.value not in w.inspected:
                w.inspected.append(str(op.value))
        elif op.op in ("set", "increment"):
            if not op.path or not path_allowed(op.path):
                raise ProposalRejected(f"forbidden patch path: {op.path}")
            if op.op == "increment":
                old = _get_path(w, op.path)
                if not isinstance(old, (int, float)) or not isinstance(op.value, (int, float)):
                    raise ProposalRejected(f"invalid numeric patch: {op.path}")
                val = old + op.value
                if op.path.startswith("relationships.") or op.path == "health":
                    val = _clamp(val, 0, 100)
                _set_path(w, op.path, val)
            else:
                _set_path(w, op.path, op.value)
        else:
            raise ProposalRejected(f"unknown operation: {op.op}")
    return w


class StateManager:
    """校验 + 提交 World 状态。version 单调递增。"""

    def __init__(self, inventory_capacity: int = 8):
        self.inventory_capacity = inventory_capacity

    def validate(
        self,
        world: WorldState,
        proposal: StatePatchProposal,
        committed_keys: list[str],
        drama_revision: Optional[int] = None,
    ) -> WorldState:
        """校验通过返回应用后的新世界（不落库）；失败抛 ProposalRejected。"""
        if proposal.idempotency_key and proposal.idempotency_key in committed_keys:
            raise ProposalRejected("idempotent duplicate", duplicate=True)
        if proposal.base_version != world.version:
            raise ProposalRejected(
                f"stale world version: base={proposal.base_version} current={world.version}")
        if proposal.base_drama_revision is not None and drama_revision is not None \
                and proposal.base_drama_revision != drama_revision:
            raise ProposalRejected(
                f"stale drama revision: base={proposal.base_drama_revision} current={drama_revision}")
        for pre in proposal.preconditions:
            actual = _get_path(world, pre.get("path", ""))
            if "equals" in pre and actual != pre["equals"]:
                raise ProposalRejected(
                    f"precondition failed: {pre.get('path')} expected {pre['equals']} got {actual}")
        new_world = apply_operations(world, proposal.operations, inventory_capacity=self.inventory_capacity)
        new_world.version = world.version + 1
        return new_world

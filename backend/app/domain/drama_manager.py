"""DramaStateManager —— Drama Domain 的确定性管理器（PRD 07.9 / Q44）。

Drama State 保存戏剧组织状态（阶段提示、伏笔、反转候选、待处理事项），不是第二份真相。
只允许白名单操作；不允许借 propose 把伏笔直接跳到 PAID_OFF。
"""
from __future__ import annotations

from .schemas import DramaPatchProposal, DramaState, ForeshadowStatus, ForeshadowEntry, PhaseHint
from .state_manager import ProposalRejected

ALLOWED_DRAMA_OPS = {
    "set_phase",               # {op, phase, reason}
    "propose_foreshadow",      # {op, entry_id, origin, truth, status=PROPOSED}
    "advance_foreshadow",      # {op, entry_id, to} 仅允许合法生命周期跃迁
    "add_obligation",          # {op, obligation}
    "update_obligation",       # {op, obligation_id, status, reason}
    "record_progress",         # {op, progress}
    "set_directive",           # {op, directive}
}

FORESHADOW_TRANSITIONS = {
    ForeshadowStatus.PROPOSED: {ForeshadowStatus.PLANTED, ForeshadowStatus.ABANDONED},
    ForeshadowStatus.PLANTED: {ForeshadowStatus.REINFORCED, ForeshadowStatus.PAYOFF_READY, ForeshadowStatus.ABANDONED},
    ForeshadowStatus.REINFORCED: {ForeshadowStatus.PAYOFF_READY, ForeshadowStatus.ABANDONED},
    ForeshadowStatus.PAYOFF_READY: {ForeshadowStatus.PAID_OFF, ForeshadowStatus.ABANDONED},
    ForeshadowStatus.PAID_OFF: set(),
    ForeshadowStatus.ABANDONED: set(),
}


class DramaStateManager:
    def validate_and_apply(self, drama: DramaState, proposal: DramaPatchProposal,
                           committed_keys: list[str]) -> DramaState:
        if proposal.idempotency_key and proposal.idempotency_key in committed_keys:
            raise ProposalRejected("idempotent duplicate", duplicate=True)
        if proposal.base_revision != drama.revision:
            raise ProposalRejected(
                f"stale drama revision: base={proposal.base_revision} current={drama.revision}")
        d = drama.model_copy(deep=True)
        for op in proposal.operations:
            kind = op.get("op")
            if kind not in ALLOWED_DRAMA_OPS:
                raise ProposalRejected(f"unknown drama operation: {kind}")
            if kind == "set_phase":
                d.phase = PhaseHint(op["phase"])
                d.phase_reason = op.get("reason", "")
            elif kind == "propose_foreshadow":
                if op.get("status", "PROPOSED") != "PROPOSED":
                    raise ProposalRejected("new foreshadow must start at PROPOSED")
                if any(f.id == op["entry_id"] for f in d.foreshadows):
                    raise ProposalRejected(f"foreshadow already exists: {op['entry_id']}")
                d.foreshadows.append(ForeshadowEntry(
                    id=op["entry_id"], origin=op.get("origin", "EMERGENT"), truth=op.get("truth", "")))
            elif kind == "advance_foreshadow":
                entry = next((f for f in d.foreshadows if f.id == op["entry_id"]), None)
                if entry is None:
                    raise ProposalRejected(f"foreshadow not found: {op['entry_id']}")
                target = ForeshadowStatus(op["to"])
                if target not in FORESHADOW_TRANSITIONS[entry.status]:
                    raise ProposalRejected(
                        f"illegal foreshadow transition: {entry.status} -> {target}")
                entry.status = target
                if op.get("evidence"):
                    entry.evidence.extend(op["evidence"])
                if op.get("presentation"):
                    entry.presentation.extend(op["presentation"])
                if op.get("abandon_reason"):
                    entry.abandon_reason = op["abandon_reason"]
            elif kind == "add_obligation":
                d.obligations.append(op["obligation"])
            elif kind == "update_obligation":
                ob = next((o for o in d.obligations if o.get("id") == op["obligation_id"]), None)
                if ob is None:
                    raise ProposalRejected(f"obligation not found: {op['obligation_id']}")
                ob["status"] = op["status"]
                if op.get("reason"):
                    ob["resolution_reason"] = op["reason"]
            elif kind == "record_progress":
                d.progress.append(op["progress"])
            elif kind == "set_directive":
                d.last_directive = op["directive"]
        d.revision = drama.revision + 1
        return d

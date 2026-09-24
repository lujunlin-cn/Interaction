"""SessionState —— Session 聚合根的完整可序列化状态（PRD 8.x / 13.4 持久化契约）。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from ..domain.schemas import (
    Branch, BranchStatus, DramaState, Event, NarrativeMemory, PlayerPreferenceState,
    PressureInstance, PresentationReceipt, RecommendationEpoch, RuntimeProfile, Wish,
    WorldState, now_ms,
)


class BudgetLedger(BaseModel):
    total: int = 500
    used: int = 0
    reserved: int = 0
    spent_by_branch: dict[str, int] = Field(default_factory=dict)
    per_turn: int = 60

    def available(self) -> int:
        return self.total - self.used - self.reserved


class Arc(BaseModel):
    id: str
    seq: int
    status: str = "ACTIVE"                    # ACTIVE / CLOSED
    ending_family: Optional[str] = None
    started_at: int = Field(default_factory=now_ms)
    closed_at: Optional[int] = None


class PlayerState(BaseModel):
    """播放器呈现状态：服务器以墙钟推导进度，前端只发命令（play/pause/skip/report）。"""
    status: str = "LOADING"                   # LOADING / PLAYING / READY / ENDED / FAILED
    scene_title: str = ""
    scene_text: str = ""
    caption: str = ""
    video_url: str = ""
    branch_id: Optional[str] = None
    duration: float = 0.0                     # 秒
    lead: float = 0.0                         # Decision Lead（秒）：进度越过 lead 即可发布下一批
    decision_open_at: float = 0.0             # 服务端推荐暴露闸门（绝不由前端决定）
    position_base: float = 0.0                # 最近一次推进到的进度
    playing: bool = False
    clock_started_at: Optional[int] = None    # 开始/恢复播放的墙钟
    receipt_committed: bool = False

    def position(self) -> float:
        if self.playing and self.clock_started_at:
            return self.position_base + (now_ms() - self.clock_started_at) / 1000.0
        return self.position_base


class TimedState(BaseModel):
    """限时互动（I02/I03）：倒计时由服务端驱动，超时结果由 Scenario 预先声明。"""
    active: bool = False
    node_id: str = ""
    kind: str = ""                            # qte / urgent_dialogue
    branch_ids: list[str] = Field(default_factory=list)
    deadline_ms: Optional[int] = None
    timeout_seconds: float = 0.0
    fallback_branch_id: Optional[str] = None
    selection_open: bool = False              # 全部 READY 前不允许选择
    fired_nodes: list[str] = Field(default_factory=list)  # 本篇章已触发过的限时节点


class EpochCounters(BaseModel):
    spend_attempts: int = 0
    spend_success: int = 0
    fallback_used: int = 0
    rebuild_count: int = 0


class SessionState(BaseModel):
    """Session 聚合根。所有字段都必须可 JSON 序列化。"""
    id: str
    scenario_id: str
    scenario_version_id: str
    scenario_snapshot: dict = Field(default_factory=dict)
    profile: RuntimeProfile = RuntimeProfile.AGENT_LOCAL

    world: WorldState = Field(default_factory=WorldState)
    drama: DramaState = Field(default_factory=DramaState)
    pressures: list[PressureInstance] = Field(default_factory=list)
    preferences: PlayerPreferenceState = Field(default_factory=PlayerPreferenceState)
    memory: NarrativeMemory = Field(default_factory=NarrativeMemory)

    arcs: list[Arc] = Field(default_factory=list)
    branches: list[Branch] = Field(default_factory=list)
    epoch: Optional[RecommendationEpoch] = None
    events: list[Event] = Field(default_factory=list)
    receipts: list[PresentationReceipt] = Field(default_factory=list)
    wishes: list[Wish] = Field(default_factory=list)
    wish_seq: int = 0

    player: PlayerState = Field(default_factory=PlayerState)
    budget: BudgetLedger = Field(default_factory=BudgetLedger)
    timed: TimedState = Field(default_factory=TimedState)
    counters: EpochCounters = Field(default_factory=EpochCounters)

    committed_keys: list[str] = Field(default_factory=list)
    merge_buffer: list[dict] = Field(default_factory=list)  # QUICK_ACK 小动作汇总缓冲
    messages: list[dict] = Field(default_factory=list)      # 小动作反馈流（ack/merged/系统提示）
    turns: list[dict] = Field(default_factory=list)         # 关键行动记录（结局页回顾）
    pending_intent: Optional[dict] = None       # 待确认/待纠正的意图（FR-046，保留原文）
    asset_manifest: list[dict] = Field(default_factory=list)  # 已绑定素材快照（指纹输入）
    hint_chips: list[str] = Field(default_factory=list)       # 「试试这些输入」建议

    selection_lock: bool = False              # SELECTED 处理中，阻塞新的提交
    pending_freeform_id: Optional[str] = None  # 自由输入分支：就绪后自动选中播放
    ended: bool = False
    pending_continuation: bool = False
    allow_media_invalidate: bool = True       # 生产环境 false：已呈现/已推荐资产不可因素材变更失效

    created_at: int = Field(default_factory=now_ms)
    updated_at: int = Field(default_factory=now_ms)

    # ------------------------------------------------------------------
    def current_arc(self) -> Optional[Arc]:
        for arc in self.arcs:
            if arc.status == "ACTIVE":
                return arc
        return None

    def branch(self, branch_id: str) -> Optional[Branch]:
        for b in self.branches:
            if b.id == branch_id:
                return b
        return None

    def active_branches(self) -> list[Branch]:
        """当前 epoch 中参与呈现的分支（READY/SELECTED）。"""
        if not self.epoch:
            return []
        ids = set(self.epoch.branch_ids)
        return [b for b in self.branches
                if b.id in ids and b.status in (BranchStatus.READY, BranchStatus.SELECTED)]

    def pipeline_branches(self) -> list[Branch]:
        return [b for b in self.branches if b.status in (
            BranchStatus.PREDICTED, BranchStatus.PLANNING, BranchStatus.NARRATIVE,
            BranchStatus.PRODUCTION, BranchStatus.GENERATING, BranchStatus.ASSEMBLING,
            BranchStatus.RETRYING)]

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        # 事件日志有界保留；完整历史在 DB 恢复路径中重新拉取（MVP 直接保留 500 条）
        if len(self.events) > 500:
            self.events = self.events[-500:]

    def touch(self) -> None:
        self.updated_at = now_ms()

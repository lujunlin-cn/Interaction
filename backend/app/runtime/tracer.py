"""Trace 服务：一个 trace_id 串起输入→评估→计划→生成→装配→呈现（PRD 15.4）。"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from ..db_models import TraceSpanRow
from ..domain.ids import uid
from ..domain.schemas import TraceSpan, now_ms


class Tracer:
    """进程内 trace 总线；负责把 span 写入 DB 并推送给 WS 订阅者。"""

    def __init__(self) -> None:
        self.recent: list[TraceSpan] = []
        self._ws_subscribers: list[Any] = []

    def subscribe(self, ws) -> None:
        self._ws_subscribers.append(ws)

    def unsubscribe(self, ws) -> None:
        if ws in self._ws_subscribers:
            self._ws_subscribers.remove(ws)

    async def emit(self, name: str, status: str, input_: dict | None = None,
                   output: dict | None = None, *, provider: str = "runtime",
                   model: str = "", model_version: str = "", profile: str = "",
                   downstream: str = "", duration_ms: int = 0,
                   session_id: Optional[str] = None, branch_id: Optional[str] = None,
                   trace_id: Optional[str] = None, skill_id: Optional[str] = None,
                   skill_version: Optional[str] = None) -> TraceSpan:
        span = TraceSpan(
            id=uid("span"), trace_id=trace_id or uid("trace"), session_id=session_id,
            branch_id=branch_id, name=name, status=status, input=input_ or {},
            output=output or {}, provider=provider, model=model, model_version=model_version,
            profile=profile, downstream_target=downstream, duration_ms=duration_ms,
            skill_id=skill_id, skill_version=skill_version, at=now_ms(),
        )
        self.recent.append(span)
        self.recent = self.recent[-2000:]
        # WS 广播（尽力而为）
        dead = []
        for ws in self._ws_subscribers:
            try:
                await ws.send_json({"type": "trace", "span": span.model_dump(mode="json")})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unsubscribe(ws)
        return span

    async def persist(self, span: TraceSpan, db) -> None:
        db.add(TraceSpanRow(
            id=span.id, trace_id=span.trace_id, session_id=span.session_id,
            branch_id=span.branch_id, name=span.name, status=span.status,
            data=span.model_dump(mode="json"), at=span.at))

    async def list_spans(self, db, session_id: str | None = None,
                         branch_id: str | None = None, limit: int = 200) -> list[TraceSpan]:
        q = select(TraceSpanRow).order_by(TraceSpanRow.at.desc()).limit(limit)
        if branch_id:
            q = select(TraceSpanRow).where(TraceSpanRow.branch_id == branch_id)\
                .order_by(TraceSpanRow.at.desc()).limit(limit)
        elif session_id:
            q = select(TraceSpanRow).where(TraceSpanRow.session_id == session_id)\
                .order_by(TraceSpanRow.at.desc()).limit(limit)
        rows = (await db.execute(q)).scalars().all()
        return [TraceSpan(**r.data) for r in rows]

    async def spans_for_skill(self, db, skill_id: str, limit: int = 5) -> list[TraceSpan]:
        """G24：某 Skill 最近调用记录（含被禁用时的阻塞记录）。"""
        rows = (await db.execute(
            select(TraceSpanRow)
            .where(TraceSpanRow.name.like(f"{skill_id}%"))
            .order_by(TraceSpanRow.at.desc()).limit(limit * 4))).scalars().all()
        spans = [TraceSpan(**r.data) for r in rows]
        hits = [s for s in spans if s.skill_id == skill_id or s.name.startswith(skill_id)]
        return hits[:limit]


tracer = Tracer()

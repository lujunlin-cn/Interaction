"""MockDecisionProvider —— Jev 的确定性替身（关键词规则）。

Jev 的真实 API 凭据未提供时，由它承担 First Pass（intent/significance/desire/confidence）。
它只产 observation，不覆盖玩家原文，不写事实。
"""
from __future__ import annotations

import asyncio
import re

from .base import DecisionAnswer


class MockDecisionProvider:
    name = "mock_decision"
    healthy = True

    async def evaluate(self, state, questions, model_version=None) -> DecisionAnswer:
        await asyncio.sleep(0.02)
        raw = str(state.get("raw_player_input", ""))
        answer: dict = {}
        for q in questions:
            qid = q.get("id")
            if qid == "intent":
                answer.update(self._intent(raw))
            elif qid == "rank":
                cands = q.get("candidates", [])
                base = [0.52, 0.31, 0.12]
                scores = {c: base[i] if i < len(base) else 0.05 for i, c in enumerate(cands)}
                scores["OTHER"] = 0.05
                answer["rank"] = scores
        return DecisionAnswer(
            choice=answer.get("action") or None,
            scores=answer.get("rank", {}),
            confidence=answer.get("confidence", 0.0),
            calibrated=False,
            model="mock-decision-v1",
            provider=self.name,
            latency_ms=20,
            details={k: v for k, v in answer.items() if k != "rank"},
        )

    def _intent(self, raw: str) -> dict:
        desire = None
        strategy = None
        source = "UNKNOWN"
        m = re.search(r"(?:是想|为了|希望)([^。！]+)", raw)
        if re.search(r"我.*(?:是想|为了|希望)", raw):
            desire = m.group(1) if m else None
            source = "PLAYER_EXPLICIT"
        elif re.search(r"假装|后门|观察|录音|钥匙|调查", raw):
            desire = "确认她是否隐瞒真相"
            source = "INFERRED"
        elif re.search(r"外套|保护|安慰", raw):
            desire = "表达关心并保护 Alice"
            source = "INFERRED"
        if re.search(r"假装|别让|不被|绕到|避免|悄悄|跟着", raw):
            strategy = "避免暴露怀疑"
        confidence = 0.88
        if re.search(r"彻底解决|处理掉|让她消失", raw):
            confidence = 0.32
        elif re.search(r"跟着|悄悄|试探", raw):
            confidence = 0.6      # 中置信度：触发意图回显（MEDIUM_ECHO，FR-046）
        impact = "HIGH" if (confidence < 0.5 or re.search(r"杀|死|解决她|公开|录音|离城|离开|等一小时", raw)) else "MEDIUM"
        # 开发夹具：置信度档位覆盖（Prototype Controls）
        from .fixtures import get as _fixtures
        mode = _fixtures().get("confidence", "auto")
        if mode == "high":
            confidence = 0.9
        elif mode == "medium":
            confidence = 0.6
        elif mode == "low":
            confidence = 0.32
        clarification = confidence < 0.5 and impact == "HIGH"
        return {
            "action": raw, "desire": desire, "strategy": strategy,
            "desire_source": source, "confidence": confidence,
            "impact": impact,
            "clarification_required": clarification,
            "clarification": "这件事的后果可能不可逆。你具体想怎么做？" if clarification else "",
        }

    async def health(self) -> bool:
        return self.healthy

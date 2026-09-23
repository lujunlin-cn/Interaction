"""JevDecisionProvider 真实 API 契约单测（不联网，桩住 httpx）。

验证：内部问题形态 → TypeSafe SystemOne 请求体的映射，
以及 answers → DecisionAnswer 的还原（rank 概率回填 label、intent 分类/置信/澄清）。
"""
from __future__ import annotations

import json

import pytest

from app.providers import real
from app.providers.real import JevDecisionProvider


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("err", request=None, response=None)  # type: ignore[arg-type]

    def json(self):
        return self._payload


class _FakeClient:
    """记录最后一次请求体并返回预设响应的 AsyncClient 桩。"""

    last_request: dict = {}

    def __init__(self, payload: dict):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.last_request = {"url": url, "json": json, "headers": headers}
        return _FakeResponse(self._payload)


def _patch(monkeypatch, payload: dict):
    monkeypatch.setattr(real.settings, "jev_api_key", "test-key")
    monkeypatch.setattr(real.httpx, "AsyncClient", lambda **kw: _FakeClient(payload))


@pytest.mark.asyncio
async def test_rank_maps_to_choice_and_scores_back_to_labels(monkeypatch):
    _patch(monkeypatch, {
        "model": "jev-1.13.0",
        "answers": {"rank": {"type": "choice", "choice": "c1", "confidence": 0.8,
                             "probabilities": {"c0": 0.2, "c1": 0.7, "OTHER": 0.1}}},
        "usage": {"input_tokens": 10, "output_tokens": 5},
    })
    p = JevDecisionProvider()
    ans = await p.evaluate(
        {"location": "foyer"},
        [{"id": "rank", "candidates": ["敲门问她", "保持沉默"]}])

    req = _FakeClient.last_request
    assert req["url"] == "https://api.typesafe.ai/v1/systemone"
    assert req["headers"]["Authorization"] == "Bearer test-key"
    q = req["json"]["questions"]["rank"]
    assert q["type"] == "choice"
    assert q["criteria"] == {"c0": "敲门问她", "c1": "保持沉默",
                             "OTHER": "以上都不合适的其他行动"}
    assert ans.scores == {"敲门问她": 0.2, "保持沉默": 0.7, "OTHER": 0.1}
    assert ans.choice == "保持沉默"
    assert ans.confidence == 0.8
    assert ans.model == "jev-1.13.0"      # FR-082：记录实际执行版本
    assert ans.provider == "jev"


@pytest.mark.asyncio
async def test_intent_maps_to_typed_questions_and_details(monkeypatch):
    _patch(monkeypatch, {
        "model": "jev-1.13.0",
        "answers": {
            "route": {"type": "choice", "choice": "action", "confidence": 0.9,
                      "probabilities": {"action": 0.9}},
            "impact": {"type": "score", "score": 1.8, "confidence": 0.6,
                       "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7}},
            "clarification": {"type": "noul", "noul": 0.72},
        },
        "usage": {},
    })
    p = JevDecisionProvider()
    ans = await p.evaluate(
        {"raw_player_input": "彻底解决她"},
        [{"id": "intent", "text": "彻底解决她"}])

    qs = _FakeClient.last_request["json"]["questions"]
    assert qs["route"]["type"] == "choice"
    assert qs["impact"]["type"] == "score" and len(qs["impact"]["criteria"]) == 3
    assert qs["clarification"]["type"] == "noul"
    d = ans.details
    assert d["action"] == "彻底解决她"          # 原文保留，Jev 不做生成式抽取
    assert d["route"] == "action"
    assert d["impact"] == "HIGH"                # score 1.8 ≥ 1.5
    assert d["clarification_required"] is True  # noul 0.72 ≥ 0.5
    assert d["clarification"]
    assert ans.confidence == 0.9


@pytest.mark.asyncio
async def test_missing_key_raises():
    import app.providers.real as real_mod
    real_mod.settings.jev_api_key = ""
    try:
        p = JevDecisionProvider(api_key="")
        with pytest.raises(RuntimeError):
            await p.evaluate({}, [{"id": "rank", "candidates": ["a"]}])
    finally:
        real_mod.settings.jev_api_key = "test-key"

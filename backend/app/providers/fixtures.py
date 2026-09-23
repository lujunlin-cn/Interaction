"""开发夹具（Prototype Controls，PRD 附录原型检查项的自动化支撑）。

只影响 Mock Provider 的输出形态（置信度档位 / 响应模式 / 泄密注入），
不改业务 Runtime：真实 Provider 接入时这些夹具自然失效。
"""
from __future__ import annotations

CONFIDENCE_MODES = ("auto", "high", "medium", "low")
RESPONSE_MODES = ("auto", "quick", "merged", "full")

_state: dict = {"confidence": "auto", "response": "auto", "leak_secret": False}


def get() -> dict:
    return dict(_state)


def set_fixture(key: str, value) -> bool:
    if key == "confidence" and value in CONFIDENCE_MODES:
        _state["confidence"] = value
        return True
    if key == "response" and value in RESPONSE_MODES:
        _state["response"] = value
        return True
    if key == "leak_secret":
        _state["leak_secret"] = bool(value)
        return True
    return False


def reset() -> None:
    _state.update({"confidence": "auto", "response": "auto", "leak_secret": False})

"""确定性 Dependency Fingerprint（PRD 10.14 / Q67）。

指纹基于 Branch 声明的 read set（依赖版本快照），由确定性代码计算 SHA-256；
不允许让 LLM「凭相似感觉」决定缓存复用。未声明依赖 → 保守 miss。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_of(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def fingerprint_of(read_set: dict[str, Any]) -> str:
    if not read_set:
        return ""
    return sha256_of(read_set)

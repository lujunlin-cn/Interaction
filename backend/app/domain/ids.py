"""稳定 ID 生成。"""
from __future__ import annotations

import itertools
import secrets

_counter = itertools.count(1)


def uid(prefix: str) -> str:
    return f"{prefix}_{next(_counter):05d}_{secrets.token_hex(3)}"

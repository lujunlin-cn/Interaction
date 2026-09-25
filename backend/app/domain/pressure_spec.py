"""Lossless authoring representation repair for the existing pressure-line contract.

The runtime consumes name｜source｜driver. Drivers must be explicit; natural
language consequences, elapsed real time, or vague urgency never imply one.
"""
from __future__ import annotations

import copy
import json
import re
from typing import Any


PRESSURE_FORMAT = "压力需要明确名称、来源，以及行动触发或故事时间推进；请保留事实并补充触发方式。"
_ALIASES = {
    "行动触发": ("行动触发", "action", "actions", "action_triggered", "action_driven", "committed_actions"),
    "故事时间推进": ("故事时间推进", "fiction_time", "fictional_time", "story_time", "story_time_driven"),
}
_KEYS = {
    "name": ("name", "title", "名称"),
    "source": ("source", "origin", "来源"),
    "driver": ("trigger_type", "trigger", "driver", "驱动", "触发方式"),
    "consequence": ("consequence", "effect", "后果"),
}


def _driver(value: str, *, exact: bool = False) -> str | None:
    value = value.strip().lower().replace("-", "_")
    if not exact and (re.search(r"(?:不是|并非|非|不随|不要|不由|不能|not|without|no)\s*(?:行动触发|故事时间推进|action|fiction|story)", value)
                      or re.search(r"(?:行动触发|故事时间推进)\s*(?:不|无效)", value)):
        raise ValueError(PRESSURE_FORMAT)
    matches = set()
    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            found = value == alias if exact else (
                alias in value if not alias.isascii() else
                bool(re.search(r"(?<![a-z_])" + re.escape(alias) + r"(?![a-z_])", value)))
            if found:
                matches.add(canonical)
    if len(matches) > 1:
        raise ValueError(PRESSURE_FORMAT)
    return next(iter(matches), None)


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or any(x in value for x in ("\n", "\r", "｜", "|")):
        raise ValueError(PRESSURE_FORMAT)
    return value.strip()


def _row(row: dict) -> str:
    if set(row) - {key for keys in _KEYS.values() for key in keys}:
        # Unknown fields may carry story semantics; never silently discard them.
        raise ValueError(PRESSURE_FORMAT)
    values = {}
    for key, aliases in _KEYS.items():
        present = [_text(row[k]) for k in aliases if k in row]
        if len(set(present)) > 1 or (not present and key != "consequence"):
            raise ValueError(PRESSURE_FORMAT)
        values[key] = present[0] if present else ""
    driver = _driver(values["driver"])
    if driver is None:
        raise ValueError(PRESSURE_FORMAT)
    source = values["source"]
    source_driver = _driver(source)
    if source_driver is not None and source_driver != driver:
        raise ValueError(PRESSURE_FORMAT)
    if _driver(values["driver"], exact=True) is None:
        source += "；" + values["driver"]
    if values["consequence"]:
        source += "；后果：" + values["consequence"]
    return f'{values["name"]}｜{source}｜{driver}'


def _line(line: str) -> str:
    parts = [_text(p) for p in re.split(r"[｜|]", line)]
    if len(parts) != 3:
        raise ValueError(PRESSURE_FORMAT)
    name, source, tail = parts
    driver = _driver(tail, exact=True)
    if driver is not None:
        source_driver = _driver(source)
        if source_driver is not None and source_driver != driver:
            raise ValueError(PRESSURE_FORMAT)
        return f"{name}｜{source}｜{driver}"
    # Older model output swapped the driver and consequence columns, or embedded
    # an explicit driver in the source. Retain both original pieces of wording.
    driver = _driver(source + "；" + tail)
    if driver is None:
        raise ValueError(PRESSURE_FORMAT)
    return f"{name}｜{source}；{tail}｜{driver}"


def normalize_pressures(value: Any) -> str:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        if value.startswith(("[", "{")):
            try:
                value = json.loads(value)
            except (ValueError, TypeError) as error:
                raise ValueError(PRESSURE_FORMAT) from error
        else:
            return "\n".join(_line(line) for line in value.splitlines() if line.strip())
    if isinstance(value, dict):
        if set(value) == {"pressures"}:
            return normalize_pressures(value["pressures"])
        if any(k in value for k in _KEYS["name"]):
            return _row(value)
        if value and all(isinstance(v, dict) for v in value.values()):
            rows = []
            for name, row in value.items():
                named = [row[key] for key in _KEYS["name"] if key in row]
                if named and any(v != name for v in named):
                    raise ValueError(PRESSURE_FORMAT)
                rows.append(_row(row if named else {"name": name, **row}))
            return "\n".join(rows)
        raise ValueError(PRESSURE_FORMAT)
    if isinstance(value, list):
        return "\n".join(normalize_pressures(row) for row in value)
    raise ValueError(PRESSURE_FORMAT)


def normalize_draft_pressures(data: dict, *, strict: bool = True) -> dict:
    """Normalize a copy. Tolerant reads keep legacy drafts editable, never valid."""
    data = copy.deepcopy(data)
    drama = data.get("drama")
    if isinstance(drama, dict) and "pressures" in drama:
        try:
            drama["pressures"] = normalize_pressures(drama["pressures"])
        except ValueError:
            if strict:
                raise
    # Historical pending proposals remain user-confirmed proposals. Repair only
    # their representation so accepting one cannot reintroduce a JSON string.
    for projection in (data.get("creator_projection") or {}).values():
        if not isinstance(projection, dict):
            continue
        for item in projection.get("items", []):
            if not isinstance(item, dict) or item.get("path") != "drama.pressures":
                continue
            for key in ("value", "before"):
                if key in item:
                    try:
                        item[key] = normalize_pressures(item[key])
                    except ValueError:
                        pass
            for suggestion in item.get("suggestions", []):
                try:
                    suggestion["value"] = normalize_pressures(suggestion["value"])
                except (ValueError, KeyError, TypeError):
                    pass
    return data

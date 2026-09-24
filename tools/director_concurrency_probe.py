"""Small OpenAI-compatible Director concurrency probe.

The probe is intentionally independent from Session state: each request carries
its own scenario context and raw action. It measures the vLLM endpoint directly;
the backend's Director admission control is not exercised here.
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass

import httpx


MODEL = os.getenv("LOCAL_LLM_MODEL", "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4")
BASE = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
WAVES = int(os.getenv("DIRECTOR_PROBE_WAVES", "3"))
LEVELS = tuple(int(value) for value in os.getenv("DIRECTOR_PROBE_LEVELS", "1,2,4,8").split(","))
MAX_TOKENS = int(os.getenv("DIRECTOR_PROBE_MAX_TOKENS", "512"))


@dataclass
class Sample:
    ok: bool
    latency_ms: float
    ttft_ms: float = 0
    output_tokens: int = 0
    error: str = ""


def payload(i: int) -> dict:
    context = {
        "title": f"并发验证场景 {i}", "genre": "悬疑", "tone": "克制",
        "core_question": "值班员为何隐瞒停电原因？",
        "ending_families": {"truth": "查清真相", "leave": "主动离开"},
        "truth_model": "outage：电源被人为切断",
        "locations": {"start": "起点", "hall": "走廊"},
        "location": "start", "inventory": [], "clues": [],
        "relationships": {"npc": 40}, "phase": "exploration",
        "npcs": [{"id": "npc", "identity": "值班员"}],
    }
    user_content = (
        f"raw_player_input: 我检查眼前的线索并询问值班员（Session {i}）。\n"
        f"scenario_context: {json.dumps(context, ensure_ascii=False)}\n"
        '返回 JSON：{"outcome":{"title":str,"text":str,"ops":[],"evidence":[],"ending":null,"kind":str,"skill_triggers":[]},'
        '"directive":{"primary_function":str,"secondary_functions":[],"target_changes":[],"hard_constraints":[],"avoid":[]}}。'
    )
    return {
        "model": MODEL,
        "temperature": 0.2,
        "max_tokens": MAX_TOKENS,
        "response_format": {"type": "json_object"},
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": user_content}],
    }


async def one(client: httpx.AsyncClient, i: int) -> Sample:
    start = time.perf_counter()
    try:
        first_token = 0.0
        tokens = 0
        parts: list[str] = []
        finish_reason = ""
        async with client.stream("POST", f"{BASE}/chat/completions", json=payload(i)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                body = json.loads(line[6:])
                choice = (body.get("choices") or [{}])[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason") or finish_reason
                chunk = delta.get("content") or ""
                if chunk:
                    if not first_token:
                        first_token = (time.perf_counter() - start) * 1000
                    parts.append(chunk)
                tokens = int((body.get("usage") or {}).get("completion_tokens") or tokens)
        try:
            parsed = json.loads("".join(parts))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {exc}; finish_reason={finish_reason}; chars={sum(map(len, parts))}; tokens={tokens}") from exc
        if not isinstance(parsed.get("outcome"), dict) or not isinstance(parsed.get("directive"), dict):
            raise ValueError("director output lacks outcome/directive")
        elapsed = (time.perf_counter() - start) * 1000
        return Sample(True, elapsed, first_token, tokens)
    except Exception as exc:  # noqa: BLE001
        return Sample(False, (time.perf_counter() - start) * 1000, error=str(exc))


async def run(level: int) -> None:
    timeout = httpx.Timeout(180.0, connect=5.0)
    batch_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        samples = []
        for wave in range(WAVES):
            samples.extend(await asyncio.gather(
                *(one(client, wave * level + i) for i in range(level))))
    batch_s = time.perf_counter() - batch_start
    good = [s for s in samples if s.ok]
    latencies = sorted(s.latency_ms for s in samples)
    p50 = statistics.median(latencies) if latencies else 0
    p95 = latencies[max(0, int((len(latencies) - 1) * 0.95 + 0.5))] if latencies else 0
    tokens = sum(s.output_tokens for s in good)
    print(json.dumps({
        "concurrency": level, "waves": WAVES,
        "max_tokens": MAX_TOKENS,
        "success": len(good), "total": len(samples),
        "success_rate": len(good) / len(samples) if samples else 0,
        "p50_ms": round(p50, 1), "p95_ms": round(p95, 1),
        "p50_ttft_ms": round(statistics.median(s.ttft_ms for s in good), 1) if good else None,
        "output_tokens": tokens, "aggregate_tokens_per_s": round(tokens / max(batch_s, 0.001), 2),
        "request_throughput_per_s": round(len(good) / max(batch_s, 0.001), 2),
        "errors": [s.error for s in samples if not s.ok],
    }, ensure_ascii=False))


async def main() -> None:
    for level in LEVELS:
        await run(level)


if __name__ == "__main__":
    asyncio.run(main())

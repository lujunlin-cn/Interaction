"""真实 Provider：StepFun（OpenAI 兼容）、本地 Nemotron（OpenAI 兼容）、fal.ai H3 Max。

密钥全部来自环境变量；任何 Provider 失效由 Router 统一处理。
"""
from __future__ import annotations

import asyncio
import time

import httpx

from ..config import settings
from .base import DecisionAnswer, TextResponse, VideoJobHandle, VideoJobResult


class OpenAICompatTextProvider:
    """Step 3.7 / Step 5 / 本地 Nemotron Lightning 共用（OpenAI chat.completions 兼容）。"""

    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def generate(self, messages, output_contract=None, tools=None, budget=None) -> TextResponse:
        t0 = time.time()
        payload: dict = {"model": self.model, "messages": messages, "temperature": 0.7}
        if output_contract:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return TextResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            provider=self.name,
            latency_ms=int((time.time() - t0) * 1000),
            usage=data.get("usage", {}),
        )

    async def health(self) -> bool:
        if not self.api_key and "127.0.0.1" not in self.base_url and "localhost" not in self.base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                resp = await client.get(f"{self.base_url}/models", headers=headers)
                return resp.status_code < 500
        except Exception:
            return False


class FalH3MaxProvider:
    """fal.ai 上的 H3 Max（reference-to-video）。提交后轮询任务状态。"""

    name = "h3_max"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.fal_key
        self.model = model or settings.fal_h3_model
        self.base = f"https://queue.fal.run/{self.model}"

    def capabilities(self) -> dict:
        return {
            "text_to_video": "documented", "reference_image": "documented",
            "reference_audio": "documented", "reference_video": "documented",
            "limits": {"image": 9, "audio": 3, "video": 3, "mixed": 12},
            "limits_source": "PRD 13.2 snapshot, 升级后需回归测试",
        }

    async def submit(self, request: dict) -> VideoJobHandle:
        prompt = request.get("prompt", "")
        payload: dict = {"prompt": prompt}
        for key in ("image_url", "reference_image_urls", "reference_audio_urls", "reference_video_urls"):
            if request.get(key):
                payload[key] = request[key]
        headers = {"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(self.base, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return VideoJobHandle(provider_job_id=data["request_id"], provider=self.name)

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        headers = {"Authorization": f"Key {self.api_key}"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(f"{self.base}/requests/{handle.provider_job_id}/status", headers=headers)
            resp.raise_for_status()
            st = resp.json().get("status", "")
            if st not in ("COMPLETED",):
                return VideoJobResult(status="GENERATING" if st in ("IN_PROGRESS", "IN_QUEUE") else st,
                                      raw={"fal_status": st})
            result = await client.get(f"{self.base}/requests/{handle.provider_job_id}", headers=headers)
            result.raise_for_status()
            data = result.json()
        video_url = (data.get("video") or {}).get("url") or data.get("video_url")
        if not video_url:
            return VideoJobResult(status="FAILED", error="fal response has no video url", raw=data)
        # 下载到受控媒体目录
        out = settings.media_path / "clips" / handle.provider_job_id
        out.mkdir(parents=True, exist_ok=True)
        target = out / "clip_1.mp4"
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("GET", video_url) as r:
                r.raise_for_status()
                with open(target, "wb") as f:
                    async for chunk in r.aiter_bytes(1 << 20):
                        f.write(chunk)
        return VideoJobResult(status="READY", video_path=str(out), raw={"clips": [str(target)], "fal": data})

    async def cancel_if_supported(self, handle: VideoJobHandle) -> bool:
        try:
            headers = {"Authorization": f"Key {self.api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(
                    f"{self.base}/requests/{handle.provider_job_id}/cancel", headers=headers)
                return resp.status_code < 300
        except Exception:
            return False

    async def health(self) -> bool:
        return bool(self.api_key)


class SolH3LocalProvider:
    """Sol-H3 本地视频后端（DGX Spark）。VIDEO_LOCAL_PROFILE 显式启用；能力需实测。"""

    name = "sol_h3_local"

    def __init__(self, base_url: str = ""):
        self.base_url = base_url

    def capabilities(self) -> dict:
        return {
            "text_to_video": "unknown",
            "reference_image": "unknown", "reference_audio": "unknown", "reference_video": "unknown",
            "note": "Spark 本地后端能力未实测；不可用时有参考的分支必须明确阻塞，不静默丢参考",
        }

    async def submit(self, request: dict) -> VideoJobHandle:
        raise RuntimeError("Sol-H3 local provider not configured")

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        return VideoJobResult(status="FAILED", error="Sol-H3 local provider not configured")

    async def cancel_if_supported(self, handle: VideoJobHandle) -> bool:
        return False

    async def health(self) -> bool:
        return bool(self.base_url)


class JevDecisionProvider:
    """Jev（TypeSafe SystemOne）真实 API：类型化问题评估，不是聊天补全（PRD S05/FR-016）。

    POST {base}/v1/systemone，questions = {id: {type, instructions, criteria}}，
    候选由调用方提供；返回 choice / score / noul 概率与 confidence。

    内部问题形态映射：
    - {"id": "rank", "candidates": [...]} → choice 题，回传 scores={候选label: 概率}
    - {"id": "intent", "text": ...}      → route(choice) + impact(score) + clarification(noul)
    Jev 不做生成式文本抽取；action 保留玩家原文，desire/strategy 交由 Director 细化
    （FR-066：Jev observation 是辅助观察，不覆盖原文、不作为事实）。
    """

    name = "jev"

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key or settings.jev_api_key
        self.base_url = (base_url or settings.jev_base_url).rstrip("/")

    async def evaluate(self, state, questions, model_version=None) -> DecisionAnswer:
        if not self.api_key:
            raise RuntimeError("jev api key not configured (JEV_API_KEY)")
        t0 = time.time()
        ts_questions: dict = {}
        kinds: dict[str, str] = {}
        rank_candidates: list[str] = []
        for q in questions:
            qid = q.get("id")
            if qid == "rank":
                rank_candidates = list(q.get("candidates", []))
                criteria = {f"c{i}": label for i, label in enumerate(rank_candidates)}
                criteria["OTHER"] = "以上都不合适的其他行动"
                ts_questions["rank"] = {
                    "type": "choice",
                    "instructions": "在当前情境与近期真实选择下，玩家最可能选择哪个行动？",
                    "criteria": criteria,
                }
                kinds["rank"] = "rank"
            elif qid == "intent":
                ts_questions["route"] = {
                    "type": "choice",
                    "instructions": "这段玩家输入属于哪一类？",
                    "criteria": {
                        "action": "玩家要让角色做的事情",
                        "dialogue": "玩家想让角色说的话",
                        "question": "玩家在询问信息",
                        "wish": "玩家表达的愿望或期待（不直接改变事实）",
                    },
                }
                ts_questions["impact"] = {
                    "type": "score",
                    "instructions": "这个行动对故事走向的潜在影响有多大？",
                    "criteria": ["低影响：日常小动作，容易撤销",
                                 "中影响：会改变关系或获得信息",
                                 "高影响：可能不可逆，涉及秘密、生死或离开"],
                }
                ts_questions["clarification"] = {
                    "type": "noul",
                    "instructions": "这段话是否含糊到无法安全执行、必须先向玩家澄清？",
                    "criteria": {"true": "含义模糊，或后果严重但表述不清",
                                 "false": "可以直接理解并执行"},
                }
                kinds["intent"] = "intent"
        payload = {
            "state": state,
            "model": model_version or settings.jev_model,
            "questions": ts_questions,
        }
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/v1/systemone",
                                     json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        answers = data.get("answers", {})
        choice: str | None = None
        scores: dict[str, float] = {}
        details: dict = {}
        confidence = 0.0
        for qid in kinds:
            if qid == "rank":
                ans = answers.get("rank") or {}
                probs = ans.get("probabilities") or {}
                for i, label in enumerate(rank_candidates):
                    scores[label] = float(probs.get(f"c{i}", 0.0))
                scores["OTHER"] = float(probs.get("OTHER", 0.0))
                sel = ans.get("choice")
                if sel == "OTHER":
                    choice = "OTHER"
                elif isinstance(sel, str) and sel.startswith("c") and sel[1:].isdigit() \
                        and int(sel[1:]) < len(rank_candidates):
                    choice = rank_candidates[int(sel[1:])]
                confidence = max(confidence, float(ans.get("confidence", 0.0)))
            else:
                route = answers.get("route") or {}
                impact = answers.get("impact") or {}
                clar = answers.get("clarification") or {}
                impact_score = float(impact.get("score", 1.0))
                impact_label = ("LOW" if impact_score < 0.5
                                else "HIGH" if impact_score >= 1.5 else "MEDIUM")
                need_clar = float(clar.get("noul", 0.0) or 0.0) >= 0.5
                route_conf = float(route.get("confidence", 0.0))
                details.update({
                    "action": state.get("raw_player_input", ""),
                    "desire": "",
                    "strategy": "",
                    "desire_source": "UNKNOWN",
                    "route": route.get("choice"),
                    "confidence": route_conf,
                    "impact": impact_label,
                    "clarification_required": need_clar,
                    "clarification": ("这件事的后果可能不可逆。你具体想怎么做？"
                                      if need_clar else ""),
                })
                confidence = max(confidence, route_conf)
        details["usage"] = data.get("usage", {})
        return DecisionAnswer(
            choice=choice, scores=scores, confidence=confidence, calibrated=False,
            model=data.get("model", settings.jev_model),   # 实际执行版本（FR-082 记录）
            provider=self.name, latency_ms=int((time.time() - t0) * 1000),
            details=details,
        )

    async def health(self) -> bool:
        return bool(self.api_key and self.base_url)


def build_provider_registry(mode: str) -> dict:
    """按 provider_mode 构建注册表。mock 模式下所有角色都有确定性 Provider。"""
    step37 = OpenAICompatTextProvider("step_37", settings.step_base_url, settings.step_api_key, settings.step37_model)
    step5 = OpenAICompatTextProvider("step_5", settings.step_base_url, settings.step_api_key, settings.step5_model)
    lightning = OpenAICompatTextProvider(
        "nemotron_local", settings.local_llm_base_url, "", settings.local_llm_model)
    registry: dict = {
        "step_37": step37,
        "step_5": step5,
        "nemotron_local": lightning,
        "h3_max": FalH3MaxProvider(),
        "sol_h3_local": SolH3LocalProvider(),
        "jev": JevDecisionProvider(),
    }
    if mode in ("mock", "hybrid"):
        from .mock_decision import MockDecisionProvider
        from .mock_text import MockTextProvider
        from .mock_video import MockVideoProvider
        registry["mock_text"] = MockTextProvider()
        registry["mock_decision"] = MockDecisionProvider()
        registry["mock_video"] = MockVideoProvider()
    return registry

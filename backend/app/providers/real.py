"""真实 Provider：StepFun（OpenAI 兼容）、本地 Nemotron（OpenAI 兼容）、fal.ai H3 Max。

密钥全部来自环境变量；任何 Provider 失效由 Router 统一处理。
"""
from __future__ import annotations

import asyncio
import time

import httpx

from ..config import settings
from .base import DecisionAnswer, TextResponse, VideoJobHandle, VideoJobResult


class FalGenerationError(RuntimeError):
    """分类后的 Fal 错误，供 Router/Runtime 做可审计回退。"""
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


_fal_circuit = {"state": "CLOSED", "reason": "", "opened_at": None}


def fal_circuit_status() -> dict:
    return dict(_fal_circuit)


def reset_fal_circuit() -> None:
    _fal_circuit.update({"state": "CLOSED", "reason": "", "opened_at": None})


def _ensure_fal_paid_allowed() -> None:
    if not settings.fal_paid_generation_enabled:
        raise FalGenerationError("PAID_GENERATION_DISABLED", "provider unavailable: paid generation disabled")
    if _fal_circuit["state"] == "OPEN":
        raise FalGenerationError(_fal_circuit["reason"] or "BILLING_LOCKED",
                                 f"provider unavailable: {_fal_circuit['reason'] or 'Fal circuit open'}")


def _fal_http_error(exc: httpx.HTTPStatusError) -> FalGenerationError:
    code = exc.response.status_code
    body = exc.response.text[:1000]
    upper = body.upper()
    if "QUOTA" in upper or "INSUFFICIENT" in upper or code == 402:
        _fal_circuit.update({"state": "OPEN", "reason": "QUOTA_EXHAUSTED", "opened_at": time.time()})
        return FalGenerationError("QUOTA_EXHAUSTED", "provider unavailable: quota exhausted")
    if code == 403 and ("TOP_UP" in upper or "USER IS LOCKED" in upper or "BILLING" in upper):
        _fal_circuit.update({"state": "OPEN", "reason": "BILLING_LOCKED", "opened_at": time.time()})
        return FalGenerationError("BILLING_LOCKED", "provider unavailable: billing locked")
    if code == 403:
        return FalGenerationError("AUTH_FAILED", "provider authentication failed")
    if code == 429:
        return FalGenerationError("RATE_LIMITED", "provider rate limited")
    if code >= 500:
        return FalGenerationError("TRANSIENT_PROVIDER_ERROR", f"provider error {code}")
    if code in (400, 422):
        return FalGenerationError("INVALID_REQUEST", f"provider rejected request ({code})")
    return FalGenerationError("TRANSIENT_PROVIDER_ERROR", f"provider HTTP error ({code})")


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
        if budget and budget.get("max_tokens"):
            payload["max_tokens"] = int(budget["max_tokens"])
        if budget and budget.get("reasoning_effort") and self.name.startswith("step_"):
            payload["reasoning_effort"] = budget["reasoning_effort"]
        # Step Plan / Step 5 currently corrupts object keys with json_object
        # (see step_format_probe_*.json). Keep schema instructions in messages
        # and validate the response at the authoring/director boundary.
        if output_contract and self.name != "step_5":
            payload["response_format"] = {"type": "json_object"}
        if self.name == "nemotron_local":
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        timeout = (settings.director_local_request_timeout_seconds
                   if self.name == "nemotron_local" else settings.provider_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        actual_model = data.get("model", "")
        if self.name == "nemotron_local" and actual_model != self.model:
            raise RuntimeError(
                f"nemotron_local model mismatch: expected {self.model}, got {actual_model}")
        return TextResponse(
            content=data["choices"][0]["message"]["content"],
            model=actual_model or self.model,
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
                resp.raise_for_status()
                if self.name == "nemotron_local":
                    return any(m.get("id") == self.model
                               for m in resp.json().get("data", []))
                return True
        except Exception:
            return False


class FalH3MaxProvider:
    """fal.ai 上的 H3 Max（reference-to-video）。提交后轮询任务状态。"""

    name = "h3_max"

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.fal_key
        self.model = model or settings.fal_h3_model
        # submit 用完整 endpoint id；status/result/cancel 优先用 submit 响应
        # 返回的 status_url/response_url/cancel_url（官方文档推荐做法，
        # 避免自己猜 app-id 层级导致 405）。
        self.base = f"https://queue.fal.run/{self.model}"

    def capabilities(self) -> dict:
        return {
            "text_to_video": "documented", "reference_image": "documented",
            "reference_audio": "documented", "reference_video": "documented",
            "limits": {"image": 9, "audio": 3, "video": 3, "mixed": 12},
            "limits_source": "PRD 13.2 snapshot, 升级后需回归测试",
        }

    def _adapt_references(self, request: dict) -> dict:
        """把 Runtime 的 references[]（type=image/voice/video + path）映射为
        fal 的 reference_image_urls / reference_audio_urls / reference_video_urls。

        Runtime 传的是统一 references 列表；这里做协议适配，不能静默丢失（G09）。
        path 为服务器本地媒体路径时须先转可访问 URL（fal 拉取）；本地路径走
        /media 挂载的公网/内网 URL 前缀。
        """
        out: dict = {"reference_image_urls": [], "reference_audio_urls": [],
                     "reference_video_urls": []}
        role_to_kind = {"identity": "image", "wardrobe": "image", "motion": "video",
                        "voice": "audio", "reference": "image"}
        for ref in request.get("references") or []:
            if isinstance(ref, str):
                path, kind = ref, "image"
            else:
                path = ref.get("path") or ref.get("url") or ""
                kind = ref.get("type") or role_to_kind.get(ref.get("role", ""), "image")
            if not path:
                continue
            if path.startswith(("http://", "https://")):
                url = path
            elif path.startswith(("/files/", "/media/")):
                url = settings.public_base_url.rstrip("/") + path
            else:
                url = f"{settings.public_base_url.rstrip('/')}/files/{path.lstrip('/')}"
            if kind == "image":
                out["reference_image_urls"].append(url)
            elif kind == "audio":
                out["reference_audio_urls"].append(url)
            elif kind == "video":
                out["reference_video_urls"].append(url)
        caps = {"reference_image_urls": 9, "reference_audio_urls": 3, "reference_video_urls": 3}
        return {k: v[: caps[k]] for k, v in out.items() if v}

    async def submit(self, request: dict) -> VideoJobHandle:
        _ensure_fal_paid_allowed()
        prompt = request.get("prompt", "")
        shots = request.get("shots") or []
        # H3 Max requires duration for each independent Shot request.  Runtime
        # deliberately submits one-shot payloads for real multi-shot assembly.
        payload: dict = {
            "prompt": prompt,
            "duration": float(shots[0].get("duration", settings.mock_shot_duration))
            if shots else settings.mock_shot_duration,
            "resolution": request.get("resolution") or settings.video_generation_resolution,
            "aspect_ratio": request.get("aspect_ratio") or settings.generation_aspect_ratio,
        }
        for key in ("image_url", "reference_image_urls", "reference_audio_urls", "reference_video_urls"):
            if request.get(key):
                payload[key] = request[key]
        # references[] → fal 字段适配（G09：不再静默丢失）
        for key, urls in self._adapt_references(request).items():
            payload.setdefault(key, [])
            payload[key] = list(dict.fromkeys(payload[key] + urls))
        headers = {"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            try:
                resp = await client.post(self.base, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise _fal_http_error(exc) from exc
            except httpx.TimeoutException as exc:
                raise FalGenerationError("TIMEOUT", "provider request timed out") from exc
            data = resp.json()
        return VideoJobHandle(
            provider_job_id=data["request_id"], provider=self.name,
            status_url=data.get("status_url"),
            response_url=data.get("response_url"),
            cancel_url=data.get("cancel_url"))

    def _status_url(self, handle: VideoJobHandle) -> str:
        if handle.status_url:
            return handle.status_url
        raise RuntimeError(
            "fal handle missing status_url (job submitted before handle-url "
            "support); resubmit the job to obtain queue URLs")

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        headers = {"Authorization": f"Key {self.api_key}"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(self._status_url(handle), headers=headers)
            resp.raise_for_status()
            st = resp.json().get("status", "")
            if st not in ("COMPLETED",):
                return VideoJobResult(status="GENERATING" if st in ("IN_PROGRESS", "IN_QUEUE") else st,
                                      raw={"fal_status": st})
            result_url = handle.response_url
            if not result_url and handle.status_url:
                # minimax 这类 app 返回的 response_url 即 .../requests/{id}（不带 /response）
                result_url = handle.status_url[: -len("/status")] \
                    if handle.status_url.endswith("/status") else handle.status_url
            if not result_url:
                raise RuntimeError("fal handle missing response_url")
            result = await client.get(result_url, headers=headers)
            if result.status_code == 422:
                # fal queue versions differ: some expose the response at
                # /response while newer ones return the request URL. Retry
                # the documented response suffix before failing the job.
                fallback_url = result_url.rstrip("/") + "/response"
                result = await client.get(fallback_url, headers=headers)
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
        if not handle.cancel_url:
            return False
        try:
            headers = {"Authorization": f"Key {self.api_key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(handle.cancel_url, headers=headers)
                return resp.status_code < 300
        except Exception:
            return False

    async def health(self) -> bool:
        return bool(self.api_key)


class SolH3LocalProvider:
    """DGX Spark 本地视频后端（h3-adapter，ComfyUI-H3/Sol 队列）。

    实测协议（h3_adapter.py）：
    - POST {base}/v1/videos/generations  Bearer token
      {prompt, resolution?, aspect_ratio?, duration?,
       reference_images: [url|dataurl], reference_videos: [{data,duration,with_audio}],
       reference_audios: [url|dataurl]}
      → {"request_id": "h3_…", "status": "pending"}
    - GET {base}/v1/videos/{id}
      → {status: pending|running|done|failed|expired|cancelled|draft,
         video:{url}, draft:{url}, error}
    - GET {base}/v1/videos/{id}/content  → mp4 字节（带 token）
    - POST {base}/v1/videos/{id}/cancel  排队直接取消，执行中中断 ComfyUI
    未配置 SOL_H3_BASE_URL 时明确阻塞，不静默丢参考。
    """

    name = "sol_h3_local"

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key

    def capabilities(self) -> dict:
        return {
            "text_to_video": "documented",
            "reference_image": "documented",   # reference_images ≤9
            "reference_audio": "documented",   # reference_audios ≤3
            "reference_video": "documented",   # reference_videos ≤3
            "limits": {"image": 9, "audio": 3, "video": 3},
            "note": "h3-adapter（ComfyUI-H3/Sol）实测协议；未配置 SOL_H3_BASE_URL 时阻塞",
        }

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _adapt_references(self, request: dict) -> dict:
        """Runtime references[]（type/role + path）→ adapter 字段。
        path 为服务器本地路径时转 {public_base_url}/files/…（适配器同机可直接拉）。"""
        imgs: list[str] = []
        vids: list[dict] = []
        auds: list[str] = []
        role_kind = {"identity": "image", "wardrobe": "image", "location": "image",
                     "style": "image", "voice": "audio", "motion": "video",
                     "camera": "video", "reference": "image"}
        for ref in request.get("references") or []:
            path = ref.get("path") or ref.get("url") or ""
            if not path:
                continue
            kind = ref.get("type") or role_kind.get(ref.get("role", ""), "image")
            url = path if path.startswith(("http://", "https://", "data:")) else \
                f"{settings.public_base_url.rstrip('/')}/files/{path.lstrip('/')}"
            if kind == "image" and len(imgs) < 9:
                imgs.append(url)
            elif kind == "video" and len(vids) < 3:
                vids.append({"data": url, "duration": ref.get("duration") or 5.0,
                             "with_audio": False})
            elif kind == "audio" and len(auds) < 3:
                auds.append(url)
        out: dict = {}
        if imgs: out["reference_images"] = imgs
        if vids: out["reference_videos"] = vids
        if auds: out["reference_audios"] = auds
        return out

    async def submit(self, request: dict) -> VideoJobHandle:
        if not self.base_url:
            raise RuntimeError("Sol-H3 local provider not configured (SOL_H3_BASE_URL)")
        shots = request.get("shots") or []
        prompt = request.get("prompt") or " / ".join(
            s.get("title") or s.get("subtitle") or "" for s in shots)
        duration = float(shots[0].get("duration", settings.mock_shot_duration)) if shots else 5.0
        payload: dict = {"prompt": prompt, "duration": duration,
                         "resolution": request.get("resolution") or settings.video_generation_resolution,
                         "aspect_ratio": request.get("aspect_ratio") or settings.generation_aspect_ratio}
        payload.update(self._adapt_references(request))
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/v1/videos/generations",
                                     json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        job_id = data.get("request_id") or data.get("id")
        if not job_id:
            raise RuntimeError(f"sol_h3 adapter submit: no request_id in {data!r}")
        return VideoJobHandle(provider_job_id=str(job_id), provider=self.name)

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        if not self.base_url:
            return VideoJobResult(status="FAILED", error="Sol-H3 local provider not configured")
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(f"{self.base_url}/v1/videos/{handle.provider_job_id}",
                                    headers=self._headers())
            if resp.status_code == 404:
                return VideoJobResult(status="FAILED", error="job expired/unknown", raw=resp.json())
            resp.raise_for_status()
            data = resp.json()
        st = str(data.get("status", "")).lower()
        if st == "done":
            video = data.get("video") or {}
            url = video.get("url")
            if not url:
                return VideoJobResult(status="FAILED", error="sol_h3: done but no video url",
                                      raw=data)
            out = settings.media_path / "clips" / handle.provider_job_id
            out.mkdir(parents=True, exist_ok=True)
            target = out / "clip_1.mp4"
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("GET", url, headers=self._headers()) as r:
                    r.raise_for_status()
                    with open(target, "wb") as f:
                        async for chunk in r.aiter_bytes(1 << 20):
                            f.write(chunk)
            return VideoJobResult(status="READY", video_path=str(out),
                                  raw={"clips": [str(target)], "adapter": data})
        if st in ("failed", "expired", "cancelled"):
            return VideoJobResult(status="FAILED",
                                  error=data.get("error") or st, raw=data)
        # pending / running / draft → 仍在生成
        return VideoJobResult(status="GENERATING", raw=data)

    async def cancel_if_supported(self, handle: VideoJobHandle) -> bool:
        if not self.base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/videos/{handle.provider_job_id}/cancel",
                    headers=self._headers())
                return resp.status_code < 300
        except Exception:
            return False

    async def health(self) -> bool:
        if not self.base_url:
            return False
        try:
            # 无 /health：用鉴权失败的 /v1/videos 探测进程存活（401 也说明服务在）
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/v1/videos?limit=1",
                                        headers=self._headers())
                return resp.status_code in (200, 401, 403)
        except Exception:
            return False


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


class OpenAIImageProvider:
    """OpenAI Images-compatible relay used for Character Studio image tasks.

    The relay accepts Bearer auth and returns the standard ``data[].url``
    response. It is deliberately registered under ``nano_banana_2`` so the
    existing CharacterService and provenance contract remain unchanged.
    """

    name = "image_relay"

    def __init__(self, base_url: str = "", api_key: str = "", model: str = ""):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.model = model or settings.image_provider_model

    def capabilities(self) -> dict:
        return {"image_generation": "openai_compatible", "image_edit": "openai_compatible",
                "endpoint_generation": f"{self.base_url}/v1/images/generations",
                "endpoint_edit": f"{self.base_url}/v1/images/edits",
                "model": self.model, "fallback_model": settings.image_provider_fallback_model}

    @staticmethod
    def _size(resolution: str) -> str:
        return {"0.5K": "512x512", "1K": "1024x1024", "2K": "2048x2048", "4K": "4096x4096"}.get(resolution, "1024x1024")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _request(self, path: str, payload: dict) -> dict:
        if not self.base_url or not self.api_key:
            raise RuntimeError("image relay is not configured")
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/v1/images/{path}",
                                         json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _images(data: dict) -> list[dict]:
        # Standard OpenAI shape: {data:[{url:...}]}.
        items = data.get("data") or data.get("images") or []
        return [x if isinstance(x, dict) else {"url": x} for x in items]

    async def generate(self, request: dict) -> dict:
        resolution = request.get("resolution") or settings.image_generation_resolution
        payload = {"model": request.get("model") or self.model,
                   "prompt": request.get("prompt", ""),
                   "size": self._size(resolution),
                   "quality": request.get("quality", "standard"),
                   "style": request.get("style", "vivid"),
                   "n": max(1, min(int(request.get("num_images", request.get("n", 2))), 10)),
                   "response_format": "url"}
        try:
            data = await self._request("generations", payload)
        except httpx.HTTPStatusError as exc:
            # The relay's alternate model is only used for an explicit model
            # rejection; transient/auth failures are surfaced unchanged.
            if exc.response.status_code not in (400, 404, 422) or not settings.image_provider_fallback_model \
                    or payload["model"] == settings.image_provider_fallback_model:
                raise
            payload["model"] = settings.image_provider_fallback_model
            data = await self._request("generations", payload)
        return {"images": self._images(data), "model": payload["model"],
                "resolution": resolution, "aspect_ratio": request.get("aspect_ratio"),
                "raw": {"provider": self.name, "payload": {k: v for k, v in payload.items() if k != "prompt"}}}

    async def edit(self, request: dict) -> dict:
        resolution = request.get("resolution") or settings.image_generation_resolution
        payload = {"model": request.get("model") or self.model,
                   "prompt": request.get("prompt", ""),
                   "size": self._size(resolution), "quality": request.get("quality", "standard"),
                   "n": 1, "response_format": "url"}
        urls = list(request.get("image_urls") or [])
        if not urls:
            raise RuntimeError("IMAGE_EDIT requires image_urls")
        # Many OpenAI-compatible relays accept image[] as URL strings.
        payload["image"] = urls[:4]
        data = await self._request("edits", payload)
        return {"images": self._images(data), "model": payload["model"],
                "resolution": resolution, "aspect_ratio": request.get("aspect_ratio"),
                "raw": {"provider": self.name, "payload": {k: v for k, v in payload.items() if k not in ("prompt", "image")}}}

    async def health(self) -> bool:
        return bool(self.base_url and self.api_key)


class FalImageProvider:
    """fal.ai Nano Banana 2 角色生图/编图（v0.6 IMAGE-01 / FR-085/086/097）。

    业务层只调逻辑能力 IMAGE_GENERATION / IMAGE_EDIT；具体 endpoint、
    模型 id、key 只存在这个 Adapter，不散落到 Character UI / Runtime。

    - IMAGE_GENERATION → fal-ai/nano-banana-2        （text-to-image, num_images）
    - IMAGE_EDIT       → fal-ai/nano-banana-2/edit   （image_urls + prompt）

    与 FalH3MaxProvider 共用 fal queue 语义：submit 响应返回
    status_url / response_url / cancel_url，轮询 status 到 COMPLETED 后
    取 result（images[]）。结果是非破坏式 Candidate，由调用方落 CharacterAsset。
    """

    name = "nano_banana_2"

    GENERATE_ENDPOINT = "fal-ai/nano-banana-2"
    EDIT_ENDPOINT = "fal-ai/nano-banana-2/edit"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.fal_key

    def capabilities(self) -> dict:
        return {"image_generation": "documented", "image_edit": "documented",
                "num_images_max": 4, "edit_image_urls_max": 4,
                "endpoint_generation": self.GENERATE_ENDPOINT,
                "endpoint_edit": self.EDIT_ENDPOINT}

    async def _submit_and_wait(self, endpoint: str, payload: dict,
                               timeout_s: int = 300) -> dict:
        """提交 queue 任务并轮询到 COMPLETED；返回 result JSON。"""
        _ensure_fal_paid_allowed()
        headers = {"Authorization": f"Key {self.api_key}",
                   "Content-Type": "application/json"}
        base = f"https://queue.fal.run/{endpoint}"
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            try:
                resp = await client.post(base, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise _fal_http_error(exc) from exc
            except httpx.TimeoutException as exc:
                raise FalGenerationError("TIMEOUT", "provider request timed out") from exc
            sub = resp.json()
            status_url = sub.get("status_url")
            response_url = sub.get("response_url")
            if not status_url or not response_url:
                raise RuntimeError(f"fal submit missing queue urls: {sub}")
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                st = await client.get(status_url,
                                      headers={"Authorization": f"Key {self.api_key}"})
                st.raise_for_status()
                body = st.json()
                s = body.get("status", "")
                if s == "COMPLETED":
                    rr = await client.get(response_url,
                                          headers={"Authorization": f"Key {self.api_key}"})
                    rr.raise_for_status()
                    return rr.json()
                if s not in ("IN_QUEUE", "IN_PROGRESS"):
                    raise RuntimeError(f"fal job terminal status={s}: {body}")
                await asyncio.sleep(3)
        raise RuntimeError(f"fal image job timeout after {timeout_s}s")

    async def generate(self, request: dict) -> dict:
        """IMAGE_GENERATION：{prompt, num_images?, resolution?} → images + provenance。"""
        payload = {
            "prompt": request.get("prompt", ""),
            "num_images": min(int(request.get("num_images", 2)), 4),
        }
        payload["resolution"] = request.get("resolution") or settings.image_generation_resolution
        if request.get("aspect_ratio"):
            payload["aspect_ratio"] = request["aspect_ratio"]
        data = await self._submit_and_wait(self.GENERATE_ENDPOINT, payload)
        return {"images": data.get("images", []), "model": self.GENERATE_ENDPOINT,
                "resolution": payload["resolution"], "aspect_ratio": payload.get("aspect_ratio"),
                "raw": {k: v for k, v in data.items() if k != "images"}}

    async def edit(self, request: dict) -> dict:
        """IMAGE_EDIT：{prompt, image_urls:[...]} → {images:[..], model, job}
        非破坏式：返回新 Candidate，不覆盖输入图。"""
        image_urls = list(request.get("image_urls") or [])
        if not image_urls:
            raise RuntimeError("IMAGE_EDIT requires image_urls")
        payload = {"prompt": request.get("prompt", ""),
                   "image_urls": image_urls[:4],
                   "resolution": request.get("resolution") or settings.image_generation_resolution}
        data = await self._submit_and_wait(self.EDIT_ENDPOINT, payload)
        return {"images": data.get("images", []), "model": self.EDIT_ENDPOINT,
                "resolution": payload["resolution"], "aspect_ratio": payload.get("aspect_ratio"),
                "raw": {k: v for k, v in data.items() if k != "images"}}

    async def health(self) -> bool:
        return bool(self.api_key)


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
        "sol_h3_local": SolH3LocalProvider(settings.sol_h3_base_url, settings.sol_h3_api_key),
        "jev": JevDecisionProvider(),
        "nano_banana_2": (OpenAIImageProvider(settings.image_provider_base_url,
                                                settings.image_provider_api_key,
                                                settings.image_provider_model)
                           if settings.image_provider_base_url and settings.image_provider_api_key
                           else FalImageProvider()),
    }
    if mode in ("mock", "hybrid"):
        from .mock_decision import MockDecisionProvider
        from .mock_image import MockImageProvider
        from .mock_text import MockTextProvider
        from .mock_video import MockVideoProvider
        registry["mock_text"] = MockTextProvider()
        registry["mock_decision"] = MockDecisionProvider()
        registry["mock_video"] = MockVideoProvider()
        # mock 模式（或 hybrid 缺 FAL_KEY 时）用确定性生图桩，保证角色链路可测
        if (mode == "mock" and not (settings.image_provider_base_url and settings.image_provider_api_key)) \
                or (not settings.fal_key and not (settings.image_provider_base_url and settings.image_provider_api_key)):
            registry["nano_banana_2"] = MockImageProvider()
    return registry

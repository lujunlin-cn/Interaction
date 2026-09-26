"""真实 Provider：StepFun（OpenAI 兼容）、本地 Nemotron（OpenAI 兼容）、fal.ai H3 Max。

密钥全部来自环境变量；任何 Provider 失效由 Router 统一处理。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import threading
import time
import uuid
from pathlib import Path

import httpx

from ..config import settings
from .base import DecisionAnswer, TextResponse, VideoJobHandle, VideoJobResult
from .reference_images import ReferenceImageError


class FalGenerationError(RuntimeError):
    """分类后的 Fal 错误，供 Router/Runtime 做可审计回退。"""
    def __init__(self, kind: str, message: str, *, submit_uncertain: bool = False,
                 usage_id: str | None = None):
        super().__init__(message)
        self.kind = kind
        self.submit_uncertain = submit_uncertain
        self.usage_id = usage_id


_fal_circuit = {"state": "CLOSED", "reason": "", "opened_at": None, "http_attempts": 0,
                "active_key_index": 0, "rotation_count": 0}
_fal_key_states: list[dict] = []
_usage_ledger_lock = threading.RLock()


def fal_circuit_status() -> dict:
    keys = _configured_fal_keys()
    _sync_fal_key_states(keys)
    return {**_fal_circuit, "keys": [
        {"index": i, "fingerprint": _key_fingerprint(k), "state": _fal_key_states[i]["state"],
         "reason": _fal_key_states[i]["reason"]}
        for i, k in enumerate(keys)
    ]}


def _configured_fal_keys() -> list[str]:
    return [k for k in (settings.fal_key, settings.fal_key_secondary) if k]


def _key_fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:10] if key else "none"


def _sync_fal_key_states(keys: list[str] | None = None) -> None:
    keys = keys if keys is not None else _configured_fal_keys()
    while len(_fal_key_states) < len(keys):
        _fal_key_states.append({"state": "CLOSED", "reason": "", "opened_at": None})
    del _fal_key_states[len(keys):]


def _next_fal_key() -> tuple[int, str] | None:
    keys = _configured_fal_keys()
    _sync_fal_key_states(keys)
    if not keys:
        return None
    start = int(_fal_circuit.get("active_key_index", 0)) % len(keys)
    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        if _fal_key_states[idx]["state"] != "OPEN":
            _fal_circuit["active_key_index"] = idx
            _fal_circuit["state"] = "CLOSED"
            return idx, keys[idx]
    _fal_circuit["state"] = "OPEN"
    return None


def _rotate_fal_key(index: int, reason: str) -> bool:
    keys = _configured_fal_keys()
    _sync_fal_key_states(keys)
    if index < len(_fal_key_states):
        _fal_key_states[index].update({"state": "OPEN", "reason": reason, "opened_at": time.time()})
    _fal_circuit["reason"] = reason
    _fal_circuit["rotation_count"] = int(_fal_circuit.get("rotation_count", 0)) + 1
    if not keys:
        _fal_circuit["state"] = "OPEN"
        return False
    for offset in range(1, len(keys) + 1):
        nxt = (index + offset) % len(keys)
        if _fal_key_states[nxt]["state"] != "OPEN":
            _fal_circuit.update({"state": "CLOSED", "active_key_index": nxt})
            return True
    _fal_circuit["state"] = "OPEN"
    return False


def usage_ledger(limit: int = 200) -> list[dict]:
    """Latest state per attempt, reconstructed from the durable event journal."""
    limit = max(1, min(int(limit), 5000))
    with _usage_ledger_lock:
        return list(reversed(list(_read_usage_ledger().values())[-limit:]))


def _usage_ledger_path() -> Path:
    folder = settings.data_path / ".private"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder / "usage-ledger.jsonl"


def _read_usage_ledger() -> dict[str, dict]:
    items: dict[str, dict] = {}
    path = _usage_ledger_path()
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict) and item.get("id"):
                        items[item["id"]] = item
                except (ValueError, TypeError):
                    # Preserve earlier complete events after an interrupted
                    # final append; never invent a completed provider request.
                    continue
    return items


def _append_usage_event(item: dict) -> None:
    # Record the attempt durably before sending a billable HTTP request. A
    # storage failure therefore stops submission rather than losing audit.
    import fcntl
    path = _usage_ledger_path()
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        size = os.fstat(fd).st_size
        # A process may have stopped midway through its final line. Separate
        # that incomplete event so it cannot swallow the next valid append.
        needs_newline = bool(size and os.pread(fd, 1, size - 1) != b"\n")
        with os.fdopen(fd, "a", encoding="utf-8", closefd=False) as stream:
            if needs_newline:
                stream.write("\n")
            stream.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def _usage_error_label(error: str) -> str:
    # Raw provider bodies can echo prompts, signed URLs or credentials. Only
    # a stable classification enters this journal.
    allowed = {"BILLING_LOCKED", "QUOTA_EXHAUSTED", "AUTH_FAILED", "RATE_LIMITED",
               "TRANSIENT_PROVIDER_ERROR", "INVALID_REQUEST", "INVALID_RESPONSE",
               "TIMEOUT", "NETWORK_ERROR", "PROVIDER_ERROR", "CANCELLED", "REFERENCE_UNAVAILABLE"}
    return error if error in allowed else ("PROVIDER_ERROR" if error else "")


def _record_usage(provider: str, model: str, task: str, request: dict,
                  status: str, blocked_reason: str = "", error: str = "") -> str:
    refs = request.get("references") or []
    image_refs = request.get("reference_image_urls") or request.get("image_urls") or request.get("image") or []
    resolution = request.get("resolution") or {
        "512x512": "0.5K", "1024x1024": "1K", "2048x2048": "2K", "4096x4096": "4K",
    }.get(request.get("size"))
    at = int(time.time() * 1000)
    item = {
        "id": f"usage_{uuid.uuid4().hex}",
        "provider": provider, "model": model, "task": task,
        "request_id": request.get("request_id") or request.get("job_id"),
        "resolution": resolution, "size": request.get("size"),
        "transport": request.get("transport"),
        "aspect_ratio": request.get("aspect_ratio") or ("1:1" if request.get("size") in {
            "512x512", "1024x1024", "2048x2048", "4096x4096"} else None),
        "duration": request.get("duration") or ((request.get("shots") or [{}])[0].get("duration")),
        "num_images": request.get("num_images") or request.get("n"),
        "reference_summary": {
            "images": len(image_refs) + int(bool(request.get("image_url"))) + sum(r.get("type", "image") == "image" for r in refs if isinstance(r, dict)),
            "videos": len(request.get("reference_video_urls") or []) + sum(r.get("type") == "video" for r in refs if isinstance(r, dict)),
            "audios": len(request.get("reference_audio_urls") or []) + sum(r.get("type") == "audio" for r in refs if isinstance(r, dict)),
        },
        "status": status, "blocked_reason": blocked_reason, "error": _usage_error_label(error),
        "external_http_attempts": 1 if status == "SUBMITTED" else 0,
        "at": at, "updated_at": at,
    }
    with _usage_ledger_lock:
        _append_usage_event(item)
    return item["id"]


def _update_usage(usage_id: str | None, status: str, *, request_id: str | None = None,
                  model: str | None = None, error: str = "", http_status: int | None = None) -> None:
    if not usage_id:
        return
    with _usage_ledger_lock:
        item = _read_usage_ledger().get(usage_id)
        if item is None:
            return
        changes = {"status": status, "error": _usage_error_label(error)}
        if request_id:
            changes["request_id"] = request_id
        if model:
            changes["model"] = model
        if http_status is not None:
            changes["http_status"] = http_status
        if all(item.get(key) == value for key, value in changes.items()):
            return
        item.update(changes, updated_at=int(time.time() * 1000))
        _append_usage_event(item)


def reset_fal_circuit() -> None:
    _fal_circuit.update({"state": "CLOSED", "reason": "", "opened_at": None, "http_attempts": 0,
                         "active_key_index": 0, "rotation_count": 0})
    for state in _fal_key_states:
        state.update({"state": "CLOSED", "reason": "", "opened_at": None})


def _ensure_fal_paid_allowed(task: str = "paid_generation", request: dict | None = None,
                             provider: str = "fal", explicit_key: str = "") -> tuple[int | None, str]:
    request = request or {}
    if not settings.fal_paid_generation_enabled:
        _record_usage(provider, "", task, request, "BLOCKED", "PAID_GENERATION_DISABLED")
        raise FalGenerationError("PAID_GENERATION_DISABLED", "provider unavailable: paid generation disabled")
    if _fal_circuit["state"] == "OPEN":
        _record_usage(provider, "", task, request, "BLOCKED", _fal_circuit["reason"] or "CIRCUIT_OPEN")
        raise FalGenerationError(_fal_circuit["reason"] or "BILLING_LOCKED",
                                 f"provider unavailable: {_fal_circuit['reason'] or 'Fal circuit open'}")
    if explicit_key:
        return None, explicit_key
    selected = _next_fal_key()
    if selected is None:
        _record_usage(provider, "", task, request, "BLOCKED", _fal_circuit["reason"] or "CIRCUIT_OPEN")
        raise FalGenerationError(_fal_circuit["reason"] or "BILLING_LOCKED", "provider unavailable: all Fal keys are circuit-open")
    return selected


def _fal_http_error(exc: httpx.HTTPStatusError, key_index: int | None = None) -> FalGenerationError:
    code = exc.response.status_code
    body = exc.response.text[:1000]
    upper = body.upper()
    if "QUOTA" in upper or "INSUFFICIENT" in upper or code == 402:
        if key_index is None:
            _fal_circuit.update({"state": "OPEN", "reason": "QUOTA_EXHAUSTED", "opened_at": time.time()})
        else:
            _rotate_fal_key(key_index, "QUOTA_EXHAUSTED")
        return FalGenerationError("QUOTA_EXHAUSTED", "provider unavailable: quota exhausted")
    if code == 403 and ("TOP_UP" in upper or "USER IS LOCKED" in upper or "BILLING" in upper):
        if key_index is None:
            _fal_circuit.update({"state": "OPEN", "reason": "BILLING_LOCKED", "opened_at": time.time()})
        else:
            _rotate_fal_key(key_index, "BILLING_LOCKED")
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
        if self.name == "nemotron_local" and output_contract and output_contract.get("json_schema"):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "runtime_output", "strict": True,
                                "schema": output_contract["json_schema"]},
            }
        if self.name == "nemotron_local":
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        timeout = (settings.director_local_request_timeout_seconds
                   if self.name == "nemotron_local" else settings.provider_timeout_seconds)
        if self.name == "step_5" and output_contract and output_contract.get("purpose") in {
            "authoring_draft", "authoring_patch", "creator_projection", "mechanic_projection", "character_understanding",
        }:
            timeout = settings.authoring_timeout_seconds
        if self.name == "step_5" and budget and budget.get("timeout_seconds"):
            timeout = float(budget["timeout_seconds"])
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
            request_id=resp.headers.get("x-request-id") or data.get("id"),
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
    REFERENCE_LIMITS = {"image": 9, "audio": 3, "video": 3, "mixed": 12}

    def __init__(self, api_key: str = "", model: str = ""):
        self._explicit_key = api_key
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
            "limits": dict(self.REFERENCE_LIMITS),
            "limits_source": "PRD per-modality caps; Fal API mixed <=12 checked 2026-09-25",
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
        return {k: list(dict.fromkeys(v)) for k, v in out.items() if v}

    async def _verify_public_reference(self, url: str) -> None:
        """Fail before a paid submit when our public asset URL is stale."""
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=True, trust_env=False) as client:
                response = await client.head(url)
                if response.status_code in (405, 501):
                    response = await client.get(url, headers={"Range": "bytes=0-0"})
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if content_type and not content_type.lower().startswith("image/"):
                    raise ReferenceImageError("public reference is not served as an image")
        except (httpx.HTTPError, ReferenceImageError) as exc:
            raise FalGenerationError(
                "REFERENCE_UNAVAILABLE",
                "configured PUBLIC_BASE_URL cannot serve a reference image",
            ) from exc

    async def submit(self, request: dict) -> VideoJobHandle:
        _ensure_fal_paid_allowed("video_generation", request, self.name, self._explicit_key)
        prompt = request.get("prompt", "")
        shots = request.get("shots") or []
        resolution = request.get("resolution") or settings.video_generation_resolution
        aspect_ratio = request.get("aspect_ratio") or settings.generation_aspect_ratio
        if resolution not in {"480P", "768P", "1080P"}:
            raise ValueError(f"H3 Max unsupported resolution: {resolution}")
        if aspect_ratio == "auto":
            aspect_ratio = "adaptive"
        if aspect_ratio not in {"adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}:
            raise ValueError(f"H3 Max unsupported aspect_ratio: {aspect_ratio}")
        try:
            requested_duration = float(shots[0].get("duration", settings.mock_shot_duration)
                                       if shots else request.get("duration", settings.mock_shot_duration))
        except (TypeError, ValueError):
            raise FalGenerationError("INVALID_REQUEST", "H3 duration must be a positive finite integer") from None
        if not math.isfinite(requested_duration) or requested_duration <= 0 or not requested_duration.is_integer():
            raise FalGenerationError("INVALID_REQUEST", "H3 duration must be a positive finite integer")
        # H3 Max requires duration for each independent Shot request.  Runtime
        # deliberately submits one-shot payloads for real multi-shot assembly.
        payload: dict = {
            "prompt": prompt,
            "duration": int(requested_duration),
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "prompt_expansion_mode": "disabled",
        }
        for key in ("image_url", "reference_image_urls", "reference_audio_urls", "reference_video_urls"):
            if request.get(key):
                payload[key] = request[key]
        # references[] → fal 字段适配（G09：不再静默丢失）
        for key, urls in self._adapt_references(request).items():
            payload.setdefault(key, [])
            payload[key] = list(dict.fromkeys(payload[key] + urls))
        reference_fields = {"image": "reference_image_urls", "audio": "reference_audio_urls", "video": "reference_video_urls"}
        counts = {kind: len(payload.get(field, [])) for kind, field in reference_fields.items()}
        if any(counts[kind] > self.REFERENCE_LIMITS[kind] for kind in counts) or sum(counts.values()) > self.REFERENCE_LIMITS["mixed"]:
            raise FalGenerationError("INVALID_REQUEST", "reference count exceeds declared H3 capability")
        # Relay URLs can expire or reject Fal's downloader. Archive exact bytes
        # before any paid submit, and retain their order for the identity map.
        from .reference_images import archive_image
        reference_transport = []
        for field in ("reference_image_urls", "image_url"):
            values = payload.get(field)
            if not values:
                continue
            urls = [values] if isinstance(values, str) else values
            transported = []
            for index, url in enumerate(urls):
                if url.startswith(settings.public_base_url.rstrip("/") + "/files/") or url.startswith(settings.public_base_url.rstrip("/") + "/media/"):
                    await self._verify_public_reference(url)
                    transported.append(url)
                    continue
                try:
                    archived = await archive_image(url)
                except ReferenceImageError as exc:
                    _record_usage(self.name, self.model, "video_generation", payload, "BLOCKED", "REFERENCE_UNAVAILABLE")
                    raise FalGenerationError("REFERENCE_UNAVAILABLE", f"reference image {index} unavailable: {exc}") from None
                public_url = settings.public_base_url.rstrip("/") + archived["url"]
                transported.append(public_url)
                reference_transport.append({**archived, "field": field, "index": index, "public_url": public_url})
            payload[field] = transported[0] if isinstance(values, str) else transported
        keys = [self._explicit_key] if self._explicit_key else _configured_fal_keys()
        attempts = max(1, len(keys))
        last_error: Exception | None = None
        for _ in range(attempts):
            selected = _ensure_fal_paid_allowed("video_generation", request, self.name, self._explicit_key)
            key_index, key = selected
            usage_id = None
            try:
                headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
                async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                    try:
                        usage_id = _record_usage(self.name, self.model, "video_generation", payload, "SUBMITTED")
                        _fal_circuit["http_attempts"] += 1
                        resp = await client.post(self.base, json=payload, headers=headers)
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise _fal_http_error(exc, key_index) from exc
                    except httpx.TimeoutException as exc:
                        uncertain = not isinstance(exc, (httpx.ConnectTimeout, httpx.PoolTimeout))
                        raise FalGenerationError("TIMEOUT", "provider submit outcome is unknown" if uncertain
                            else "provider connection timed out before submit", submit_uncertain=uncertain,
                            usage_id=usage_id) from exc
                    data = resp.json()
                _update_usage(usage_id, "ACCEPTED", request_id=data["request_id"], http_status=resp.status_code)
                return VideoJobHandle(
                    provider_job_id=data["request_id"], provider=self.name,
                    status_url=data.get("status_url"), response_url=data.get("response_url"),
                    cancel_url=data.get("cancel_url"),
                    metadata={"fal_key_index": key_index, "fal_key_fingerprint": _key_fingerprint(key),
                              "usage_id": usage_id, "reference_transport": reference_transport})
            except FalGenerationError as exc:
                _update_usage(usage_id, "SUBMISSION_UNCERTAIN" if exc.submit_uncertain else "FAILED", error=exc.kind)
                last_error = exc
                if self._explicit_key or exc.kind not in {"QUOTA_EXHAUSTED", "BILLING_LOCKED"}:
                    raise
                if _next_fal_key() is None:
                    raise
            except httpx.RequestError as exc:
                uncertain = not isinstance(exc, httpx.ConnectError)
                _update_usage(usage_id, "SUBMISSION_UNCERTAIN" if uncertain else "FAILED", error="NETWORK_ERROR")
                raise FalGenerationError("TRANSIENT_PROVIDER_ERROR", "provider submit outcome is unknown" if uncertain
                    else "provider connection failed before submit", submit_uncertain=uncertain,
                    usage_id=usage_id) from exc
            except (ValueError, KeyError) as exc:
                # A successful HTTP response without a usable job ID does
                # not prove that no billable job was created.
                _update_usage(usage_id, "SUBMISSION_UNCERTAIN", error="INVALID_RESPONSE")
                raise FalGenerationError("INVALID_REQUEST", "provider submit response is missing a usable job identifier",
                                         submit_uncertain=True, usage_id=usage_id) from exc
        if last_error:
            raise last_error
        raise FalGenerationError("BILLING_LOCKED", "provider unavailable: all Fal keys are circuit-open")

    def _status_url(self, handle: VideoJobHandle) -> str:
        if handle.status_url:
            return handle.status_url
        raise RuntimeError(
            "fal handle missing status_url (job submitted before handle-url "
            "support); resubmit the job to obtain queue URLs")

    def recover_handle(self, job_id: str) -> VideoJobHandle:
        """Read-only migration for jobs predating durable queue handles.

        Fal queue URLs use owner/app, without the endpoint's subpath. This
        reconstructs only the documented status/result URLs; never submits.
        New jobs persist the actual URLs from Fal's submit response instead.
        """
        if not job_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in job_id):
            raise ValueError("invalid Fal job identifier")
        root = "https://queue.fal.run/" + "/".join(self.model.split("/")[:2]) + "/requests/" + job_id
        usage = next((entry for entry in usage_ledger(5000)
                      if entry.get("request_id") == job_id and entry.get("provider") == self.name), {})
        return VideoJobHandle(provider=self.name, provider_job_id=job_id,
            status_url=root + "/status", response_url=root,
            metadata={"usage_id": usage.get("id"), "legacy_handle_recovered": True})

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        # Polling and downloading are idempotent reads. A temporary transport
        # failure must not abandon a still-running paid job or buy a new one.
        try:
            return await self._read_status(handle)
        except httpx.RequestError:
            return VideoJobResult(status="GENERATING", raw={"poll_error": "NETWORK_ERROR",
                "request_id": handle.provider_job_id})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (408, 429, 500, 502, 503, 504):
                return VideoJobResult(status="GENERATING", raw={"poll_error": "TRANSIENT_PROVIDER_ERROR",
                    "http_status": exc.response.status_code, "request_id": handle.provider_job_id})
            raise

    async def _read_status(self, handle: VideoJobHandle) -> VideoJobResult:
        usage_id = handle.metadata.get("usage_id")
        key_index = handle.metadata.get("fal_key_index")
        keys = _configured_fal_keys()
        key = keys[int(key_index)] if key_index is not None and int(key_index) < len(keys) else self.api_key
        headers = {"Authorization": f"Key {key}"}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            resp = await client.get(self._status_url(handle), headers=headers)
            resp.raise_for_status()
            st = resp.json().get("status", "")
            if st not in ("COMPLETED",):
                _update_usage(usage_id, "GENERATING" if st in ("IN_PROGRESS", "IN_QUEUE") else "FAILED",
                              request_id=handle.provider_job_id,
                              error="" if st in ("IN_PROGRESS", "IN_QUEUE") else "PROVIDER_ERROR")
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
                # COMPLETED means the queue finished, not that generation
                # succeeded. Keep the original failure; do not guess URLs.
                try:
                    body = result.json()
                    details = body.get("detail", []) if isinstance(body, dict) else []
                except ValueError:
                    details = []
                downloads = [item for item in details if isinstance(item, dict)
                             and item.get("type") == "file_download_error"] if isinstance(details, list) else []
                indices = [item["loc"][-1] for item in downloads if isinstance(item.get("loc"), list)
                           and item["loc"] and isinstance(item["loc"][-1], int)]
                kind = "REFERENCE_UNAVAILABLE" if downloads else "INVALID_REQUEST"
                _update_usage(usage_id, "FAILED", request_id=handle.provider_job_id, error=kind, http_status=422)
                return VideoJobResult(status="FAILED", error=f"{kind}: Fal rejected the completed job (422)",
                    raw={"http_status": 422, "request_id": handle.provider_job_id,
                         "reference_indices": indices, "error_kind": kind})
            result.raise_for_status()
            data = result.json()
        video_url = (data.get("video") or {}).get("url") or data.get("video_url")
        if not video_url:
            _update_usage(usage_id, "FAILED", request_id=handle.provider_job_id, error="INVALID_RESPONSE")
            return VideoJobResult(status="FAILED", error="fal response has no video url", raw=data)
        _update_usage(usage_id, "SUCCEEDED", request_id=handle.provider_job_id)
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
            key_index = handle.metadata.get("fal_key_index")
            keys = _configured_fal_keys()
            key = keys[int(key_index)] if key_index is not None and int(key_index) < len(keys) else self.api_key
            headers = {"Authorization": f"Key {key}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(handle.cancel_url, headers=headers)
                if resp.status_code < 300:
                    _update_usage(handle.metadata.get("usage_id"), "CANCEL_REQUESTED",
                                  request_id=handle.provider_job_id, http_status=resp.status_code)
                return resp.status_code < 300
        except Exception:
            return False

    async def health(self) -> bool:
        return bool(self._explicit_key or _configured_fal_keys())


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
        resolution = request.get("resolution") or settings.video_generation_resolution
        aspect_ratio = request.get("aspect_ratio") or settings.generation_aspect_ratio
        if resolution not in {"480P", "768P", "1080P"}:
            raise ValueError(f"Sol-H3 unsupported resolution: {resolution}")
        if aspect_ratio not in {"auto", "16:9", "9:16", "1:1"}:
            raise ValueError(f"Sol-H3 unsupported aspect_ratio: {aspect_ratio}")
        payload: dict = {"prompt": prompt, "duration": duration,
                         "resolution": resolution, "aspect_ratio": aspect_ratio}
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
                "model": self.model, "fallback_model": settings.image_provider_fallback_model,
                "fallback_model_2": settings.image_provider_fallback_model_2,
                "fallback_model_3": settings.image_provider_fallback_model_3}

    @staticmethod
    def _size(resolution: str) -> str:
        sizes = {"0.5K": "512x512", "1K": "1024x1024", "2K": "2048x2048", "4K": "4096x4096"}
        if resolution not in sizes:
            raise ValueError(f"image provider unsupported resolution: {resolution}")
        return sizes[resolution]

    def _headers(self, multipart: bool = False) -> dict:
        # httpx must set the multipart boundary itself; sending a JSON content
        # type with a file body is rejected by a number of OpenAI-compatible
        # relays. The upstream failure cause must still be verified live.
        if multipart:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _request(self, path: str, payload: dict) -> dict:
        if not self.base_url or not self.api_key:
            raise RuntimeError("image relay is not configured")
        multipart_files = payload.get("_multipart_files") or []
        if path == "edits" and not multipart_files and payload.get("_source_urls"):
            multipart_files = await self._read_edit_sources(list(payload["_source_urls"]))
            payload["_multipart_files"] = multipart_files
        multipart = bool(multipart_files)
        request_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            usage_id = _record_usage(self.name, request_payload["model"],
                                     "image_edit" if path == "edits" else "image_generation",
                                     {**request_payload, "transport": "multipart/form-data" if multipart else "application/json"}, "SUBMITTED")
            try:
                if multipart:
                    # OpenAI-compatible edit contract: scalar options are form
                    # fields and each source image is an uploaded file.
                    form = {k: str(v) for k, v in request_payload.items() if k != "image"}
                    response = await client.post(
                        f"{self.base_url}/v1/images/{path}", data=form,
                        files=multipart_files, headers=self._headers(multipart=True))
                else:
                    response = await client.post(f"{self.base_url}/v1/images/{path}",
                                                 json=request_payload, headers=self._headers())
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not any(img.get("url") for img in self._images(data)):
                    raise ValueError("invalid image response")
                # Some relays only expose the external ID in a header.
                response_id = response.headers.get("x-request-id") or response.headers.get("request-id")
                if response_id:
                    data["_response_request_id"] = response_id
                _update_usage(usage_id, "SUCCEEDED", request_id=data.get("request_id") or data.get("id") or response_id,
                              model=data.get("model") or payload["model"], http_status=response.status_code)
                return data
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                kind = ("AUTH_FAILED" if code in (401, 403) else "QUOTA_EXHAUSTED" if code == 402
                        else "RATE_LIMITED" if code == 429 else "INVALID_REQUEST" if code in (400, 404, 422)
                        else "TRANSIENT_PROVIDER_ERROR")
                _update_usage(usage_id, "FAILED", request_id=exc.response.headers.get("x-request-id"),
                              error=kind, http_status=code)
                raise
            except httpx.TimeoutException:
                _update_usage(usage_id, "FAILED", error="TIMEOUT")
                raise
            except httpx.RequestError:
                _update_usage(usage_id, "FAILED", error="NETWORK_ERROR")
                raise
            except (ValueError, TypeError):
                _update_usage(usage_id, "FAILED", error="INVALID_RESPONSE")
                raise RuntimeError("image relay returned an invalid response") from None

    @staticmethod
    def _unsupported_model(exc: httpx.HTTPStatusError) -> bool:
        if exc.response.status_code not in (400, 404, 422):
            return False
        try:
            data = exc.response.json()
        except ValueError:
            return False
        error = data.get("error", data) if isinstance(data, dict) else {}
        if not isinstance(error, dict):
            return False
        code = str(error.get("code") or error.get("type") or "").lower()
        if code in {"model_not_found", "unsupported_model", "invalid_model", "model_not_supported"}:
            return True
        message = str(error.get("message", "")).lower()
        return any(term in message for term in (
            "model does not exist", "model not found", "model is not supported", "unsupported model", "unknown model")) \
            or (error.get("param") == "model" and any(term in message for term in (
                "does not exist", "not found", "not supported", "unsupported")))

    @staticmethod
    def _images(data: dict) -> list[dict]:
        # Standard OpenAI shape: {data:[{url:...}]}.
        items = data.get("data") or data.get("images") or []
        return [x if isinstance(x, dict) else {"url": x} for x in items]

    def _result(self, data: dict, payload: dict, request: dict, resolution: str) -> dict:
        images = self._images(data)
        dimensions = []
        for img in images:
            width, height = img.get("width"), img.get("height")
            if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
                dimensions.append({"width": width, "height": height})
            else:
                dimensions.append(None)
        actual_ratio = data.get("aspect_ratio")
        if not actual_ratio and dimensions and dimensions[0]:
            width, height = dimensions[0]["width"], dimensions[0]["height"]
            divisor = math.gcd(width, height)
            actual_ratio = f"{width // divisor}:{height // divisor}"
        # Size is the OpenAI Images contract actually sent to the relay. Do
        # not label the caller's requested video aspect as an observed image
        # aspect: the existing relay contract requests square image sizes.
        requested_width, requested_height = (int(n) for n in payload["size"].split("x"))
        divisor = math.gcd(requested_width, requested_height)
        submitted_ratio = f"{requested_width // divisor}:{requested_height // divisor}"
        requested_ratio = request.get("aspect_ratio")
        normalized = requested_ratio not in (None, "", "adaptive", submitted_ratio)
        return {
            "images": images,
            "provider": self.name,
            "model": data.get("model") or payload["model"],
            "requested_model": request.get("model") or self.model,
            "request_id": data.get("request_id") or data.get("id") or data.get("_response_request_id"),
            "resolution": data.get("resolution") or resolution,
            "requested_resolution": resolution,
            "aspect_ratio": actual_ratio or submitted_ratio,
            "requested_aspect_ratio": requested_ratio,
            "actual_aspect_ratio": actual_ratio,
            "requested_size": payload["size"],
            "output_dimensions": dimensions,
            "transport": "multipart/form-data" if payload.get("_source_urls") else "application/json",
            "source_image_sha256": [hashlib.sha256(part[1][1]).hexdigest() for part in payload.get("_multipart_files", [])],
            "normalization": ({"aspect_ratio": {"requested": requested_ratio,
                                "submitted": submitted_ratio,
                                "reason": "OpenAI-compatible relay uses square size presets"}}
                              if normalized else {}),
            "raw": {"provider": self.name,
                    "payload": {k: v for k, v in payload.items() if k not in ("prompt", "image") and not k.startswith("_")}},
        }

    async def generate(self, request: dict) -> dict:
        resolution = request.get("resolution") or settings.image_generation_resolution
        payload = {"model": request.get("model") or self.model,
                   "prompt": request.get("prompt", ""),
                   "size": self._size(resolution),
                   "quality": request.get("quality", "standard"),
                   "style": request.get("style", "vivid"),
                   "n": max(1, min(int(request.get("num_images", request.get("n", 2))), 10)),
                   "response_format": "url"}
        data = await self._request_with_model_fallback("generations", payload)
        return self._result(data, payload, request, resolution)

    async def _read_edit_sources(self, urls: list[str]) -> list[tuple[str, tuple[str, bytes, str]]]:
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds, follow_redirects=True) as client:
            for index, url in enumerate(urls[:4]):
                if url.startswith("/files/"):
                    from urllib.parse import unquote
                    relative = Path(unquote(url.removeprefix("/files/")))
                    local = (settings.data_path / relative).resolve()
                    if any(part.startswith(".") for part in relative.parts) or not local.is_relative_to(settings.data_path.resolve()):
                        raise ValueError("IMAGE_EDIT requires a public image asset")
                    if local.stat().st_size > 50 * 1024 * 1024:
                        raise ValueError("IMAGE_EDIT source image exceeds 50 MB")
                    content = local.read_bytes()
                elif url.startswith("http://") or url.startswith("https://"):
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 50 * 1024 * 1024:
                                raise ValueError("IMAGE_EDIT source image exceeds 50 MB")
                        content = bytes(content)
                else:
                    raise ValueError("IMAGE_EDIT source must be an http(s) URL or local /files asset")
                if content.startswith(b"\x89PNG\r\n\x1a\n"):
                    extension, mime = "png", "image/png"
                elif content.startswith(b"\xff\xd8\xff"):
                    extension, mime = "jpg", "image/jpeg"
                elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
                    extension, mime = "webp", "image/webp"
                else:
                    raise ValueError("IMAGE_EDIT requires a PNG, JPEG or WebP image")
                # The relay follows the OpenAI multipart contract: repeated
                # ``image`` fields carry multiple source images.  Some
                # clients use ``image[]``, but this relay ignores that field
                # name and reports image_input_required.
                files.append(("image", (f"reference-{index}.{extension}", content, mime)))
        return files

    async def edit(self, request: dict) -> dict:
        resolution = request.get("resolution") or settings.image_generation_resolution
        payload = {"model": request.get("model") or self.model,
                   "prompt": request.get("prompt", ""),
                   "size": self._size(resolution), "quality": request.get("quality", "standard"),
                   "n": 1, "response_format": "url"}
        urls = list(request.get("image_urls") or [])
        if not urls:
            raise RuntimeError("IMAGE_EDIT requires image_urls")
        payload["image"] = urls[:4]
        # Resolve URLs inside the transport adapter, after the provider/model
        # route has been selected. Tests and offline contract probes can still
        # stub _request without downloading external media.
        payload["_source_urls"] = urls[:4]
        data = await self._request_with_model_fallback("edits", payload)
        return self._result(data, payload, request, resolution)

    async def _request_with_model_fallback(self, path: str, payload: dict) -> dict:
        """Try the configured Relay model, then explicit Relay fallbacks.

        A fallback is allowed only for provider/model rejection or transient
        provider failure. Authentication, quota and invalid-request failures
        stop immediately; Fal is never consulted by this path.
        """
        requested_model = payload["model"]
        models = [requested_model]
        for model in (settings.image_provider_fallback_model,
                      settings.image_provider_fallback_model_2,
                      settings.image_provider_fallback_model_3):
            if model and model not in models:
                models.append(model)
        last: Exception | None = None
        for index, model in enumerate(models):
            payload["model"] = model
            try:
                return await self._request(path, payload)
            except httpx.HTTPStatusError as exc:
                last = exc
                code = exc.response.status_code
                retryable = self._unsupported_model(exc) or code in (500, 502, 503, 504)
                if not retryable or index == len(models) - 1:
                    raise
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last = exc
                if index == len(models) - 1:
                    raise
        assert last is not None
        raise last

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
        self._explicit_key = api_key
        self.api_key = api_key or settings.fal_key

    def capabilities(self) -> dict:
        return {"image_generation": "documented", "image_edit": "documented",
                "num_images_max": 4, "edit_image_urls_max": 4,
                "endpoint_generation": self.GENERATE_ENDPOINT,
                "endpoint_edit": self.EDIT_ENDPOINT}

    async def _submit_and_wait(self, endpoint: str, payload: dict,
                               timeout_s: int = 300) -> dict:
        """提交 queue 任务并轮询到 COMPLETED；返回 result JSON。"""
        task = "image_edit" if endpoint.endswith("/edit") else "image_generation"
        base = f"https://queue.fal.run/{endpoint}"
        keys = [self._explicit_key] if self._explicit_key else _configured_fal_keys()
        attempts = max(1, len(keys))
        for _ in range(attempts):
            key_index, key = _ensure_fal_paid_allowed(task, payload, self.name, self._explicit_key)
            headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
            usage_id = None
            try:
                async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
                    try:
                        usage_id = _record_usage(self.name, endpoint, task, payload, "SUBMITTED")
                        _fal_circuit["http_attempts"] += 1
                        resp = await client.post(base, json=payload, headers=headers)
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise _fal_http_error(exc, key_index) from exc
                    except httpx.TimeoutException as exc:
                        raise FalGenerationError("TIMEOUT", "provider request timed out") from exc
                    sub = resp.json()
                    request_id = sub.get("request_id")
                    _update_usage(usage_id, "ACCEPTED", request_id=request_id, http_status=resp.status_code)
                    status_url = sub.get("status_url")
                    response_url = sub.get("response_url")
                    if not status_url or not response_url:
                        raise RuntimeError(f"fal submit missing queue urls: {sub}")
                    deadline = time.time() + timeout_s
                    while time.time() < deadline:
                        st = await client.get(status_url, headers={"Authorization": f"Key {key}"})
                        st.raise_for_status()
                        body = st.json()
                        s = body.get("status", "")
                        if s == "COMPLETED":
                            rr = await client.get(response_url, headers={"Authorization": f"Key {key}"})
                            rr.raise_for_status()
                            result = rr.json()
                            result.setdefault("request_id", request_id)
                            _update_usage(usage_id, "SUCCEEDED", request_id=request_id)
                            return result
                        if s not in ("IN_QUEUE", "IN_PROGRESS"):
                            raise RuntimeError(f"fal job terminal status={s}: {body}")
                        await asyncio.sleep(3)
                    raise FalGenerationError("TIMEOUT", "provider image job timed out")
            except FalGenerationError as exc:
                _update_usage(usage_id, "FAILED", error=exc.kind)
                if self._explicit_key or exc.kind not in {"QUOTA_EXHAUSTED", "BILLING_LOCKED"}:
                    raise
                if _next_fal_key() is None:
                    raise
            except httpx.HTTPStatusError as exc:
                _update_usage(usage_id, "FAILED", error="PROVIDER_ERROR", http_status=exc.response.status_code)
                raise
            except httpx.TimeoutException:
                _update_usage(usage_id, "FAILED", error="TIMEOUT")
                raise
            except httpx.RequestError:
                _update_usage(usage_id, "FAILED", error="NETWORK_ERROR")
                raise
            except (ValueError, TypeError, RuntimeError):
                _update_usage(usage_id, "FAILED", error="INVALID_RESPONSE")
                raise
        raise FalGenerationError("BILLING_LOCKED", "provider unavailable: all Fal keys are circuit-open")

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
                "request_id": data.get("request_id"),
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
                "request_id": data.get("request_id"),
                "resolution": payload["resolution"], "aspect_ratio": payload.get("aspect_ratio"),
                "raw": {k: v for k, v in data.items() if k != "images"}}

    async def health(self) -> bool:
        return bool(self._explicit_key or _configured_fal_keys())


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
                           if settings.image_provider_base_url or settings.image_provider_api_key
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
        if (mode == "mock" and not (settings.image_provider_base_url or settings.image_provider_api_key)) \
                or (not (settings.fal_key or settings.fal_key_secondary)
                    and not (settings.image_provider_base_url or settings.image_provider_api_key)):
            registry["nano_banana_2"] = MockImageProvider()
    return registry

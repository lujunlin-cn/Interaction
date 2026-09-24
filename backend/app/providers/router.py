"""ProviderRouter —— 统一管理 timeout / retry / circuit breaker / fallback / route / trace（PRD 14.6 / Q70）。

- Agent 不直接绑定 SDK，不散落降级逻辑；所有角色路由集中在这里。
- Profile 约束在路由前生效：VIDEO_LOCAL_PROFILE 中 nemotron_local 不可用。
- 每次路由产生 ProviderRouteRecord；fallback 记录 primary_error。
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Optional

import httpx

from ..config import settings
from ..domain.ids import uid
from ..domain.schemas import ProviderRouteRecord, RuntimeProfile

# PRD 冻结矩阵（live 模式）
LIVE_ROUTES: dict[str, list[str]] = {
    "director": ["nemotron_local", "step_5"],
    "narrative": ["step_37", "nemotron_local"],
    "production": ["nemotron_local", "step_37"],
    "authoring": ["step_5"],
    "decision": ["jev"],
    "cloud_video": ["h3_max"],
    "local_video": ["sol_h3_local"],
}

# 开发 / 离线演示路由：Mock 只替换 Provider，不替换业务 Runtime
MOCK_ROUTES: dict[str, list[str]] = {
    "director": ["mock_text"],
    "narrative": ["mock_text"],
    "production": ["mock_text"],
    "authoring": ["mock_text"],
    "decision": ["mock_decision"],
    "cloud_video": ["mock_video"],
    "local_video": ["mock_video"],
}

# 混合部署（PRD Q21）：文本与决策走真实 Provider，视频首选真实 H3/Sol。
# 末位挂 Mock 作为显式降级兜底（degraded mode）：路由记录与开发者矩阵可见，
# 保证冷启动/外部 API 抖动时不丢玩家输入；Mock 不替代真实接入验收。
HYBRID_ROUTES: dict[str, list[str]] = {
    "director": ["nemotron_local", "step_5", "mock_text"],
    "narrative": ["step_37", "nemotron_local", "mock_text"],
    "production": ["nemotron_local", "step_37", "mock_text"],
    "authoring": ["step_5", "mock_text"],
    "decision": ["jev", "mock_decision"],
    "cloud_video": ["h3_max", "mock_video"],
    "local_video": ["sol_h3_local", "mock_video"],
}

_MODE_ROUTES = {"live": LIVE_ROUTES, "hybrid": HYBRID_ROUTES}


def _with_durations(timeline: list[dict]) -> list[dict]:
    """G22：给七态 timeline 补每态停留时长（duration_ms）。"""
    out = []
    for i, t in enumerate(timeline):
        nxt = timeline[i + 1]["at"] if i + 1 < len(timeline) else t["at"]
        out.append({**t, "duration_ms": nxt - t["at"]})
    return out

# Runtime Profile 可用性（PRD 14.4）
PROFILE_AVAILABLE = {
    RuntimeProfile.AGENT_LOCAL: {"nemotron_local", "jev", "step_37", "step_5", "h3_max",
                                 "mock_text", "mock_decision", "mock_video"},
    RuntimeProfile.VIDEO_LOCAL: {"sol_h3_local", "jev", "step_37", "step_5", "h3_max",
                                 "mock_text", "mock_decision", "mock_video"},
}

RETRYABLE = "retryable_transient"


class ProviderError(Exception):
    def __init__(self, kind: str, message: str, provider: str = ""):
        super().__init__(message)
        self.kind = kind        # retryable_transient / provider_unhealthy / schema_failure /
                                # permanent_request_error / policy_rejection / profile_unavailable
        self.provider = provider


class DirectorAdmissionRejected(Exception):
    """Local capacity limit; it must not count as a model health failure."""


class ProviderBlocked(Exception):
    def __init__(self, role: str, reasons: list[dict[str, str]], permanent: bool = False):
        super().__init__(f"no available provider for role={role}")
        self.role = role
        self.reasons = reasons
        self.permanent = permanent


class _Health:
    def __init__(self) -> None:
        self.status = "unknown"        # unknown / healthy / unhealthy / circuit_open
        self.errors = 0
        self.last_error: Optional[str] = None
        self.circuit = "CLOSED"        # CLOSED / OPEN

    def to_dict(self) -> dict:
        return {"status": self.status, "errors": self.errors,
                "last_error": self.last_error, "circuit": self.circuit}


class ProviderRouter:
    def __init__(self, registry: dict[str, Any], mode: str = "mock",
                 profile: RuntimeProfile = RuntimeProfile.AGENT_LOCAL):
        self.registry = registry
        self.mode = mode
        self.profile = profile
        self.routes = _MODE_ROUTES.get(mode, MOCK_ROUTES)
        self.health: dict[str, _Health] = {k: _Health() for k in registry}
        self.events: list[dict] = []          # ProviderRouteEvent（同时由上层落库）
        self.on_route_event: Optional[Callable[[dict], None]] = None
        # Profile 切换状态机（FR-064/078、AT-56）：IDLE 之外的状态表示切换进行中
        self.profile_state = "ACTIVE"   # ACTIVE/DRAINING/PERSISTING/STOPPING/
                                        # STARTING_TARGET/HEALTH_CHECK/FAILED_RECOVERABLE
        self.profile_history: list[dict] = []
        self._director_slots = asyncio.Semaphore(max(1, settings.director_local_max_concurrency))
        self._director_queue = 0
        self._director_queue_rejected = 0
        self._director_admission_until = 0.0

    # 每个 Profile 必需的本地服务（缺失/不健康则切换失败并回滚）
    PROFILE_REQUIRED = {
        RuntimeProfile.AGENT_LOCAL: ["nemotron_local"],
        RuntimeProfile.VIDEO_LOCAL: ["sol_h3_local"],
    }

    async def switch_profile(self, target: RuntimeProfile, drain_check=None) -> dict:
        """AGENT_LOCAL ↔ VIDEO_LOCAL 原子切换：drain → persist → stop → start → 健康检查。

        健康检查失败回滚到旧 Profile（FAILED_RECOVERABLE → ACTIVE）。切换期间路由不变。
        """
        if target == self.profile and self.profile_state == "ACTIVE":
            return {"ok": True, "profile": target.value, "unchanged": True}
        if self.profile_state != "ACTIVE":
            raise ProviderError("profile_unavailable", "另一个 Profile 切换正在进行")
        timeline: list[dict] = []

        def mark(state: str) -> None:
            self.profile_state = state
            timeline.append({"state": state, "at": int(time.time() * 1000)})

        old = self.profile
        mark("DRAINING")
        if drain_check is not None:
            # 等待在途生成排空（超时 15s，强制继续，任务会自然结束）
            drained = False
            for _ in range(150):
                if await drain_check():
                    drained = True
                    break
                await asyncio.sleep(0.1)
            if not drained:
                self.profile_state = "ACTIVE"
                raise ProviderError("profile_lifecycle", "active jobs did not drain within 15s")
        mark("PERSISTING")     # Session 状态本就每步落库；此处是显式边界
        mark("STOPPING")
        lifecycle = []
        if settings.profile_lifecycle_enabled:
            # Single-GPU Spark: release the currently active model before
            # starting the target service.  Commands are deliberately explicit
            # so the transition can be audited from the returned evidence.
            old_container = (settings.nemotron_container if old == RuntimeProfile.AGENT_LOCAL
                             else settings.video_local_container)
            target_container = (settings.nemotron_container if target == RuntimeProfile.AGENT_LOCAL
                                else settings.video_local_container)
            lifecycle.append({"action": "stop", "container": old_container,
                              "profile": old.value,
                              "executor": self._lifecycle_executor(old, "stop")})
            try:
                await self._stop_service(old, old_container)
            except ProviderError:
                self.profile_state = "ACTIVE"
                raise
            lifecycle.append({"action": "release_resources", "container": old_container})
            await asyncio.sleep(0.2)
            lifecycle.append({"action": "start", "container": target_container,
                              "profile": target.value,
                              "executor": self._lifecycle_executor(target, "start")})
            try:
                await self._start_service(target, target_container)
            except ProviderError:
                # Best effort restore of the old service before surfacing the
                # failed transition to the caller.
                await self._start_service(old, old_container)
                self.profile_state = "ACTIVE"
                raise
        mark("STARTING_TARGET")
        self.profile = target          # 原子切换：后续路由立刻按新 Profile 计算
        mark("HEALTH_CHECK")
        failed: list[str] = []
        for pid in self.PROFILE_REQUIRED.get(target, []):
            provider = self.registry.get(pid)
            if provider is None:
                continue               # mock 注册表无真实本地服务，跳过
            ok = False
            # Nemotron NVFP4 cold start on Spark takes ~2 minutes to load 52
            # shards before CUDA graph capture; allow a full five-minute boot.
            for _ in range(150 if settings.profile_lifecycle_enabled else 1):
                try:
                    ok = await asyncio.wait_for(provider.health(), timeout=10)
                    if ok and settings.profile_lifecycle_enabled:
                        ok = await self._target_running(target, target_container)
                except Exception:          # noqa: BLE001
                    ok = False
                if ok:
                    break
                await asyncio.sleep(2)
            if not ok:
                failed.append(pid)
        if failed:
            self.profile = old         # 回滚
            if settings.profile_lifecycle_enabled:
                await self._stop_service(target, target_container)
                await self._start_service(old, old_container)
                lifecycle.extend([{"action": "stop", "container": target_container},
                                  {"action": "restore", "container": old_container}])
            mark("FAILED_RECOVERABLE")
            self.profile_state = "ACTIVE"
            self.profile_history.append(
                {"from": old.value, "to": target.value, "result": "rolled_back",
                 "failed_health": failed, "timeline": _with_durations(timeline)})
            return {"ok": False, "profile": old.value, "restored": True,
                    "failed_health": failed, "timeline": _with_durations(timeline),
                    "lifecycle": lifecycle}
        mark("ACTIVE")
        self.profile_history.append(
            {"from": old.value, "to": target.value, "result": "switched",
             "timeline": _with_durations(timeline)})
        return {"ok": True, "profile": target.value,
                "timeline": _with_durations(timeline), "lifecycle": lifecycle}

    @staticmethod
    async def _docker(action: str, container: str) -> None:
        """Run a bounded Docker lifecycle command for real local profile switches."""
        proc = await asyncio.create_subprocess_exec(
            "docker", action, container,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _out, err = await asyncio.wait_for(proc.communicate(), timeout=45)
        if proc.returncode != 0:
            raise ProviderError("profile_lifecycle", err.decode(errors="replace")[-500:])

    @staticmethod
    async def _command(command: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "bash", "-lc", command,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            raise ProviderError("profile_lifecycle", err.decode(errors="replace")[-500:])

    @classmethod
    async def _stop_service(cls, profile: RuntimeProfile, container: str) -> None:
        if profile == RuntimeProfile.VIDEO_LOCAL and settings.video_local_stop_command:
            await cls._command(settings.video_local_stop_command)
        else:
            await cls._docker("stop", container)

    @staticmethod
    def _lifecycle_executor(profile: RuntimeProfile, action: str) -> str:
        if profile == RuntimeProfile.VIDEO_LOCAL and (
                settings.video_local_stop_command if action == "stop"
                else settings.video_local_start_command):
            return "host_process_command"
        return "docker"

    @classmethod
    async def _start_service(cls, profile: RuntimeProfile, container: str) -> None:
        if profile == RuntimeProfile.VIDEO_LOCAL and settings.video_local_start_command:
            await cls._command(settings.video_local_start_command)
        else:
            await cls._docker("start", container)

    @classmethod
    async def _target_running(cls, profile: RuntimeProfile, container: str) -> bool:
        if profile == RuntimeProfile.VIDEO_LOCAL and settings.video_local_process_pattern:
            proc = await asyncio.create_subprocess_exec(
                "pgrep", "-f", settings.video_local_process_pattern,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0 and bool(out.strip())
        return await cls._container_running(container)

    @staticmethod
    async def _container_running(container: str) -> bool:
        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", "--format", "{{.State.Running}}", container,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0 and out.strip() == b"true"

    def profile_status(self) -> dict:
        return {"profile": self.profile.value, "state": self.profile_state,
                "history": self.profile_history[-10:]}

    # ------------------------------------------------------------------
    def _classify(self, exc: Exception) -> str:
        if isinstance(exc, ProviderError):
            return exc.kind
        if isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
            return "retryable_transient"
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            if code == 429 or code >= 500:
                return "retryable_transient"
            if code in (401, 403):
                return "policy_rejection"
            return "permanent_request_error"
        return "provider_unhealthy"

    def _available_by_profile(self, provider_id: str) -> bool:
        return provider_id in PROFILE_AVAILABLE.get(self.profile, set())

    def _health_ok(self, provider_id: str) -> tuple[bool, str]:
        h = self.health.get(provider_id)
        if h is None:
            return False, "unregistered"
        if h.circuit == "OPEN":
            return False, "circuit_open"
        if h.status in ("unhealthy",):
            return False, h.last_error or "unhealthy"
        return True, "ok"

    def route(self, role: str, branch_id: str | None = None, record: bool = True) -> tuple[Any, ProviderRouteRecord]:
        chain = self.routes.get(role, [])
        primary = chain[0] if chain else ""
        skipped: list[dict[str, str]] = []
        chosen: Optional[str] = None
        primary_health = self.health.get(primary)
        if primary_health and primary_health.last_error in ("policy_rejection", "permanent_request_error"):
            rec = ProviderRouteRecord(role=role, primary=primary, selected=None, status="blocked",
                                      reason=[{"provider": primary, "reason": primary_health.last_error}],
                                      profile=self.profile.value)
            if record:
                self._emit(rec, branch_id)
            raise ProviderBlocked(role, rec.reason, permanent=True)
        for pid in chain:
            if pid not in self.registry:
                skipped.append({"provider": pid, "reason": "unregistered"})
                continue
            if not self._available_by_profile(pid):
                skipped.append({"provider": pid, "reason": "profile_unavailable"})
                continue
            if role == "director" and pid == "nemotron_local" and \
                    time.monotonic() < self._director_admission_until:
                skipped.append({"provider": pid, "reason": "admission_limited"})
                continue
            ok, why = self._health_ok(pid)
            if not ok:
                skipped.append({"provider": pid, "reason": why})
                continue
            chosen = pid
            break
        rec = ProviderRouteRecord(
            role=role, primary=primary, selected=chosen,
            status="healthy" if chosen == primary else ("fallback" if chosen else "blocked"),
            reason=skipped, profile=self.profile.value,
            model=getattr(self.registry.get(chosen), "model", None) if chosen else None,
            version=getattr(self.registry.get(chosen), "name", None) if chosen else None,
        )
        if record:
            self._emit(rec, branch_id)
        if chosen is None:
            raise ProviderBlocked(role, skipped)
        return self.registry[chosen], rec

    def _emit(self, rec: ProviderRouteRecord, branch_id: str | None) -> None:
        event = {"id": uid("route"), "branch_id": branch_id, **rec.model_dump()}
        self.events.append(event)
        self.events = self.events[-500:]
        if self.on_route_event:
            self.on_route_event(event)

    # ------------------------------------------------------------------
    def _mark_failure(self, provider_id: str, kind: str) -> None:
        h = self.health.setdefault(provider_id, _Health())
        h.errors += 1
        h.last_error = kind
        if kind in ("provider_unhealthy", "retryable_transient") and \
                h.errors >= settings.provider_circuit_threshold:
            h.circuit = "OPEN"
            h.status = "unhealthy"
        elif kind in ("policy_rejection", "permanent_request_error"):
            h.status = "unhealthy"

    def _mark_success(self, provider_id: str) -> None:
        h = self.health.setdefault(provider_id, _Health())
        h.status = "healthy"
        h.errors = 0
        h.circuit = "CLOSED"

    def recover_all(self) -> None:
        for h in self.health.values():
            h.status = "healthy"
            h.errors = 0
            h.circuit = "CLOSED"
            h.last_error = None

    def inject_failure(self, provider_id: str, kind: str = "retryable_transient") -> None:
        """开发/验收用的故障注入。"""
        h = self.health.setdefault(provider_id, _Health())
        h.status = "unhealthy"
        h.last_error = kind
        if kind == "circuit_open":
            h.circuit = "OPEN"

    # ------------------------------------------------------------------
    async def call_text(self, role: str, messages: list[dict], output_contract: dict | None = None,
                        budget: dict | None = None, branch_id: str | None = None,
                        allow_retry: bool = False) -> tuple[Any, ProviderRouteRecord, Any]:
        """按角色路由调用文本模型。fallback 链上的 Provider 复用同一输入/输出契约。"""
        last_exc: Optional[Exception] = None
        # 至少把 fallback 链上的每个 Provider 试一遍；allow_retry 时整链再重试一次
        chain_len = max(1, len(self.routes.get(role, [])))
        attempts = chain_len * (2 if allow_retry else 1)
        for _ in range(attempts):
            try:
                provider, rec = self.route(role, branch_id)
            except ProviderBlocked:
                raise
            t0 = time.time()
            acquired_director = False
            try:
                if role == "director" and rec.selected == "nemotron_local":
                    if not await asyncio.wait_for(provider.health(), timeout=3):
                        raise ProviderError("provider_unhealthy", "nemotron_local health failed",
                                            "nemotron_local")
                    if self._director_queue >= settings.director_queue_max:
                        self._director_queue_rejected += 1
                        self._director_admission_until = time.monotonic() + 1.0
                        raise DirectorAdmissionRejected("director admission queue full")
                    self._director_queue += 1
                    try:
                        await asyncio.wait_for(
                            self._director_slots.acquire(),
                            timeout=settings.director_queue_timeout_seconds)
                        acquired_director = True
                    except asyncio.TimeoutError as exc:
                        self._director_queue_rejected += 1
                        self._director_admission_until = time.monotonic() + 1.0
                        raise DirectorAdmissionRejected(
                            "director admission queue timeout") from exc
                    finally:
                        self._director_queue -= 1
                resp = await asyncio.wait_for(
                    provider.generate(messages, output_contract, None, budget),
                    timeout=(settings.director_local_request_timeout_seconds
                             if role == "director" and rec.selected == "nemotron_local"
                             else settings.provider_timeout_seconds))
                rec.model = resp.model
                self._mark_success(rec.selected)
                return provider, rec, resp
            except Exception as exc:  # noqa: BLE001
                kind = "retryable_transient" if isinstance(exc, DirectorAdmissionRejected) \
                    else self._classify(exc)
                if not isinstance(exc, DirectorAdmissionRejected):
                    self._mark_failure(rec.selected, kind)
                    if role == "director" and rec.selected == "nemotron_local":
                        self._director_admission_until = time.monotonic() + 1.0
                last_exc = ProviderError(kind, str(exc), rec.selected)
                if kind in ("policy_rejection", "permanent_request_error", "schema_failure"):
                    break           # 永久错误不重试
                # 暂时错误：换 fallback 链上的下一个（由 route 重新计算）
            finally:
                if acquired_director:
                    self._director_slots.release()
        assert last_exc is not None
        raise last_exc

    async def call_decision(self, state: dict, questions: list[dict],
                            branch_id: str | None = None):
        provider, rec = self.route("decision", branch_id)
        try:
            resp = await asyncio.wait_for(
                provider.evaluate(state, questions), timeout=settings.provider_timeout_seconds)
            self._mark_success(rec.selected)
            return provider, rec, resp
        except Exception as exc:  # noqa: BLE001
            kind = self._classify(exc)
            self._mark_failure(rec.selected, kind)
            raise ProviderError(kind, str(exc), rec.selected)

    def video_provider(self, branch_id: str | None = None, local: bool = False):
        role = "local_video" if local else "cloud_video"
        provider, rec = self.route(role, branch_id)
        return provider, rec

    # ------------------------------------------------------------------
    def health_snapshot(self) -> dict[str, dict]:
        out = {k: h.to_dict() for k, h in self.health.items()}
        out["director_admission"] = {
            "max_concurrency": settings.director_local_max_concurrency,
            "queue": self._director_queue,
            "queue_max": settings.director_queue_max,
            "queue_rejected": self._director_queue_rejected,
            "queue_timeout_seconds": settings.director_queue_timeout_seconds,
        }
        return out

    def route_matrix(self) -> list[dict]:
        out = []
        for role, chain in self.routes.items():
            try:
                _, rec = self.route(role, record=False)
                out.append({"role": role, "primary": rec.primary,
                            "fallbacks": chain[1:], "selected": rec.selected,
                            "status": rec.status,
                            "skipped": rec.reason})
            except ProviderBlocked as e:
                out.append({"role": role, "primary": chain[0] if chain else "",
                            "fallbacks": chain[1:], "selected": None,
                            "status": "blocked", "skipped": e.reasons})
        return out

"""Provider 接口（PRD 08.3）：三类 Provider，不强行套一种接口。"""
from __future__ import annotations

from typing import Any, Optional, Protocol

from pydantic import BaseModel, Field


class TextResponse(BaseModel):
    content: str
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    usage: dict[str, Any] = {}


class TextModelProvider(Protocol):
    name: str

    async def generate(
        self,
        messages: list[dict[str, str]],
        output_contract: Optional[dict] = None,
        tools: Optional[list] = None,
        budget: Optional[dict] = None,
    ) -> TextResponse: ...

    async def health(self) -> bool: ...


class DecisionAnswer(BaseModel):
    choice: Optional[str] = None
    scores: dict[str, float] = {}
    confidence: float = 0.0
    calibrated: bool = False
    model: str = ""
    provider: str = ""
    latency_ms: int = 0
    details: dict[str, Any] = {}      # intent observation: action/desire/strategy/impact/...


class DecisionProvider(Protocol):
    name: str

    async def evaluate(
        self,
        state: dict[str, Any],
        questions: list[dict[str, Any]],
        model_version: Optional[str] = None,
    ) -> DecisionAnswer: ...

    async def health(self) -> bool: ...


class VideoJobHandle(BaseModel):
    provider_job_id: str
    provider: str
    submitted: bool = True
    # fal queue submit 返回的便利 URL（status_url/response_url/cancel_url），
    # 由 provider 自行选择使用；为空时 provider 自行按平台规则拼 URL。
    status_url: Optional[str] = None
    response_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoJobResult(BaseModel):
    status: str                     # QUEUED / GENERATING / READY / FAILED
    video_path: Optional[str] = None
    error: Optional[str] = None
    timings: dict[str, Any] = {}
    raw: dict[str, Any] = {}


class VideoProvider(Protocol):
    name: str

    def capabilities(self) -> dict[str, Any]: ...

    async def submit(self, request: dict[str, Any]) -> VideoJobHandle: ...

    async def status(self, handle: VideoJobHandle) -> VideoJobResult: ...

    async def cancel_if_supported(self, handle: VideoJobHandle) -> bool: ...

    async def health(self) -> bool: ...

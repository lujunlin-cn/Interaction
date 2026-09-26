"""全局配置：全部通过环境变量 / .env 注入，禁止在代码中写死密钥或端点。"""
from __future__ import annotations

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- 基础 ---
    app_name: str = "interactive-drama"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 9000
    public_base_url: str = "http://139.199.69.46:9000"   # 素材对外可访问基址（fal 拉取 references）

    # --- 数据库 ---
    database_url: str = "postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama"

    # --- 媒体与素材存储 ---
    data_dir: Path = Path("./data")            # 素材上传
    media_dir: Path = Path("./data/media")     # 生成的视频 / 装配产物

    # --- Provider 密钥（全部来自环境，禁止入库 / 入代码）---
    step_api_key: str = ""
    step_base_url: str = "https://api.stepfun.com/step_plan/v1"
    step37_model: str = "step-3.7-flash"       # 实际模型 ID 待账号确认（PIN_*）
    step5_model: str = "step-5-preview"        # 同上
    authoring_reasoning_effort: str = "high"
    authoring_max_tokens: int = 32768
    authoring_timeout_seconds: float = 300.0

    fal_key: str = ""
    # Optional second Fal account. Keys are only read from environment/.env
    # and are never exposed in traces or UI. The provider rotates on quota or
    # billing lock and keeps each key's circuit state independently.
    fal_key_secondary: str = ""
    # 付费媒体生成总开关。默认关闭，避免账单锁定时重复提交云任务。
    fal_paid_generation_enabled: bool = False
    # fal 官方 endpoint id 不带 fal-ai/ 前缀（fal-ai/ 命名空间会 404
    # "Path /h3-max/reference-to-video not found"）。
    fal_h3_model: str = "minimax/h3-max/reference-to-video"

    # OpenAI-compatible image relay (preferred when configured). Credentials
    # stay in .env and are never persisted in provenance/UI.
    image_provider_base_url: str = ""
    image_provider_api_key: str = ""
    image_provider_model: str = "gpt-image-2.5-sunburst"
    image_provider_fallback_model: str = "gpt-image-2.5-flare"
    image_provider_fallback_model_2: str = "gpt-image-2.5-sunburst"
    image_provider_fallback_model_3: str = "gpt-image-2"

    jev_api_key: str = ""
    jev_base_url: str = "https://api.typesafe.ai"   # Jev（TypeSafe SystemOne）API
    jev_model: str = "jev-latest"                   # 锁定版本时改为具体 ID（如 jev-1.13.0，PRD S06）

    local_llm_base_url: str = "http://127.0.0.1:8001/v1"   # DGX Spark 本地 OpenAI 兼容端点
    # 固定的 Director primary。Gemma/Ollama 只能作为显式外部 fallback，
    # 不允许再通过 nemotron_local 槽位冒充该模型。
    local_llm_model: str = "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4"

    sol_h3_base_url: str = ""               # 本地视频适配器（如 h3-adapter 8790）
    sol_h3_api_key: str = ""                # 适配器鉴权（若启用）

    # --- Provider 运行模式 ---
    # mock     : 全部角色使用 Mock Provider（离线开发，零费用）
    # live     : 按 PRD 冻结矩阵走真实 Provider（本地 Lightning / StepFun / fal）
    # hybrid   : 文本走真实 Provider，视频走 Mock（默认，安全起步）
    provider_mode: str = "hybrid"

    # --- Runtime Profile（Q53/Q68：单 Spark 显式切换）---
    runtime_profile: str = "AGENT_LOCAL_PROFILE"  # or VIDEO_LOCAL_PROFILE
    profile_lifecycle_enabled: bool = False       # docker stop/start evidence mode
    nemotron_container: str = "interaction-nemotron"
    video_local_container: str = "comfyui-nvidia"
    # Optional host-process lifecycle hooks for Sol-H3 adapters that are not
    # managed by Docker. Empty values keep the Docker lifecycle above.
    video_local_stop_command: str = ""
    video_local_start_command: str = ""
    video_local_process_pattern: str = ""

    # --- 调度默认值（PRD 12.2，部署配置，非业务常数）---
    budget_total: int = 500
    budget_per_turn: int = 60
    budget_speculation_cap: int = 160
    video_concurrency: int = 3
    target_k: int = 3
    shots_per_branch: int = 2
    branch_ttl_seconds: int = 180
    shot_unit_cost: int = 5  # 每 Shot 预留额度（内部记账单位）

    # --- Provider 容错 ---
    provider_timeout_seconds: float = 30.0
    provider_circuit_threshold: int = 3
    director_local_max_concurrency: int = 2
    director_queue_timeout_seconds: float = 10.0
    director_queue_max: int = 16
    director_local_request_timeout_seconds: float = 90.0

    # --- CORS（G28：收敛，不再 "*"）---
    # 逗号分隔；默认同源 + 常见本地 dev（vite 5173/4173、preview）。
    # 生产同源部署下 CORS 头实际上用不到，但仍收敛避免被任意站点跨域调用 API。
    cors_origins: str = ("http://127.0.0.1:5173,http://localhost:5173,"
                        "http://127.0.0.1:4173,http://localhost:4173,"
                        "http://139.199.69.46:9000,http://127.0.0.1:9000")

    # --- 运行时节奏 ---
    branch_phase_delay_ms: int = 350      # 各管线阶段之间的最小间隔（让状态转换可观察）
    decision_lead_seconds: float = 2.0    # Decision Lead：距场景结束多少秒即可发布下一批推荐
    mock_shot_duration: float = 5.0       # Mock 视频单镜头时长
    opening_shot_duration: float = 8.0   # Opening/ending use deliberate establishment/resolution beats
    ending_shot_duration: float = 8.0
    max_video_shot_duration: float = 10.0
    timed_timeout_override: float = 0.0   # >0 时覆盖 Scenario 声明的限时秒数（测试用）

    # 新生成任务的媒体参数（旧 Artifact 不受影响）
    image_generation_resolution: str = "0.5K"
    video_generation_resolution: str = "480P"
    generation_aspect_ratio: str = "16:9"
    video_language: Literal["zh-CN", "en"] = "zh-CN"
    subtitle_language: Literal["zh-CN", "en"] = "zh-CN"
    developer_test_top_k: int = 1
    developer_test_max_shots: int = 1
    developer_test_shot_duration: float = 5.0
    max_test_reference_images: int = 2
    max_test_reference_videos: int = 0
    developer_test_override_enabled: bool = False
    # Jev recommendations can be planned without purchasing speculative H3
    # media. The selected recommendation is generated on demand.
    pre_generate_recommendation_media: bool = True

    @property
    def effective_target_k(self) -> int:
        return self.developer_test_top_k if self.developer_test_override_enabled else self.target_k

    @property
    def effective_shots_per_branch(self) -> int:
        return self.developer_test_max_shots if self.developer_test_override_enabled else self.shots_per_branch

    @property
    def effective_shot_duration(self) -> float:
        return self.developer_test_shot_duration if self.developer_test_override_enabled else self.mock_shot_duration

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def media_path(self) -> Path:
        p = Path(self.media_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

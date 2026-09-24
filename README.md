# Interactive Drama · 互动短剧平台

基于 PRD v0.6 Final Closure 的可运行实现：React+TypeScript 前端 + FastAPI + PostgreSQL 后端，
部署目标为 DGX Spark（`/home/hajimi2025/interaction`）。

## 架构

```
frontend/   React + TS + Vite（左侧 Sidebar IA：故事库/创作/角色库/素材/游玩/开发者 Inspector）
backend/    FastAPI + SQLAlchemy 2 async + Pydantic v2
  app/domain/       确定性状态核心（StateManager / DramaStateManager / Fingerprint）
  app/providers/    Provider Router + Mock/真实 Provider（Nemotron 本地 / StepFun / fal H3 / Jev）
  app/runtime/      RuntimeEngine（Branch 生命周期、Top-K 调度、两阶段提交、原子发布）
  app/skills/       平台 Skills 与玩法机制注册表（只产 Proposal）
  app/api/          REST + WebSocket
deploy/     Docker Compose（PostgreSQL 5433）+ 一键启动脚本
```

## 快速开始（DGX Spark）

```bash
cd /home/hajimi2025/interaction
cp backend/.env.example backend/.env   # 填入 STEP_API_KEY / FAL_KEY
bash deploy/start.sh                    # 起库 + 依赖 + 构建 + 服务于 :9000
```

打开 `http://<spark-ip>:9000`。默认 `PROVIDER_MODE=mock`：全部 Provider 为正式 Mock
（确定性规则 + FFmpeg 真实生成占位视频），业务 Runtime 完全真实。

## Provider 模式

| 模式 | 文本（Director/Narrative/Authoring） | 视频 | 决策 |
| --- | --- | --- | --- |
| mock | MockTextProvider（确定性规则） | MockVideoProvider（FFmpeg 字幕卡） | MockDecisionProvider |
| live | PRD 冻结矩阵（Lightning 本地 → Step5 / Step3.7 → Lightning / Step5） | fal H3 Max / Sol-H3 本地 | Jev API |
| hybrid | 同 live 矩阵，失败显式降级并记录路由事件 | H3 Max → Mock | 同 live |

冻结矩阵（live）：director→[nemotron_local, step_5]，narrative→[step_37, nemotron_local]，
production→[nemotron_local, step_37]，authoring→[step_5]，decision→[jev]，
cloud_video→[h3_max]，local_video→[sol_h3_local]。

## 测试

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db PROVIDER_MODE=mock \
  .venv/bin/python -m pytest tests/ -q
```

2026-09-24 DGX Spark 实测：Nemotron Lightning NVFP4 通过 vLLM 0.27.1-aarch64
运行于 `127.0.0.1:8001`，`/v1/models` 返回固定模型 ID，中文 Director JSON 冒烟成功。
真实直连并发 1/2/4 路三轮成功率为 3/3、6/6、12/12，8 路单轮为 8/8；业务
`DIRECTOR_LOCAL_MAX_CONCURRENCY` 默认仍为 2，超时回退 Step 5。详见
`DIRECTOR_CONCURRENCY_REPORT.md` 与 `G29_MODEL_DEPLOY_AUDIT.md`。

正式 Character Studio 接入 AI 双 Candidate、Canonical、多视图二次确认、非破坏编辑、Outfit、版本 Diff、Scenario Snapshot、Local Override/Promote 与 Reference Resolver。视频 Runtime 按每个 Shot 独立提交 Provider Job，再由 FFmpeg concat 生成 SceneArtifact；Mock 结果不作为 Real Multi-Shot 证据。

## 关键契约

- **Ready Gate**：只有媒体 READY 的分支显示给玩家（I05）；Top-K 锁定后并行生成；
  单分支失败快速重试 1 次后 K-1 原子发布（记录 effective_k）。
- **Two-Phase Canonicalization**：SELECTED → PROVISIONAL（媒体确认）→ CANONICAL；
  失败回滚不污染正式状态。
- **Dependency Fingerprint**：分支声明 read set 的 SHA-256；未声明依赖保守 miss；
  愿望/素材变更使未就绪分支 INVALIDATED。
- **呈现回执**：玩家实际看完（PresentationReceipt）后，内容才进入 knowledge。
- **术语隔离**：玩家界面只有自然中文；技术状态仅出现在开发者模式。

## 安全与已知限制（G28）

- **密钥**：所有外部凭据（StepFun / fal / Jev / Sol-H3 adapter token）只走
  `backend/.env`（已 gitignore）或环境变量注入，**禁止**写进代码、Git、Trace span、
  日志或界面。Provider 内部构造 `Authorization` 头，不落库不回显。
- **CORS**：`CORSMiddleware` 收敛为 `settings.cors_origins`（默认同源 +
  本地 dev 端口），不再 `*`。生产同源部署下跨域头实际不触发。
- **媒体/素材目录无鉴权**：`/media`（生成产物）与 `/files`（上传素材）以
  `StaticFiles` 直接挂载，任何人拿到 URL 即可访问。Sol-H3 adapter 拉取
  `reference_*` 依赖该公开路径。**仅适合内网/演示部署**；公网开放需在前置
  反代加鉴权或签名 URL（当前部署在 FRP 中转后暴露公网，属已知接受风险）。
- **管理接口**：`/dev/*`（providers/inject、profile/switch、fixtures、jobs）
  无鉴权，供开发者模式与验收脚本使用；公网部署应限制来源。
- **会话**：无账号体系，`session_id` 即访问令牌——知道 sid 即可读状态/发 action。
  单租户演示可接受，多用户需补鉴权层。

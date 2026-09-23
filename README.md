# Interactive Drama · 互动短剧平台

基于 PRD v0.5 的可运行实现：React+TypeScript 前端 + FastAPI + PostgreSQL 后端，
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
| hybrid | 同 live 矩阵，失败显式降级并记录路由事件 | 同 live | 同 live |

冻结矩阵（live）：director→[nemotron_local, step_5]，narrative→[step_37, nemotron_local]，
production→[nemotron_local, step_37]，authoring→[step_5]，decision→[jev]，
cloud_video→[h3_max]，local_video→[sol_h3_local]。

## 测试

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db PROVIDER_MODE=mock \
  .venv/bin/python -m pytest tests/ -q
```

## 关键契约

- **Ready Gate**：只有媒体 READY 的分支显示给玩家（I05）；Top-K 锁定后并行生成；
  单分支失败快速重试 1 次后 K-1 原子发布（记录 effective_k）。
- **Two-Phase Canonicalization**：SELECTED → PROVISIONAL（媒体确认）→ CANONICAL；
  失败回滚不污染正式状态。
- **Dependency Fingerprint**：分支声明 read set 的 SHA-256；未声明依赖保守 miss；
  愿望/素材变更使未就绪分支 INVALIDATED。
- **呈现回执**：玩家实际看完（PresentationReceipt）后，内容才进入 knowledge。
- **术语隔离**：玩家界面只有自然中文；技术状态仅出现在开发者模式。

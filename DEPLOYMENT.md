# 部署与运维手册 · 互动短剧

部署目标：DGX Spark `/home/hajimi2025/interaction`，公网经 FRP 中转暴露
`http://139.199.69.46:9000`（前端 + API 同端口，API 前缀 `/api`）。

## 拓扑

```
浏览器 ──► FRP(139.199.69.46:9000) ──► DGX uvicorn :9000 ──► PG :5433 (docker)
                                            │
                                            ├─► StepFun api.stepfun.com   (step_37/step_5)
                                            ├─► Jev api.typesafe.ai        (decision)
                                            ├─► fal.ai                     (h3_max cloud video)
                                            ├─► Sol-H3 local adapter       (local_video, VIDEO_LOCAL)
                                            └─► vLLM 127.0.0.1:8001       (Nemotron Lightning director/production)
```

## 启动 / 重启

后端由 `/tmp/start_backend.sh` 拉起（DGX 本地）：

```bash
#!/bin/bash
cd ~/interaction/backend
set -a; . ./.env; set +a
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > ~/interaction/backend.log 2>&1
```

远程重启（SSH 后台化的唯一可靠姿势——远程 `&` 会被 SSH 会话回收）：

```bash
ssh -f -p 22222 hajimi2025@139.199.69.46 \
  'setsid /tmp/start_backend.sh < /dev/null > /dev/null 2>&1'
```

验证：

```bash
curl -s http://139.199.69.46:9000/api/health
# {"ok":true,"provider_mode":"hybrid","profile":"AGENT_LOCAL_PROFILE"}
```

## 在DGX上同步与构建

2026-09-25已在本机验证 `npm ci && npm run build` 成功；旧文档“DGX npm必然OOM、只能传dist”的结论已失效。

```bash
cd /home/hajimi2025/interaction
git pull --ff-only
git rev-parse HEAD
cd frontend
npm ci
npm run build
```

后端与前端必须来自同一应用代码候选。重启前检查 `/api/dev/jobs`，区分实际活动任务与历史残留记录；等待活动流水线完成后向旧uvicorn发送SIGTERM，再从backend目录用现有.env启动。仅更新应用时不停止Nemotron/Sol-H3容器。重启后核验本地与公网 `/api/health`、新增API的OpenAPI路径和HTML引用的bundle hash。

本轮最新应用代码候选、源码树指纹与构建hash见 `docs/acceptance/prd_v06_latest/verification_summary.json`，实际重启证据见同目录 `deployment_validation.json`。

## 关键配置（backend/.env，gitignore，不入库不入 Git）

| 变量 | 用途 |
| --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://…@127.0.0.1:5433/…` |
| `PROVIDER_TIMEOUT_SECONDS` | 实际部署为120秒；真实Step作者请求可能超过旧30秒默认，仍保留有界超时/重试 |
| `PROVIDER_MODE` | `mock` / `live` / `hybrid`（hybrid：真实 H3 Max，失败显式降级 Mock） |
| `PROFILE_LIFECYCLE_ENABLED` | 真实 Profile 切换时执行 stop/release/start/health；单 GPU 生产环境开启 |
| `NEMOTRON_CONTAINER` / `VIDEO_LOCAL_CONTAINER` | `interaction-nemotron` / `comfyui-nvidia` |
| `VIDEO_LOCAL_STOP_COMMAND` / `VIDEO_LOCAL_START_COMMAND` | Sol-H3 adapter 为宿主机进程时的 stop/start hook |
| `VIDEO_LOCAL_PROCESS_PATTERN` | Profile health 时确认 Sol-H3 进程实际存在 |
| `RUNTIME_PROFILE` | `AGENT_LOCAL_PROFILE` / `VIDEO_LOCAL_PROFILE` |
| `STEP_API_KEY` | StepFun step_37 / step_5 |
| `STEP_BASE_URL` | OpenAI-compatible endpoint: `https://api.stepfun.com/step_plan/v1` |
| `JEV_API_KEY` | Jev 决策 |
| `FAL_KEY` | fal h3_max 云视频 |
| `FAL_PAID_GENERATION_ENABLED` | 付费 H3/Nano Banana 总开关；默认 `false`，充值并完成付费验收前保持关闭 |
| `IMAGE_PROVIDER_BASE_URL` / `IMAGE_PROVIDER_API_KEY` | OpenAI-compatible 生图中转站；配置后 Character Studio 优先使用中转站 |
| `IMAGE_PROVIDER_MODEL` / `IMAGE_PROVIDER_FALLBACK_MODEL` | 默认 `gpt-image-2.5-sunburst` / `gpt-image-2` |
| `IMAGE_GENERATION_RESOLUTION` / `VIDEO_GENERATION_RESOLUTION` | 新任务默认图片/视频分辨率（0.5K / 480P） |
| `GENERATION_ASPECT_RATIO` | 新任务比例（默认 16:9） |
| `SOL_H3_*` | Sol-H3 本地 adapter 端点/token |
| `LOCAL_LLM_*` | 固定 Nemotron Lightning vLLM OpenAI 兼容端点；Gemma 不能占用 nemotron_local 槽位 |
| `DIRECTOR_LOCAL_MAX_CONCURRENCY` | 本地 Director 同时推理上限（默认 2） |
| `DIRECTOR_QUEUE_TIMEOUT_SECONDS` | 等待本地 Director slot 的超时（默认 10 秒，随后路由 Step 5） |
| `DIRECTOR_QUEUE_MAX` | 本地 Director 等待队列上限（默认 16） |
| `CORS_ORIGINS` | 逗号分隔白名单（默认同源 + 本地 dev 端口） |

## Provider 运行模式

| 模式 | 文本 | 视频 | 决策 |
| --- | --- | --- | --- |
| `mock` | MockText 确定性规则 | MockVideo FFmpeg 占位 | MockDecision |
| `hybrid` | 真实（本地/StepFun），失败显式降级 | H3 Max → Mock | Jev |
| `live` | 完整冻结矩阵 | 真实 h3_max / sol_h3_local | Jev |

hybrid矩阵（live移除每条链末尾Mock，不允许Mock冒充成功）：

- director → `nemotron_local → step_5 → mock_text`
- narrative → `step_37 → nemotron_local → mock_text`
- production → `nemotron_local → step_37 → mock_text`
- authoring → `step_5 → mock_text`
- decision → `jev → mock_decision`
- cloud_video → `h3_max → mock_video`；local_video → `sol_h3_local → mock_video`

降级由 Router 按 circuit breaker 驱动，`GET /api/dev/providers` 可见
`skipped[]`（`circuit_open`/`profile_unavailable`）与 `selected`。

## 故障排查

| 现象 | 排查 |
| --- | --- |
| 分支卡 PLANNING | `tail -f backend.log` 看 provider HTTP 调用；circuit_open 会在 `/dev/providers` 标出；`POST /api/dev/providers/recover` 复位熔断 |
| `location`/角色 op 不生效 | mock `_director_plan` 的 `scenario_context` 提取——已修 `raw_decode`（2026-09-23），确认 DGX 同步 |
| 公网 curl POST 返回空 | FRP 间歇丢包：服务端可能已执行。**不要盲重试**，先 `GET /sessions/{sid}/view` 查状态，或走 `ssh … curl 127.0.0.1:9000` 本地回环 |
| `last_failed_action` 有值 | 正式Player显示重新生成/修改行动/文字模式继续；`POST /sessions/{sid}/player` 的retry/text_continue走原有校验，失败不重复提交 |
| Nemotron 未部署或满载 | 检查 `:8001/v1/models`、`/api/dev/providers` 的 `director_admission`；Director 回退 Step 5，Gemma 不计为 Nemotron 成功 |

Nemotron 启动入口为 `deploy/start_nemotron_lightning.sh`，使用本机已安装的
`vllm/vllm-openai:v0.27.1-aarch64` 容器。模型目录默认为
`/home/hajimi2025/.cache/interaction-nemotron`；脚本会先检查 52 个权重分片。
FlashInfer/vLLM 编译缓存持久化到 `/home/hajimi2025/.cache/interaction-vllm`，
容器使用 `restart=unless-stopped`；重启时日志应出现 `Loaded 32 configs`，而不是
重新执行完整自动调优。这样可以避免首次重启阶段因临时 autotune cache 或容器被
删除导致的启动崩溃。
本机与其他 GPU 进程共用内存，旧值 `LOCAL_LLM_GPU_MEMORY_UTILIZATION=0.75`
启动失败，实测可用值 `0.65` 已成为脚本默认值。启动后以
`curl http://127.0.0.1:8001/v1/models` 核对模型 ID，再用
`tools/director_concurrency_probe.py` 测并发。2026-09-24 的 1/2/4 路实测见
`DIRECTOR_CONCURRENCY_REPORT.md`；该探针直连 vLLM，不经过业务后端限流。

## 测试

```bash
cd backend
DATABASE_URL="sqlite+aiosqlite:///./itest.db" PROVIDER_MODE=mock \
  PROFILE_LIFECYCLE_ENABLED=false .venv/bin/python -m pytest tests/ -q     # 63 passed, 6 warnings（2026-09-25最新候选）
```

真实双向 Profile 证据见 `PROFILE_SWITCH_ACCEPTANCE.md`；真实 H3 Max 双 Shot 证据见
`REAL_MULTISHOT_ACCEPTANCE.md`。线上当前服务：`http://139.199.69.46:9000`，不再作为
本轮 Gap。

## 已知限制（详见 `SECURITY_KNOWN_LIMITATIONS.md`）

`/media`、`/files`、`/dev/*` 无鉴权；session_id 即访问令牌。内网/演示适用，
公网需反代签名 URL。FRP 暴露属已知接受风险。

## 本轮真实Provider限制与测试配置

- 真实验收API为本地9002，独立SQLite验收库，PROVIDER_MODE=live；生产9000仍为hybrid、AGENT_LOCAL_PROFILE、PROFILE_LIFECYCLE_ENABLED=true。
- 为停顿检查，验收BRANCH_TTL_SECONDS=900；生产保持180。媒体回放夹具仅写隔离验收库，不导入生产。
- Step Plan的step_5采用提示约束JSON并在服务端验证/最多一次格式修复；本机对照显示强制response_format=json_object会破坏输出。key与endpoint未更换。
- fal返回403 `User is locked. Reason: TOP_UP.` 时保留错误和job信息，使用显式文字恢复。hybrid可能显式降级Mock，不能把该视频视为真实Provider验收PASS。
- 本轮没有重启/重新部署已验证的Nemotron或重复Profile往返；仅更新应用与前端。

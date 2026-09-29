# PlotShift 部署说明

本文说明如何在一台 Linux 主机上部署 PlotShift，如何使用本地 NVIDIA 算力运行智能体，如何接入外部 API，以及如何用较低成本验证系统。应用和 API 通过 9000 端口提供；PostgreSQL 只绑定本机 5433；本地 Nemotron 以 OpenAI-compatible API 监听 8001。所有密钥只保存在服务器的 `backend/.env` 或 Secret Manager 中，不能写进前端、截图、日志或 Git。

## 1. 环境准备

基础环境：Linux、Python 3.11+、Node.js 20+、npm、Docker Compose Plugin。使用本地模型时还需要 NVIDIA GPU、匹配的 NVIDIA Driver、CUDA 运行时、NVIDIA Container Toolkit 和足够的显存/统一内存。项目已按 DGX Spark + ARM64 vLLM 路径提供脚本；没有本地 GPU 时可用 `mock`、`hybrid` 或只接入云端文本服务。

```bash
git clone https://github.com/lujunlin-cn/PlotShift.git
cd PlotShift
docker compose -f deploy/docker-compose.yml up -d
cp backend/.env.example backend/.env
```

数据库默认连接：

```text
postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama
```

## 2. 先启动零费用离线模式

先把 `backend/.env` 设置为：

```dotenv
DATABASE_URL=postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama
PROVIDER_MODE=mock
RUNTIME_PROFILE=AGENT_LOCAL_PROFILE
PROFILE_LIFECYCLE_ENABLED=false
FAL_PAID_GENERATION_ENABLED=false
```

一键脚本会创建虚拟环境、安装后端依赖、安装前端依赖、构建前端并启动 9000：

```bash
bash deploy/start.sh
curl -fsS http://127.0.0.1:9000/api/health
```

## 3. 使用本地 NVIDIA 算力部署智能体

Director 使用 `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`。该模型通过 vLLM OpenAI-compatible 服务运行，业务层不依赖模型私有 SDK。启动脚本会在容器启动前检查 `config.json`、索引文件和 52 个 safetensors 分片，避免只下载部分权重却误报服务成功。

```bash
export LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
bash deploy/start_nemotron_lightning.sh
curl -fsS http://127.0.0.1:8001/v1/models
```

后端配置：

```dotenv
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
DIRECTOR_LOCAL_MAX_CONCURRENCY=2
DIRECTOR_QUEUE_TIMEOUT_SECONDS=10
DIRECTOR_QUEUE_MAX=16
DIRECTOR_LOCAL_REQUEST_TIMEOUT_SECONDS=90
```

脚本使用 NVIDIA Container Toolkit 的 GPU 直通、Marlin MoE 后端、FlashInfer Mamba 后端、FP8 KV cache、prefix caching 和受控的 GPU memory utilization。这样可以在有限显存下保留较长上下文，同时用并发上限和队列保护避免多个回合争抢显存。`--max-model-len`、GPU 利用率和并发数应根据实际机器压测调整；不能只看单请求成功就把并发上限调大。

## 4. 接入外部 API（只填自己的值）

下面的示例只使用占位符。部署者应在服务器上替换 `<...>`，不要把真实 Key 复制到 README、Issue、前端变量或提交记录。

### StepFun 阶跃星辰

StepFun 提供文本生成：Step 3.7 Flash 用于 Narrative，Step 5 Preview 用于 Authoring、审查和必要的 Director 回退。

```dotenv
STEP_API_KEY=<your-stepfun-key>
STEP_BASE_URL=https://api.stepfun.com/step_plan/v1
STEP37_MODEL=step-3.7-flash
STEP5_MODEL=step-5-preview
```

### Jev 决策服务

```dotenv
JEV_API_KEY=<your-jev-key>
JEV_BASE_URL=https://api.typesafe.ai
JEV_MODEL=jev-latest
```

Jev 负责快速分类、路由、评分和 Top-K 排序，不直接决定世界真相或结局。

### fal.ai 视频

PlotShift 的视频 Provider 固定为：

```dotenv
FAL_KEY=<your-fal-key>
FAL_KEY_SECONDARY=<optional-second-key>
FAL_H3_MODEL=minimax/h3-max/reference-to-video
FAL_PAID_GENERATION_ENABLED=false
```

确认文本、图片和参考素材链路正确后，才把付费开关改为 `true`。Jev 预测预生成视频默认关闭，只有玩家实际选择或明确测试时才提交 H3 任务。`PUBLIC_BASE_URL` 必须是 fal.ai 能访问的公网地址，不能填 localhost：

```dotenv
PUBLIC_BASE_URL=https://<your-public-host>:9000
```

### OpenAI-compatible Image Relay

角色图、标准视图和编辑图走 OpenAI-compatible Image Relay，不走 fal.ai 生图：

```dotenv
IMAGE_PROVIDER_BASE_URL=https://<your-image-relay>
IMAGE_PROVIDER_API_KEY=<your-relay-key>
IMAGE_PROVIDER_MODEL=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL=gpt-image-2.5-flare
IMAGE_PROVIDER_FALLBACK_MODEL_2=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL_3=gpt-image-2
IMAGE_GENERATION_RESOLUTION=4K
```

中转站需要兼容 `/v1/images/generations` 和 `/v1/images/edits`。后端会把结果归档到自己的媒体目录，浏览器只拿应用地址。

## 5. 如何设计和部署 Agent Skills

Skill 应代表一个可复用的判断能力，而不是把普通函数改名。每个 Skill 至少定义：Purpose、Trigger、Input Schema、Output Schema、允许的状态读取范围、Proposal 权限、失败语义、Fallback、版本和 Metrics。Runtime 先建立分层 Working Context，再按需触发 Skill：

1. **Understand Free Action**：把玩家原文整理为 action、target、goal、strategy、constraints 和 risk。
2. **Evaluate Choices**：生成策略、风险和信息价值有差异的候选，并让 Jev 排序。
3. **Reconcile Mechanics**：协调 Inventory、Clue、Relationship、Wish、Timed/QTE 的提案，去重并处理冲突。
4. **Character Reference Resolver**：从已发布 Snapshot 绑定角色身份和参考素材。
5. **Narrative**：只接收 Scene Packet，生成可见叙事和字幕，不修改 Canonical State。
6. **Production / Visual QA**：规划镜头、绑定素材、检查角色连续性，返回可审计的媒体计划。

Skill 可以并行准备，但只能由 StateManager 提交正式状态。每次调用记录输入摘要、版本、耗时、输出、接受/拒绝结果和失败原因。开发者可通过 trace 和 Replay 比较 Skill 触发精度、Proposal 接受率、上下文 Token、Ready 延迟和媒体浪费。

## 6. 生产优化和运行模式

| 目的 | `PROVIDER_MODE` | 付费视频 | 说明 |
| --- | --- | --- | --- |
| 页面和状态机开发 | `mock` | `false` | 零外部请求 |
| 文本链路验收 | `hybrid` | `false` | 真实文本，媒体可回退 |
| 人工视频测试 | `live`/`hybrid` | 按需 `true` | 只生成玩家实际选择的分支 |
| 本地视频实验 | `live` | `false` | 使用 `VIDEO_LOCAL_PROFILE` 的 Sol-H3 适配器 |

推荐的优化顺序是：先用 Jev 和规则判断是否需要完整 Beat，再让 Director 规划；锁定 K 后并行 Narrative 和素材准备；只给当前 Skill 投影所需的 Context；对本地模型启用 prefix caching、有限并发和队列；对外部 Provider 使用连接复用、有限重试、熔断和回退。所有优化都必须通过历史 Replay 验证，不能用增加无用媒体请求换取表面上的速度。

## 7. 长期运行、更新和验证

生产环境使用 systemd 或容器 `restart: unless-stopped`。临时部署可使用：

```bash
setsid bash deploy/start.sh </dev/null >/tmp/plotshift.log 2>&1 &
```

更新后重新构建前端并检查：

```bash
git pull --ff-only
(cd frontend && npm ci && npm run build)
curl -fsS http://127.0.0.1:9000/api/health
curl -fsS http://127.0.0.1:8001/v1/models
ss -ltnp | grep -E ':9000|:8001'
```

离线回归：

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db PROVIDER_MODE=mock \
PROFILE_LIFECYCLE_ENABLED=false .venv/bin/python -m pytest tests/ -q
```

# 部署说明

本文从一台干净的 Linux 主机开始，部署一个可访问的 Interaction 实例。应用、API 和生成媒体使用同一个 9000 端口；PostgreSQL 只绑定本机 5433。

## 1. 运行环境

离线模式需要：

- Linux
- Python 3.11+
- Node.js 20+ 和 npm
- Docker 与 Docker Compose Plugin

真实本地模型还需要 NVIDIA 驱动、CUDA 和足够的 GPU/统一内存。没有 GPU 也可以用 `mock` 或仅使用云端 Provider。

## 2. 安装代码和数据库

```bash
git clone https://github.com/lujunlin-cn/Interaction.git
cd Interaction
docker compose -f deploy/docker-compose.yml up -d
```

数据库连接默认是：

```text
postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama
```

## 3. 创建服务端配置

```bash
cp backend/.env.example backend/.env
```

先用这组配置启动离线模式：

```dotenv
DATABASE_URL=postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama
PROVIDER_MODE=mock
RUNTIME_PROFILE=AGENT_LOCAL_PROFILE
FAL_PAID_GENERATION_ENABLED=false
```

配置文件只在服务器上保存。外部服务的 Key 通过环境变量或 Secret Manager 注入，浏览器不需要、也不应该持有这些 Key。

## 4. 接入外部服务

所有 Provider 都由后端调用。把下面的占位值替换成你自己的服务地址和 Key。

### StepFun：文本生成

```dotenv
STEP_API_KEY=<stepfun-key>
STEP_BASE_URL=https://api.stepfun.com/step_plan/v1
STEP37_MODEL=step-3.7-flash
STEP5_MODEL=step-5-preview
```

### Jev：推荐决策

```dotenv
JEV_API_KEY=<jev-key>
JEV_BASE_URL=https://api.typesafe.ai
JEV_MODEL=jev-latest
```

### fal.ai：视频

视频接口固定使用 `minimax/h3-max/reference-to-video`：

```dotenv
FAL_KEY=<fal-key>
FAL_KEY_SECONDARY=<optional-second-key>
FAL_H3_MODEL=minimax/h3-max/reference-to-video
FAL_PAID_GENERATION_ENABLED=false
```

确认文本、图片和素材地址都能正常工作后，再把 `FAL_PAID_GENERATION_ENABLED` 改成 `true`。Jev 预测预生成默认关闭，只有玩家实际选择或明确测试时才提交视频任务。

### OpenAI-compatible Image Relay：图片

角色图、标准视图和编辑使用兼容 OpenAI Images API 的中转服务，不使用 fal.ai 图片接口：

```dotenv
IMAGE_PROVIDER_BASE_URL=https://<relay-host>
IMAGE_PROVIDER_API_KEY=<relay-key>
IMAGE_PROVIDER_MODEL=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL=gpt-image-2.5-flare
IMAGE_PROVIDER_FALLBACK_MODEL_2=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL_3=gpt-image-2
```

中转服务需要提供 `/v1/images/generations` 和 `/v1/images/edits`。服务端会把生成结果归档到媒体目录，前端只接收应用自己的文件地址。

### Nemotron：本地文本模型（可选）

```bash
export LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
bash deploy/start_nemotron_lightning.sh
```

后端配置：

```dotenv
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
```

启动后确认：

```bash
curl -fsS http://127.0.0.1:8001/v1/models
```

## 5. 构建并启动应用

一键启动会创建 Python 虚拟环境、安装后端依赖、安装前端依赖、构建前端并监听 9000：

```bash
bash deploy/start.sh
```

手动启动：

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ../frontend && npm ci && npm run build
cd ../backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

部署完成后打开 `http://<server-ip>:9000`，检查：

```bash
curl -fsS http://127.0.0.1:9000/api/health
ss -ltnp | grep ':9000'
```

健康接口返回 `ok: true`，端口处于 LISTEN 状态，即可访问应用。

## 6. 模式选择

| 场景 | PROVIDER_MODE | 付费视频 | 说明 |
| --- | --- | --- | --- |
| 页面开发 | `mock` | `false` | 零外部请求 |
| 文本演示 | `hybrid` | `false` | 真实文本，媒体可回退 |
| 人工视频测试 | `live` 或 `hybrid` | 按需 `true` | 只在实际选择时生成 |
| 本地视频实验 | `live` | `false` | 使用 `VIDEO_LOCAL_PROFILE` |

## 7. 更新和后台运行

更新应用：

```bash
git pull --ff-only
cd frontend && npm ci && npm run build
cd ..
```

重启时保留数据库和本地模型服务。生产环境用 systemd 或容器的 `restart: unless-stopped` 运行应用；临时启动可用：

```bash
setsid bash deploy/start.sh </dev/null >interaction.log 2>&1 &
```

这样 SSH 断开后进程仍会继续运行。更新后再次检查 `/api/health`、9000 端口和本地模型 `/v1/models`。

## 8. 离线回归

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db \
PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false \
.venv/bin/python -m pytest tests/ -q
cd ../frontend
npm ci
npm run build
```

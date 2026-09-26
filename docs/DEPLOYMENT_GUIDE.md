# Interaction 部署说明

本文面向第一次部署项目的开发者。示例不会包含任何真实 API Key；请在自己的密钥管理系统、CI Secret 或服务器上的 `backend/.env` 注入凭据。

## 部署模式选择

| 模式 | 适合场景 | 外部请求 | 需要 GPU |
| --- | --- | --- | --- |
| `mock` | 本地开发、评审 UI、自动化回归 | 无 | 否 |
| `hybrid` | 文本真实、媒体失败可回退的演示 | 按已配置 Provider | 推荐 |
| `live` | 完整真实模型和媒体验收 | 会产生真实费用 | 运行 Nemotron 时需要 |

第一次部署建议从 `mock` 开始，确认页面、数据库和状态机工作后，再单独打开文本、图片、决策和视频。不要为了验证页面而直接打开所有付费 Provider。

## 1. 环境要求

- Linux（推荐 NVIDIA DGX Spark 或带 NVIDIA GPU 的主机）
- Docker 与 Docker Compose Plugin
- Python 3.11+
- Node.js 20+、npm
- 运行真实本地模型时，需要可用的 NVIDIA 驱动、CUDA 运行时和足够的统一内存；只做离线演示可以使用 `PROVIDER_MODE=mock`，不需要 GPU 或外部 API。

## 2. 获取代码并启动数据库

```bash
git clone https://github.com/lujunlin-cn/Interaction.git
cd Interaction
docker compose -f deploy/docker-compose.yml up -d
```

Compose 只启动 PostgreSQL，绑定到本机 `127.0.0.1:5433`，不会把数据库端口直接暴露到公网。

## 3. 配置服务端环境

```bash
cp backend/.env.example backend/.env
${EDITOR:-vi} backend/.env
```

最小离线配置如下：

```dotenv
DATABASE_URL=postgresql+asyncpg://drama:drama@127.0.0.1:5433/interaction_drama
PROVIDER_MODE=mock
RUNTIME_PROFILE=AGENT_LOCAL_PROFILE
FAL_PAID_GENERATION_ENABLED=false
```

需要真实模型时，将 `PROVIDER_MODE` 改为 `live` 或 `hybrid`，并按下面的 Provider 教程填入自己的凭据。`.env` 已被 Git 忽略，禁止把它复制进提交、截图、日志或 Issue。

## 4. 外部 API 接入教程

所有外部 API 都由后端调用，浏览器只访问 Interaction 的 `/api`。部署者可以使用环境变量、Docker Secret、Kubernetes Secret 或云平台 Secret Manager；不要把 Key 写进 React、Vite 的 `VITE_*` 变量，也不要把 Key 放在 URL 查询参数中。

### StepFun（文本模型）

在 StepFun 控制台创建服务端 Key，把值注入：

```dotenv
STEP_API_KEY=<your-stepfun-key>
STEP_BASE_URL=https://api.stepfun.com/step_plan/v1
STEP37_MODEL=step-3.7-flash
STEP5_MODEL=step-5-preview
```

### Jev（决策评估）

在 Jev/TypeSafe 服务创建 Key：

```dotenv
JEV_API_KEY=<your-jev-key>
JEV_BASE_URL=https://api.typesafe.ai
JEV_MODEL=jev-latest
```

### fal.ai（视频）

在 fal.ai 创建服务端 Key。Interaction 使用的模型固定为 `minimax/h3-max/reference-to-video`：

```dotenv
FAL_KEY=<your-fal-key>
FAL_KEY_SECONDARY=<optional-second-key>
FAL_H3_MODEL=minimax/h3-max/reference-to-video
FAL_PAID_GENERATION_ENABLED=false
```

确认余额、参考图可被服务端访问并完成小额验证后，才把付费开关改为 `true`。Jev 推荐预生成视频默认关闭；只有用户真正选择或明确发起测试时才提交视频任务。

### OpenAI-compatible 图片中转

图片生成与编辑使用兼容 OpenAI Images API 的中转服务，不走 fal.ai 图片模型。向中转服务申请一个服务端 Key，并填写：

```dotenv
IMAGE_PROVIDER_BASE_URL=https://<your-relay-host>
IMAGE_PROVIDER_API_KEY=<your-relay-key>
IMAGE_PROVIDER_MODEL=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL=gpt-image-2.5-flare
IMAGE_PROVIDER_FALLBACK_MODEL_2=gpt-image-2.5-sunburst
IMAGE_PROVIDER_FALLBACK_MODEL_3=gpt-image-2
```

中转站必须支持项目使用的 `/v1/images/generations` 和 `/v1/images/edits` 合约。先在隔离环境验证 JSON 或 multipart 图片传输，再开放角色工作室；不要把远端 Key 交给前端。

### 本地 Nemotron（可选）

DGX Spark 上可使用仓库脚本启动 vLLM OpenAI-compatible 服务：

```bash
export LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
bash deploy/start_nemotron_lightning.sh
```

后端配置：

```dotenv
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
```

启动后检查 `http://127.0.0.1:8001/v1/models`，确认模型名与配置完全一致。脚本会检查 52 个权重分片；模型未加载时，后端可以回退到 StepFun，但不会把其他模型冒充 Nemotron。

## 5. 安装依赖、构建和启动

```bash
bash deploy/start.sh
```

脚本会启动 PostgreSQL、创建后端虚拟环境、安装 Python 依赖、安装前端依赖、执行 `npm run build`，最后由 Uvicorn 在 `0.0.0.0:9000` 提供前端、API 和媒体静态文件。

手动启动可使用：

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

部署完成后访问 `http://<server-ip>:9000`，并检查：

```bash
curl http://127.0.0.1:9000/api/health
```

返回 `ok: true` 后，再从开发者设置页检查 Provider、模型和付费熔断状态。

## 6. 首次部署验收清单

```bash
# 应用健康
curl -fsS http://127.0.0.1:9000/api/health

# 端口监听
ss -ltnp | rg ':9000'

# 前端构建
test -f frontend/dist/index.html

# 数据库容器
docker compose -f deploy/docker-compose.yml ps
```

真实本地模型额外检查：

```bash
curl -fsS http://127.0.0.1:8001/v1/models
```

返回的模型 ID 必须与 `LOCAL_LLM_MODEL` 完全一致。`/api/health` 只证明应用进程可响应，不等于每个外部 Provider 都可用；Provider 的选择、跳过原因和熔断状态应在开发者设置页核对。

## 7. 配置建议

| 场景 | `PROVIDER_MODE` | `FAL_PAID_GENERATION_ENABLED` | `RUNTIME_PROFILE` |
| --- | --- | --- | --- |
| 页面开发 | `mock` | `false` | `AGENT_LOCAL_PROFILE` |
| 文本模型演示 | `hybrid` | `false` | `AGENT_LOCAL_PROFILE` |
| 人工视频测试 | `live` 或 `hybrid` | 按需 `true` | `AGENT_LOCAL_PROFILE` |
| 本地视频实验 | `live` | `false` | `VIDEO_LOCAL_PROFILE` |

Jev 推荐预生成视频保持关闭，可以先展示选项和文本结果；只有玩家实际选择或明确进行媒体测试时才提交 H3 任务。

## 8. 生产安全注意事项

- `/dev/*` 是开发者接口，公网部署必须通过反向代理、VPN 或访问控制保护。
- `/media` 与 `/files` 使用静态文件服务，公网环境应增加签名 URL 或鉴权。
- `session_id` 当前承担会话访问凭据角色，多用户生产环境需要接入账号和权限系统。
- 断开 SSH 后仍需保持服务运行时，请使用 systemd、Docker restart policy 或 `setsid`；不要依赖交互式终端后台进程。
- 更新代码前先检查活动媒体任务，避免重复提交付费请求；更新后再次检查 `/api/health`、前端构建产物和本地模型 `/v1/models`。

## 9. 更新、回滚和 SSH 断连

更新应用时：

1. `git pull --ff-only`，确认当前 commit。
2. 检查 `/api/dev/jobs` 是否有活动媒体任务，避免更新过程中重复提交。
3. 只重启后端和前端；不要随意停止 Nemotron 或本地视频容器。
4. 更新后重新执行健康、端口、前端资源和模型 `/v1/models` 检查。

使用 systemd 或 Docker 的 `restart: unless-stopped` 保持 SSH 断开后的服务；临时手工启动可以使用 `setsid`：

```bash
setsid bash deploy/start.sh </dev/null >interaction-start.log 2>&1 &
```

若新版本启动失败，回滚到上一个已知 commit 后重新构建前端，再检查数据库迁移和活动任务。不要通过删除 PostgreSQL volume 解决应用启动问题。

## 10. 离线回归

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db \
PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false \
.venv/bin/python -m pytest tests/ -q
cd ../frontend
npm ci
npm run build
```

离线回归不会调用 StepFun、Jev、fal.ai 或图片中转，也不会产生付费媒体任务。

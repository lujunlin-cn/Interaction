# Interaction · 互动短剧平台

Interaction 是一个面向 Agent Skills 的互动短剧创作与游玩平台。创作者可以用自然语言创建世界、戏剧、角色和机制；玩家可以选择推荐行动，也可以输入自己的行动；系统通过可版本化的 Agent Skills、分支状态机和受控媒体管线把行动推进为下一幕。

## 项目文档

- [项目说明文档](docs/PROJECT_DESCRIPTION.md)
- [部署说明](docs/DEPLOYMENT_GUIDE.md)
- [技术栈说明](docs/TECH_STACK.md)
- [运维手册](DEPLOYMENT.md)
- [安全与已知限制](SECURITY_KNOWN_LIMITATIONS.md)

## 快速开始

离线开发不需要外部 API：

```bash
cd /home/hajimi2025/interaction
cp backend/.env.example backend/.env
# 将 PROVIDER_MODE=mock，保持 FAL_PAID_GENERATION_ENABLED=false
bash deploy/start.sh
```

启动后访问 `http://127.0.0.1:9000`。真实 Provider 的接入方式、密钥注入和 NVIDIA 本地模型启动方式见[部署说明](docs/DEPLOYMENT_GUIDE.md)。任何外部凭据都只能放在服务端 Secret 或 `backend/.env`，不能提交到 Git，也不能写进前端环境变量、日志和截图。

## 架构概览

```text
React + TypeScript + Vite
          │ REST / WebSocket
FastAPI + Runtime + Agent Skills
          │
PostgreSQL ─ Provider Router ─ Nemotron / StepFun / Jev / Image Relay / fal H3
```

Runtime 保持 StateManager 为唯一 Canonical 提交入口。Skill 只能提出经过 schema 校验的 Proposal；分支必须达到 READY 后才能展示，媒体失败会进入可恢复状态，不会伪造成功结果。`mock` 模式用于无费用开发和回归，`live` / `hybrid` 模式才会调用真实 Provider。

## 测试

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db \
PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false \
.venv/bin/python -m pytest tests/ -q
cd ../frontend
npm ci
npm run build
```

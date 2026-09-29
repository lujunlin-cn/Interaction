# PlotShift

PlotShift 是一个由 Agent Skills 驱动的互动短剧平台。创作者用自然语言建立世界、角色和戏剧冲突，玩家在每一幕选择推荐行动或输入自己的计划，系统在已确认的世界状态上继续编排剧情、机制、镜头和媒体。

## 文档

- [项目说明](docs/PROJECT_DESCRIPTION.md)：产品体验、核心亮点和架构设计
- [部署说明](docs/DEPLOYMENT_GUIDE.md)：本地算力、外部 API、模型和生产部署
- [技术栈说明](docs/TECH_STACK.md)：NVIDIA、StepFun、Provider、Runtime 和 Skills

## 快速启动

离线模式不会请求外部模型，也不会产生图片或视频费用，适合先检查页面、数据库和回合状态机：

```bash
git clone https://github.com/lujunlin-cn/PlotShift.git
cd PlotShift
cp backend/.env.example backend/.env
sed -i 's/^PROVIDER_MODE=.*/PROVIDER_MODE=mock/' backend/.env
bash deploy/start.sh
```

打开 <http://127.0.0.1:9000>。需要真实模型时，按[部署说明](docs/DEPLOYMENT_GUIDE.md)在服务器端填写自己的密钥；密钥不放进浏览器，也不提交到 Git。

视频生成提示：Fal.ai 的 `minimax/h3-max/reference-to-video` 属于远端队列服务，单个视频实际可能等待约 60 秒；本地开发和现场演示建议部署 Sol-H3，并使用 `VIDEO_LOCAL_PROFILE`。

## 检查服务

```bash
curl -fsS http://127.0.0.1:9000/api/health
ss -ltnp | grep ':9000'
```

## 开发测试

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./itest.db \
PROVIDER_MODE=mock PROFILE_LIFECYCLE_ENABLED=false \
.venv/bin/python -m pytest tests/ -q
cd ../frontend
npm ci
npm run build
```

仓库中的运行数据库、临时截图、验收材料和本地凭据不属于发布文档。代码内部仍保留 `interaction` 目录名，是 Python 模块和历史数据库兼容路径；产品、仓库和对外文档名称统一为 PlotShift。

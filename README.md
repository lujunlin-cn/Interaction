# Interaction

Interaction 是一个可以“自己行动”的互动短剧平台。创作者用自然语言搭建故事，玩家在每一幕选择推荐行动或输入自己的行动，系统根据已确认的世界状态继续写作、安排镜头并播放下一幕。

## 从这里开始

- [项目说明](docs/PROJECT_DESCRIPTION.md)：产品、用户流程和系统架构
- [部署说明](docs/DEPLOYMENT_GUIDE.md)：从零启动、接入外部模型和更新服务
- [技术栈](docs/TECH_STACK.md)：代码目录、运行时、Agent Skills 和 Provider 路由

## 最快启动：离线模式

离线模式不调用外部模型，也不会产生图片或视频费用，适合先确认页面和数据库工作正常。

```bash
git clone https://github.com/lujunlin-cn/Interaction.git
cd Interaction
cp backend/.env.example backend/.env
sed -i 's/^PROVIDER_MODE=.*/PROVIDER_MODE=mock/' backend/.env
bash deploy/start.sh
```

打开 <http://127.0.0.1:9000>。需要真实模型时，按[部署说明](docs/DEPLOYMENT_GUIDE.md)填写服务端环境变量。

## 常用检查

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

仓库中的公开文档只保留项目说明、部署说明和技术栈说明。运行数据库、临时截图、验收记录和本地凭据不属于发布内容。

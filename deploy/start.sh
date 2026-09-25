#!/usr/bin/env bash
# DGX Spark 一键部署：数据库 → 后端依赖 → 前端构建 → 启动服务
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5 启动 PostgreSQL (Docker, 127.0.0.1:5433) =="
docker compose -f deploy/docker-compose.yml up -d
for i in $(seq 1 30); do
  if docker exec interaction-drama-db pg_isready -U drama -d interaction_drama >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "== 2/5 后端依赖 =="
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install -q -r backend/requirements.txt

echo "== 3/5 环境配置 =="
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "  已生成 backend/.env（请填入 STEP_API_KEY / FAL_KEY 等后切换到 live/hybrid）"
fi

echo "== 4/5 前端构建 =="
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
(cd frontend && npm run build)

echo "== 5/5 启动服务（单端口 9000，前端+API+媒体） =="
mkdir -p backend/data
cd backend
# Parse dotenv values without evaluating shell commands. This keeps lifecycle
# hooks such as `pkill -f ...` as data and prevents a malformed .env from
# aborting deployment before uvicorn starts.
exec .venv/bin/python - <<'PY'
import os
from pathlib import Path

for raw in Path('.env').read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

import uvicorn
uvicorn.run('app.main:app', host='0.0.0.0', port=9000)
PY

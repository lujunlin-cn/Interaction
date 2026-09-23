"""pytest 共享 fixture：单一 TestClient / 单一路径 SQLite，避免模块间互相删库。"""
import os

import pytest

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./itest.db"
os.environ["PROVIDER_MODE"] = "mock"
os.environ["BRANCH_PHASE_DELAY_MS"] = "30"
os.environ["MOCK_SHOT_DURATION"] = "1"
os.environ["TIMED_TIMEOUT_OVERRIDE"] = "5"     # 限时互动测试加速


@pytest.fixture(scope="session")
def client():
    for f in ("itest.db",):
        if os.path.exists(f):
            os.remove(f)
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c

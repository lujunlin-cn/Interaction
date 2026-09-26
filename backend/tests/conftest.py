"""pytest 共享 fixture：单一 TestClient / 单一路径 SQLite，避免模块间互相删库。"""
import os
import tempfile

import pytest

# Unique process-owned database; parallel research/UX regressions must not
# delete each other's SQLite files or inherit live profile lifecycle hooks.
_test_data = tempfile.TemporaryDirectory(prefix="interaction-tests-")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.join(_test_data.name, "test.db")
os.environ["PROFILE_LIFECYCLE_ENABLED"] = "false"
os.environ["PROVIDER_MODE"] = "mock"
# The deployment can defer speculative media. Offline tests use the product
# default; deferred-media tests explicitly override this setting themselves.
os.environ["PRE_GENERATE_RECOMMENDATION_MEDIA"] = "true"
os.environ["BRANCH_PHASE_DELAY_MS"] = "30"
os.environ["MOCK_SHOT_DURATION"] = "1"
os.environ["TIMED_TIMEOUT_OVERRIDE"] = "5"     # 限时互动测试加速
# Media, uploads and paid-attempt audit must never touch the live data tree.
os.environ["DATA_DIR"] = _test_data.name
os.environ["MEDIA_DIR"] = os.path.join(_test_data.name, "media")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c

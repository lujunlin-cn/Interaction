"""应用入口：FastAPI + 静态前端 + 媒体目录 + 启动种子。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import select

from .config import settings
from .db import Base, engine as db_engine, SessionLocal
from .db_models import ScenarioRow, ScenarioVersionRow
from .domain.schemas import RuntimeProfile, now_ms
from .providers.real import build_provider_registry
from .providers.router import ProviderRouter
from .runtime.engine import RuntimeEngine
from .seed.rainy_apartment import rainy_apartment

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("drama")


def build_runtime() -> tuple[RuntimeEngine, ProviderRouter]:
    registry = build_provider_registry(settings.provider_mode)
    # mock：全部走 Mock；hybrid：文本/决策/视频优先真实 Provider，允许显式 Mock 降级；
    # live：完整 PRD 冻结矩阵。真实 Provider 不可用时由 Router 按规则降级/熔断。
    router = ProviderRouter(registry, mode=settings.provider_mode,
                            profile=RuntimeProfile(settings.runtime_profile))
    engine = RuntimeEngine(router)
    return engine, router


runtime_engine, provider_router = build_runtime()


async def seed_if_empty() -> None:
    """内置 Scenario「雨夜公寓」+ 全局角色库种子。

    官方内容是幂等 upsert：部署更新时 snapshot 与角色库随之刷新；
    用户的草稿/会话不受影响。已发布版本号不变（内容修正走同一 ver_rainy_1_0_0）。
    """
    from .db_models import GlobalCharacterRow

    draft = rainy_apartment()
    snapshot = draft.model_dump(mode="json")
    now = now_ms()
    async with SessionLocal() as db:
        async with db.begin():
            existing = await db.get(ScenarioRow, "rainy_apartment")
            if existing is None:
                db.add(ScenarioRow(id=draft.id, status="PUBLISHED", draft=snapshot,
                                   updated_at=now))
                logger.info("seeded scenario rainy_apartment v%s", draft.version)
            elif existing.draft != snapshot:
                existing.draft = snapshot
                existing.updated_at = now
                logger.info("refreshed scenario rainy_apartment snapshot")
            ver = await db.get(ScenarioVersionRow, "ver_rainy_1_0_0")
            if ver is None:
                db.add(ScenarioVersionRow(id="ver_rainy_1_0_0", scenario_id=draft.id,
                                          version=draft.version, snapshot=snapshot,
                                          created_at=now))
            elif ver.snapshot != snapshot:
                ver.snapshot = snapshot
        async with db.begin():
            alice = await db.get(GlobalCharacterRow, "chr_alice")
            if alice is None:
                db.add(GlobalCharacterRow(
                    id="chr_alice", name="Alice",
                    data={"id": "chr_alice", "name": "Alice",
                          "bio": "即将离城的档案修复师；谨慎、温柔，不轻易交付信任。",
                          "personality": "谨慎、温柔、不轻易交付信任",
                          "tags": ["悬疑", "雨夜公寓", "官方角色"],
                          "created_at": now, "updated_at": now},
                    version=1, updated_at=now))
                logger.info("seeded global character chr_alice")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_if_empty()
    logger.info("provider_mode=%s profile=%s", settings.provider_mode, settings.runtime_profile)
    yield


app = FastAPI(title="Interactive Drama Runtime", lifespan=lifespan)
_cors = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_cors or ["http://127.0.0.1:9000"],
                   allow_methods=["*"], allow_headers=["*"])

from .api.routes import build_api, build_ws_router  # noqa: E402

app.include_router(build_api(runtime_engine, provider_router))
app.include_router(build_ws_router(runtime_engine))

# Private audit files share the data root, but must never be served as assets.
class PublicAssetFiles(StaticFiles):
    async def get_response(self, path, scope):
        if any(part.startswith(".") for part in Path(path).parts):
            raise StarletteHTTPException(status_code=404)
        return await super().get_response(path, scope)


# 媒体目录（生成的场景视频 / 素材）
app.mount("/media", StaticFiles(directory=str(settings.media_path)), name="media")
app.mount("/files", PublicAssetFiles(directory=str(settings.data_path)), name="files")

# 前端构建产物（存在时托管，单端口部署）
_frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")

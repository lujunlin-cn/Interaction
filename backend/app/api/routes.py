"""REST + WebSocket API 层。薄路由：业务逻辑全部在 runtime / domain / providers。"""
from __future__ import annotations

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..db_models import AssetRow, FeedbackRow
from ..domain.ids import uid
from ..domain.schemas import Asset, AssetType, PlayerExperienceFeedback, now_ms
from ..providers.router import ProviderRouter
from ..runtime.engine import EngineError, RuntimeEngine
from ..runtime.scenario_service import CharacterService, ScenarioService
from ..runtime.tracer import tracer
from ..skills.registry import registry as skills_registry


class CreateSessionReq(BaseModel):
    version_id: str


class ActionReq(BaseModel):
    text: str


class SelectReq(BaseModel):
    branch_id: str


class PlayerCmdReq(BaseModel):
    command: str            # play / pause / skip


class WishReq(BaseModel):
    text: str


class InstructReq(BaseModel):
    instruction: str


class IdeaReq(BaseModel):
    idea: str


class FeedbackReq(BaseModel):
    session_id: str | None = None
    name: str = ""
    relation: str = ""
    guided: str = ""
    liked: str
    reasons: str
    relevant_turn: str = ""
    wants_continue: str = ""


class IntentConfirmReq(BaseModel):
    approved: bool = True
    action: str = ""
    desire: str = ""
    strategy: str = ""


class SkillToggleReq(BaseModel):
    enabled: bool


class ProfileSwitchReq(BaseModel):
    target: str            # AGENT_LOCAL_PROFILE / VIDEO_LOCAL_PROFILE


class FixtureReq(BaseModel):
    key: str               # confidence / response / leak_secret
    value: object = None


def build_api(engine: RuntimeEngine, router: ProviderRouter) -> APIRouter:
    api = APIRouter(prefix="/api")
    scenarios = ScenarioService(router)
    characters = CharacterService()

    # ---------------- 基础 ----------------
    @api.get("/health")
    async def health():
        return {"ok": True, "provider_mode": router.mode, "profile": router.profile.value}

    # ---------------- Scenario ----------------
    @api.get("/scenarios")
    async def list_scenarios():
        drafts = await scenarios.list()
        return {"items": [d.model_dump(mode="json") for d in drafts]}

    @api.post("/scenarios")
    async def create_scenario(req: IdeaReq | None = None):
        if req and req.idea.strip():
            draft = await scenarios.create_from_idea(req.idea.strip())
        else:
            draft = await scenarios.create_empty()
        return draft.model_dump(mode="json")

    @api.get("/scenarios/{sid}")
    async def get_scenario(sid: str):
        draft = await scenarios.get(sid)
        if draft is None:
            raise HTTPException(404, "scenario not found")
        return draft.model_dump(mode="json")

    @api.put("/scenarios/{sid}")
    async def save_scenario(sid: str, draft: dict):
        from ..domain.schemas import ScenarioDraft
        d = ScenarioDraft(**{**draft, "id": sid})
        await scenarios.save_draft(d)
        return d.model_dump(mode="json")

    @api.post("/scenarios/{sid}/instruct")
    async def instruct_scenario(sid: str, req: InstructReq):
        try:
            draft = await scenarios.apply_instruction(sid, req.instruction)
        except KeyError:
            raise HTTPException(404, "scenario not found")
        return draft.model_dump(mode="json")

    @api.post("/scenarios/{sid}/publish")
    async def publish_scenario(sid: str):
        try:
            return await scenarios.publish(sid)
        except KeyError:
            raise HTTPException(404, "scenario not found")

    @api.get("/scenarios/{sid}/versions")
    async def scenario_versions(sid: str):
        return {"items": await scenarios.versions(sid)}

    @api.post("/scenarios/{sid}/duplicate")
    async def duplicate_scenario(sid: str):
        try:
            clone = await scenarios.duplicate(sid)
        except KeyError:
            raise HTTPException(404, "scenario not found")
        return clone.model_dump(mode="json")

    @api.delete("/scenarios/{sid}")
    async def delete_scenario(sid: str):
        await scenarios.delete(sid)
        return {"ok": True}

    # ---------------- 全局角色库 ----------------
    @api.get("/characters")
    async def list_characters(q: str = ""):
        return {"items": await characters.list(q)}

    @api.post("/characters")
    async def create_character(data: dict):
        return await characters.create(data)

    @api.patch("/characters/{cid}")
    async def update_character(cid: str, patch: dict):
        try:
            return await characters.update(cid, patch)
        except KeyError:
            raise HTTPException(404, "character not found")

    # ---------------- 素材 ----------------
    @api.post("/scenarios/{sid}/assets")
    async def upload_asset(sid: str, file: UploadFile, binding: str = "",
                           role: str = "", entity: str = ""):
        suffix = (file.filename or "asset").rsplit(".", 1)[-1] if file.filename else "bin"
        asset_id = uid("asset")
        folder = settings.data_path / "assets" / sid
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{asset_id}.{suffix}"
        size = 0
        async with aiofiles.open(path, "wb") as f:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                await f.write(chunk)
        mime = file.content_type or ""
        atype = AssetType.IMAGE if mime.startswith("image/") else \
            AssetType.VIDEO if mime.startswith("video/") else \
            AssetType.VOICE if mime.startswith("audio/") else AssetType.IMAGE
        asset = Asset(id=asset_id, scenario_id=sid, type=atype, name=file.filename or asset_id,
                      mime=mime, size=size, storage_path=str(path.relative_to(settings.data_path)),
                      binding=binding, role=role, entity=entity, source="upload")
        async with SessionLocal() as db:
            async with db.begin():
                db.add(AssetRow(id=asset_id, scenario_id=sid,
                                data=asset.model_dump(mode="json"), created_at=now_ms()))
        await engine.refresh_assets(sid)
        return asset.model_dump(mode="json")

    @api.put("/scenarios/{sid}/assets/{aid}")
    async def replace_asset(sid: str, aid: str, file: UploadFile):
        """替换素材文件：版本递增（FR-007），活跃会话的候选分支按指纹保守失效。"""
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(AssetRow, aid)
                if row is None or row.scenario_id != sid:
                    raise HTTPException(404, "asset not found")
                data = dict(row.data)
                old_path = settings.data_path / data.get("storage_path", "")
                suffix = (file.filename or "asset").rsplit(".", 1)[-1] if file.filename else "bin"
                new_id_path = settings.data_path / "assets" / sid / f"{aid}_v{data.get('version', 1) + 1}.{suffix}"
                new_id_path.parent.mkdir(parents=True, exist_ok=True)
                size = 0
                async with aiofiles.open(new_id_path, "wb") as f:
                    while chunk := await file.read(1 << 20):
                        size += len(chunk)
                        await f.write(chunk)
                data["storage_path"] = str(new_id_path.relative_to(settings.data_path))
                data["size"] = size
                data["mime"] = file.content_type or data.get("mime", "")
                data["name"] = file.filename or data.get("name", aid)
                data["version"] = int(data.get("version", 1)) + 1
                row.data = data
                updated = dict(data)
        if old_path.exists() and str(old_path) != str(settings.data_path / updated["storage_path"]):
            old_path.unlink(missing_ok=True)
        await engine.refresh_assets(sid)
        return updated

    @api.delete("/scenarios/{sid}/assets/{aid}")
    async def remove_asset(sid: str, aid: str):
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(AssetRow, aid)
                if row is None or row.scenario_id != sid:
                    raise HTTPException(404, "asset not found")
                path = settings.data_path / row.data.get("storage_path", "")
                await db.delete(row)
        path.unlink(missing_ok=True)
        await engine.refresh_assets(sid)
        return {"ok": True}

    @api.get("/scenarios/{sid}/assets")
    async def list_assets(sid: str):
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(AssetRow).where(AssetRow.scenario_id == sid)
                .order_by(AssetRow.created_at.desc()))).scalars().all()
        return {"items": [r.data for r in rows]}

    # ---------------- Session / Player ----------------
    @api.post("/sessions")
    async def create_session(req: CreateSessionReq):
        try:
            state = await engine.create_session(req.version_id)
        except EngineError as e:
            raise HTTPException(404, str(e))
        return {"session_id": state.id}

    @api.get("/sessions/{sid}/view")
    async def session_view(sid: str):
        state = await engine.load_session(sid)
        if state is None:
            raise HTTPException(404, "session not found")
        return engine.player_view(state)

    @api.post("/sessions/{sid}/select")
    async def select_branch(sid: str, req: SelectReq):
        try:
            return await engine.select_branch(sid, req.branch_id)
        except EngineError as e:
            raise HTTPException(409, str(e))

    @api.post("/sessions/{sid}/action")
    async def free_action(sid: str, req: ActionReq):
        if not req.text.strip():
            raise HTTPException(400, "empty action")
        try:
            return await engine.free_action(sid, req.text.strip())
        except EngineError as e:
            raise HTTPException(409, str(e))

    @api.post("/sessions/{sid}/intent/confirm")
    async def confirm_intent(sid: str, req: IntentConfirmReq):
        try:
            return await engine.confirm_intent(sid, req.approved, req.action,
                                               req.desire, req.strategy)
        except EngineError as e:
            raise HTTPException(409, str(e))

    @api.post("/sessions/{sid}/cancel")
    async def cancel_generation(sid: str):
        try:
            return await engine.cancel_generation(sid)
        except EngineError as e:
            raise HTTPException(404, str(e))

    @api.post("/sessions/{sid}/player")
    async def player_command(sid: str, req: PlayerCmdReq):
        try:
            return await engine.player_command(sid, req.command)
        except EngineError as e:
            raise HTTPException(404, str(e))

    @api.post("/sessions/{sid}/receipt")
    async def commit_receipt(sid: str):
        await engine.commit_receipt(sid)
        return {"ok": True}

    @api.post("/sessions/{sid}/wishes")
    async def add_wish(sid: str, req: WishReq):
        try:
            wish = await engine.add_wish(sid, req.text)
            return wish.model_dump(mode="json")
        except EngineError as e:
            raise HTTPException(404, str(e))

    @api.delete("/sessions/{sid}/wishes/{wish_id}")
    async def withdraw_wish(sid: str, wish_id: str):
        await engine.withdraw_wish(sid, wish_id)
        return {"ok": True}

    @api.post("/sessions/{sid}/continue")
    async def continue_world(sid: str):
        try:
            return await engine.continue_world(sid)
        except EngineError as e:
            raise HTTPException(409, str(e))

    # ---------------- 开发者 Inspector ----------------
    @api.get("/dev/sessions/{sid}/state")
    async def dev_state(sid: str):
        state = await engine.load_session(sid)
        if state is None:
            raise HTTPException(404, "session not found")
        return state.model_dump(mode="json")

    @api.get("/dev/sessions/{sid}/branches")
    async def dev_branches(sid: str):
        state = await engine.load_session(sid)
        if state is None:
            raise HTTPException(404, "session not found")
        return {"items": [b.model_dump(mode="json") for b in state.branches]}

    @api.get("/dev/sessions/{sid}/events")
    async def dev_events(sid: str):
        state = await engine.load_session(sid)
        if state is None:
            raise HTTPException(404, "session not found")
        return {"items": [e.model_dump(mode="json") for e in state.events]}

    @api.get("/dev/traces")
    async def dev_traces(limit: int = 200):
        return {"items": [s.model_dump(mode="json") for s in tracer.recent[-limit:]]}

    @api.get("/dev/providers")
    async def dev_providers():
        return {"mode": router.mode, "profile": router.profile.value,
                "health": router.health_snapshot(), "matrix": router.route_matrix(),
                "events": router.events[-100:]}

    @api.post("/dev/providers/recover")
    async def dev_providers_recover():
        router.recover_all()
        return {"ok": True}

    @api.post("/dev/providers/inject")
    async def dev_providers_inject(data: dict):
        router.inject_failure(data.get("provider", ""), data.get("kind", "retryable_transient"))
        return {"ok": True}

    # ---------------- 开发者：Profile / 夹具 / 本地任务 ----------------
    @api.get("/dev/profile")
    async def dev_profile():
        return router.profile_status()

    @api.post("/dev/profile/switch")
    async def dev_profile_switch(req: ProfileSwitchReq):
        from ..domain.schemas import RuntimeProfile
        from ..providers.router import ProviderError
        try:
            target = RuntimeProfile(req.target)
        except ValueError:
            raise HTTPException(400, f"unknown profile: {req.target}")

        async def drained() -> bool:
            return all(t.done() for t in engine._pipeline_tasks.values())

        try:
            result = await router.switch_profile(target, drain_check=drained)
        except ProviderError as e:
            raise HTTPException(409, str(e))
        return result

    @api.get("/dev/fixtures")
    async def dev_fixtures_get():
        from ..providers import fixtures
        return fixtures.get()

    @api.post("/dev/fixtures")
    async def dev_fixtures_set(req: FixtureReq):
        from ..providers import fixtures
        if req.key == "reset":
            fixtures.reset()
            return fixtures.get()
        if not fixtures.set_fixture(req.key, req.value):
            raise HTTPException(400, f"unknown fixture: {req.key}")
        return fixtures.get()

    @api.post("/dev/local-task")
    async def dev_local_task(data: dict):
        """显式提交 Sol-H3 本地视频任务（FR-026 / 演示 D8：独立任务不污染分支管线）。"""
        from ..domain.schemas import GenerationJob, JobStatus
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            raise HTTPException(400, "empty prompt")
        provider, rec = router.video_provider(local=True)
        job = GenerationJob(id=uid("job"), provider=rec.selected or "sol_h3_local",
                            profile=router.profile.value,
                            status=JobStatus.QUEUED, standalone=True,
                            request={"prompt": prompt})
        handle = await provider.submit({"job_id": job.id,
                                        "shots": [{"id": "shot_1", "title": prompt[:24],
                                                   "subtitle": prompt[:60],
                                                   "duration": settings.mock_shot_duration}],
                                        "prompt": prompt})
        job.status = JobStatus.GENERATING
        job.output = {"handle": handle.provider_job_id}
        async with SessionLocal() as db:
            async with db.begin():
                from ..db_models import JobRow
                db.add(JobRow(id=job.id, session_id=None, branch_id=None,
                              provider=job.provider, status=job.status.value,
                              data=job.model_dump(mode="json"),
                              started_at=job.started_at))
        return job.model_dump(mode="json")

    # ---------------- Skills / Feedback ----------------
    @api.get("/skills")
    async def list_skills():
        return skills_registry()

    @api.post("/skills/{skill_id}/toggle")
    async def toggle_skill(skill_id: str, req: SkillToggleReq):
        from ..skills.registry import set_enabled
        if not set_enabled(skill_id, req.enabled):
            raise HTTPException(404, "skill not found")
        await tracer.emit("skill.toggle", "success",
                          output={"skill": skill_id, "enabled": req.enabled})
        return skills_registry()

    @api.post("/feedback")
    async def submit_feedback(req: FeedbackReq):
        fb = PlayerExperienceFeedback(id=uid("fb"), **req.model_dump())
        async with SessionLocal() as db:
            async with db.begin():
                db.add(FeedbackRow(id=fb.id, data=fb.model_dump(mode="json"), at=fb.at))
        return {"ok": True, "id": fb.id}

    return api


def build_ws_router(engine: RuntimeEngine) -> APIRouter:
    ws_router = APIRouter()

    @ws_router.websocket("/ws/sessions/{sid}")
    async def session_ws(websocket: WebSocket, sid: str):
        await websocket.accept()
        state = await engine.load_session(sid)
        if state is None:
            await websocket.close(code=4404)
            return
        engine.subscribers.setdefault(sid, []).append(websocket)
        tracer.subscribe(websocket)
        try:
            await websocket.send_json({"type": "state", "view": engine.player_view(state)})
            while True:
                # 客户端可发 {"command": "play"/"pause"/"skip"} 或心跳
                msg = await websocket.receive_json()
                cmd = msg.get("command")
                if cmd in ("play", "pause", "skip"):
                    await engine.player_command(sid, cmd)
                elif msg.get("type") == "receipt":
                    await engine.commit_receipt(sid)
        except WebSocketDisconnect:
            pass
        finally:
            subs = engine.subscribers.get(sid, [])
            if websocket in subs:
                subs.remove(websocket)
            tracer.unsubscribe(websocket)

    return ws_router

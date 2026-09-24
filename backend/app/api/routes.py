"""REST + WebSocket API 层。薄路由：业务逻辑全部在 runtime / domain / providers。"""
from __future__ import annotations

import asyncio

import aiofiles
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
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


class PublishReq(BaseModel):
    reviewed: bool = False          # G18：发布需显式「我已审阅」
    play: bool = False              # G19：发布并试玩


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
    from ..runtime.character_service import CharacterAssetService
    from ..domain.schemas import CharacterAssetStatus
    char_assets = CharacterAssetService(router)

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
            try:
                draft = await scenarios.create_from_idea(req.idea.strip())
            except Exception as error:
                await tracer.emit("authoring.draft", "failed", input_={"idea": req.idea}, output={"error": repr(error)})
                raise HTTPException(502, "故事草案暂时没有生成成功，你的描述可保留后重试。")
            from ..runtime.creator_projection import propose
            try:
                await propose(scenarios, draft.id, "drama")
                draft = await scenarios.get(draft.id)
            except Exception as error:
                await tracer.emit("authoring.projection", "failed", input_={"scenario_id": draft.id}, output={"error": str(error)})
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
        incoming = ScenarioDraft(**{**draft, "id": sid})
        from ..domain.mechanic_spec import validate_mechanics
        try:
            incoming.mechanics = validate_mechanics(incoming.mechanics)
        except ValueError:
            raise HTTPException(422, "玩法配置不符合已安装玩法的类型或权限，请检查后保存。")
        # G17：对比旧草案，把人工编辑写入结构化 changes
        old = await scenarios.get(sid)
        if old is not None:
            incoming.changes = list(old.changes)
            for path in ("title", "description", "genre", "tone", "play_style",
                         "player_character",
                         "world.rules", "world.lore", "world.locations", "world.constraints",
                         "drama.core_question", "drama.central_conflict", "drama.truth_model",
                         "drama.secrets", "drama.misbeliefs", "drama.pressures",
                         "drama.anchors", "drama.ending_families", "drama.foreshadows",
                         "drama.forbidden_outcomes", "drama.timed_interactions",
                         "theme.accent", "theme.font", "theme.density",
                         "theme.subtitles", "theme.background"):
                before = ScenarioService._get_path(old, path)
                after = ScenarioService._get_path(incoming, path)
                if before != after:
                    incoming.changes.append({
                        "path": path, "before": before, "after": after,
                        "reason": "", "source": "manual", "at": now_ms()})
            for key in set(old.mechanics) | set(incoming.mechanics):
                before = old.mechanics[key].model_dump(mode="json") if key in old.mechanics else None
                after = incoming.mechanics[key].model_dump(mode="json") if key in incoming.mechanics else None
                if before != after:
                    incoming.changes.append({"path": f"mechanics.{key}", "before": before,
                        "after": after, "reason": "", "source": "manual", "at": now_ms()})
            # 角色级差异（按 id 对齐逐字段对比）
            old_chars = {c.id: c for c in old.characters}
            for c in incoming.characters:
                oc = old_chars.get(c.id)
                if oc is None:
                    incoming.changes.append({"path": f"characters[{c.id}]",
                        "before": None, "after": c.identity, "reason": "",
                        "source": "manual", "at": now_ms()})
                    continue
                for f in ("identity", "personality", "desire", "fear", "secrets",
                          "knowledge", "relationship", "visual_state"):
                    bv, av = getattr(oc, f), getattr(c, f)
                    if bv != av:
                        incoming.changes.append({
                            "path": f"characters[{c.id}].{f}", "before": bv, "after": av,
                            "reason": "", "source": "manual", "at": now_ms()})
        try:
            await scenarios.save_draft(incoming)
        except ValueError:
            raise HTTPException(422, "玩法配置不符合已安装玩法的类型或权限，请检查后保存。")
        return incoming.model_dump(mode="json")

    @api.post("/scenarios/{sid}/instruct")
    async def instruct_scenario(sid: str, req: InstructReq):
        try:
            draft = await scenarios.apply_instruction(sid, req.instruction)
        except KeyError:
            raise HTTPException(404, "scenario not found")
        return draft.model_dump(mode="json")

    @api.post("/scenarios/{sid}/understanding")
    async def creator_understanding(sid: str, data: dict):
        from ..runtime.creator_projection import propose
        try:
            return await propose(scenarios, sid, data.get("scope", "drama"),
                                 data.get("instruction", ""), data.get("character_id", ""))
        except KeyError:
            raise HTTPException(404, "故事不存在")
        except Exception as e:
            await tracer.emit("authoring.projection", "failed", output={"error": str(e)})
            raise HTTPException(422, "这次理解暂时没有完成，请保留描述后重试。")

    @api.post("/scenarios/{sid}/understanding/confirm")
    async def confirm_understanding(sid: str, data: dict):
        from ..runtime.creator_projection import accept
        try:
            draft = await accept(scenarios, sid, data["projection_id"], data.get("answers", {}))
            return draft.model_dump(mode="json")
        except (ValueError, KeyError) as e:
            await tracer.emit("authoring.confirm", "failed", output={"error": str(e)})
            message = str(e) if any(word in str(e) for word in ("已锁定", "已被修改", "建议已更新")) else "这项建议与故事设置不一致，请更新理解后重试。"
            raise HTTPException(409, message)

    @api.post("/scenarios/{sid}/characters/{cid}/promote")
    async def promote_story_character(sid: str, cid: str):
        draft = await scenarios.get(sid)
        sc = next((c for c in draft.characters if c.id == cid), None) if draft else None
        if not sc or not sc.global_character_id:
            raise HTTPException(422, "请先绑定全局角色")
        # Explicit promotion only. Existing published snapshots remain unchanged.
        patch = {"personality": sc.personality, "appearance": sc.visual_state,
                 **{"default_" + k: getattr(sc, k) for k in ("desire", "fear", "secrets", "knowledge", "relationship")}}
        await characters.update(sc.global_character_id, patch)
        version = await char_assets._new_version(sc.global_character_id, "METADATA")
        await tracer.emit("character.overlay_promote", "success", input_={"scenario": sid, "character": cid},
                          output={"version": version.version, "changes": patch})
        return version.model_dump(mode="json")

    @api.get("/scenarios/{sid}/publish-check")
    async def publish_check(sid: str):
        """发布前检查清单（不发布，仅预览 gate 结果）。"""
        draft = await scenarios.get(sid)
        if draft is None:
            raise HTTPException(404, "scenario not found")
        return {"checklist": scenarios.publish_checklist(draft)}

    @api.post("/scenarios/{sid}/publish")
    async def publish_scenario(sid: str, req: PublishReq | None = None):
        try:
            result = await scenarios.publish(sid, reviewed=bool(req and req.reviewed))
        except KeyError:
            raise HTTPException(404, "scenario not found")
        # FR-091/Q86：为绑定全局角色的 ScenarioCharacter 冻结版本快照
        draft = await scenarios.get(sid)
        snapshot_ids: list[str] = []
        if draft:
            for sc in draft.characters:
                if not getattr(sc, "global_character_id", None):
                    continue
                try:
                    snap = await char_assets.snapshot_for_scenario(
                        result["version_id"], sc.global_character_id,
                        version=sc.global_character_version,
                        overrides={k: getattr(sc, k) for k in ("identity", "personality", "desire", "fear", "secrets", "knowledge", "relationship", "visual_state")})
                    snapshot_ids.append(snap.id)
                except KeyError:
                    raise HTTPException(422, f"global character not found: {sc.global_character_id}")
        if snapshot_ids:
            result["character_snapshots"] = snapshot_ids
        if req and req.play:
            state = await engine.create_session(result["version_id"])
            result["session_id"] = state.id
        return result

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
        if not str(data.get("name", "")).strip() or not str(data.get("bio", "")).strip():
            raise HTTPException(422, "请填写名字和一句话角色定义")
        result = await characters.create(data)
        await char_assets._new_version(result["id"], "IDENTITY")
        return await char_assets.get_character(result["id"])

    @api.patch("/characters/{cid}")
    async def update_character(cid: str, patch: dict):
        try:
            await characters.update(cid, patch)
            await char_assets._new_version(cid, "METADATA")
            return await char_assets.get_character(cid)
        except ValueError:
            raise HTTPException(422, "请检查角色资料；名字和一句话角色定义不能为空。")
        except KeyError:
            raise HTTPException(404, "character not found")

    # ---------------- 角色素材（全局池，scenario_id=__global__）----------------
    GLOBAL_ASSET_SCOPE = "__global__"

    @api.get("/characters/{cid}/assets")
    async def list_character_assets(cid: str):
        """该角色可引用的素材：全局池 + entity 绑定到该角色的条目。"""
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(AssetRow).order_by(AssetRow.created_at.desc()))).scalars().all()
        items = [r.data for r in rows
                 if r.data.get("scenario_id") == GLOBAL_ASSET_SCOPE
                 or r.data.get("entity") == cid]
        return {"items": items}

    @api.post("/characters/{cid}/assets")
    async def upload_character_asset(cid: str, file: UploadFile,
                                     role: str = Form("identity")):
        """上传素材到角色全局池（G11：ref_* 槽位可从这里挑选绑定）。"""
        suffix = (file.filename or "asset").rsplit(".", 1)[-1] if file.filename else "bin"
        asset_id = uid("asset")
        folder = settings.data_path / "assets" / GLOBAL_ASSET_SCOPE
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
        asset = Asset(id=asset_id, scenario_id=GLOBAL_ASSET_SCOPE, type=atype,
                      name=file.filename or asset_id, mime=mime, size=size,
                      storage_path=str(path.relative_to(settings.data_path)),
                      binding=cid, role=role, entity=cid, source="upload")
        async with SessionLocal() as db:
            async with db.begin():
                db.add(AssetRow(id=asset_id, scenario_id=GLOBAL_ASSET_SCOPE,
                                data=asset.model_dump(mode="json"), created_at=now_ms()))
        return asset.model_dump(mode="json")

    @api.post("/characters/{cid}/baseline-image")
    async def import_character_baseline(cid: str, file: UploadFile):
        """从图片创建角色的身份 Candidate；原文件仍保存在全局素材池。"""
        if await char_assets.get_character(cid) is None:
            raise HTTPException(404, "character not found")
        suffix = (file.filename or "portrait").rsplit(".", 1)[-1] if file.filename else "bin"
        asset_id = uid("asset")
        folder = settings.data_path / "assets" / GLOBAL_ASSET_SCOPE
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{asset_id}.{suffix}"
        async with aiofiles.open(path, "wb") as f:
            while chunk := await file.read(1 << 20):
                await f.write(chunk)
        rel = str(path.relative_to(settings.data_path))
        asset = await char_assets.add_asset(
            cid, role="front", url=f"/files/{rel}",
            status=CharacterAssetStatus.CANDIDATE,
            provenance={"source": "upload", "filename": file.filename or asset_id,
                        "capability": "IDENTITY_BASELINE"})
        return asset.model_dump(mode="json")

    # ---------------- 素材 ----------------
    @api.post("/scenarios/{sid}/assets")
    async def upload_asset(sid: str, file: UploadFile, binding: str = Form(""),
                           role: str = Form(""), entity: str = Form("")):
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

    # ---------------- v0.6 Character Asset System ----------------
    @api.post("/characters/{cid}/understanding")
    async def global_character_understanding(cid: str):
        import json
        ch = await char_assets.get_character(cid)
        if not ch:
            raise HTTPException(404, "角色不存在")
        allowed = {"personality", "appearance", "default_desire", "default_fear", "default_secrets", "default_knowledge", "default_relationship"}
        try:
            _, rec, response = await router.call_text("authoring", messages=[
                {"role": "system", "content": "为这个跨故事角色提出可选的稳定默认信息。返回 JSON 对象，值为自然中文字符串，只包含以下字段：" + ",".join(sorted(allowed)) + "。不引入具体故事的秘密或情节。"},
                {"role": "user", "content": json.dumps(ch, ensure_ascii=False)}], output_contract={"purpose": "character_understanding"}, budget={"max_tokens": 2048, "reasoning_effort": "low"})
            from ..runtime.structured_output import decode_object
            result = decode_object(response.content)
            if not isinstance(result, dict) or not result or any(k not in allowed or not isinstance(v, str) for k, v in result.items()):
                raise ValueError("invalid character proposal")
            await tracer.emit("character.understanding", "success", input_={"character_id": cid}, output=result, provider=rec.selected or "", model=response.model)
            return result
        except Exception as e:
            await tracer.emit("character.understanding", "failed", output={"error": str(e), "raw_output": response.content if "response" in locals() else ""})
            raise HTTPException(502, "角色建议暂时没有生成成功，请重试。")

    @api.post("/characters/{cid}/ai-describe")
    async def character_ai_describe(cid: str):
        """FR-096：AI 补全外观描述草案（用户确认后才写入，不自动落库/不生图）。"""
        ch = await char_assets.get_character(cid)
        if ch is None:
            raise HTTPException(404, "character not found")
        prompt = (f"为互动剧角色写一段外观描述（中文、120 字内、只写外貌服饰气质，"
                  f"供图像生成模型参考）。角色名：{ch.get('name','')}；"
                  f"简介：{ch.get('bio','')[:200]}；人格：{ch.get('personality','')[:120]}。"
                  f"直接输出描述文本，不要解释。")
        try:
            _, rec, resp = await router.call_text(
                "authoring", messages=[{"role": "user", "content": prompt}])
            text = (resp.content or "").strip().strip('"').strip()
            return {"appearance": text, "provider": rec.selected or ""}
        except Exception as e:
            raise HTTPException(502, f"describe failed: {e}")

    @api.post("/characters/{cid}/ai-generate")
    async def character_ai_generate(cid: str, data: dict | None = None):
        """AI 建角色生图：nano-banana-2 → 2 张 Candidate（FR-085）。"""
        try:
            prompt = (data or {}).get("prompt", "")
            n = int((data or {}).get("num_images", 2))
            out = await char_assets.ai_generate_candidates(cid, prompt, n)
            return {"items": [a.model_dump(mode="json") for a in out]}
        except KeyError:
            raise HTTPException(404, "character not found")
        except Exception as e:
            raise HTTPException(502, f"image generation failed: {e}")

    @api.post("/characters/{cid}/standard-views")
    async def character_standard_views(cid: str, data: dict):
        """选定主图后二次确认的标准多视图批量生成（FR-087，前端必须显式确认）。"""
        try:
            out = await char_assets.generate_standard_views(cid, data["front_asset_id"])
            return {"items": [a.model_dump(mode="json") for a in out]}
        except KeyError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(502, f"standard views failed: {e}")

    @api.post("/characters/{cid}/edit-image")
    async def character_edit_image(cid: str, data: dict):
        """非破坏式 Edit：换装/背景/表情/姿势/视角/自由编辑 → 新 Candidate（FR-086/088）。"""
        try:
            out = await char_assets.edit_image(
                cid, data["source_asset_id"], data["instruction"],
                role=data.get("role", "derived"),
                outfit_id=data.get("outfit_id"))
            return {"items": [a.model_dump(mode="json") for a in out]}
        except KeyError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(502, f"image edit failed: {e}")

    @api.get("/characters/{cid}/character-assets")
    async def character_asset_list(cid: str, status: str = ""):
        items = await char_assets.list_assets(cid, status or None)
        return {"items": [a.model_dump(mode="json") for a in items]}

    @api.patch("/character-assets/{aid}")
    async def character_asset_status(aid: str, data: dict):
        """资产状态流转（ARCHIVED 归档等；CANONICAL 提升请走 approve 保证同 role 唯一）。"""
        try:
            st = CharacterAssetStatus(data["status"])
        except (KeyError, ValueError):
            raise HTTPException(400, "bad status")
        try:
            a = await char_assets.set_asset_status(aid, st)
            return a.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "asset not found")

    @api.post("/characters/{cid}/assets/{aid}/approve")
    async def character_asset_approve(cid: str, aid: str):
        """提升为 Canonical（同 role 旧的归档）；front 提升属 IDENTITY 变更。"""
        try:
            a = await char_assets.approve_canonical(aid)
            return a.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "asset not found")

    @api.get("/characters/{cid}/versions")
    async def character_versions(cid: str):
        items = await char_assets.list_versions(cid)
        return {"items": [v.model_dump(mode="json") for v in items]}

    @api.get("/characters/{cid}/outfits")
    async def character_outfits(cid: str):
        try:
            return {"items": [o.model_dump(mode="json") for o in await char_assets.list_outfits(cid)]}
        except KeyError:
            raise HTTPException(404, "character not found")

    @api.post("/characters/{cid}/outfits")
    async def character_outfit_create(cid: str, data: dict):
        try:
            outfit = await char_assets.add_outfit(cid, str(data.get("name", "新造型")),
                                                  str(data.get("description", "")))
            return outfit.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "character not found")

    @api.get("/characters/{cid}/versions/diff")
    async def character_version_diff(cid: str, from_v: int, to_v: int):
        try:
            d = await char_assets.diff_versions(cid, from_v, to_v)
            return d.model_dump(mode="json")
        except KeyError as e:
            raise HTTPException(404, str(e))

    @api.post("/scenarios/{sver}/character-snapshots/{cid}")
    async def scenario_char_snapshot(sver: str, cid: str):
        """Scenario 绑定角色版本快照（FR-091/Q86）。"""
        try:
            s = await char_assets.snapshot_for_scenario(sver, cid)
            return s.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "character not found")

    @api.get("/scenarios/{sver}/character-snapshots")
    async def scenario_char_snapshots(sver: str):
        items = await char_assets.list_snapshots(sver)
        return {"items": [s.model_dump(mode="json") for s in items]}

    @api.post("/character-snapshots/{snap}/override")
    async def snapshot_override(snap: str, data: dict):
        """仅本故事修改（Q103 Local Override）。"""
        try:
            s = await char_assets.apply_local_override(snap, data)
            return s.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "snapshot not found")

    @api.post("/character-snapshots/{snap}/promote")
    async def snapshot_promote(snap: str):
        """Local Override 人工升为新全局版本（Q104）。"""
        try:
            v = await char_assets.promote_override_to_global(snap)
            return v.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "snapshot not found")
        except RuntimeError as e:
            raise HTTPException(400, str(e))

    @api.post("/character-snapshots/{snap}/resolve-references")
    async def snapshot_resolve(snap: str, data: dict):
        """Production Reference Resolver：选 2-4 张角色图（FR-093，可审计）。"""
        try:
            sel = await char_assets.resolve_references(
                snap, data.get("scene_or_shot_id", "scene"),
                provider_limits=data.get("provider_limits"),
                developer_override=data.get("developer_override"))
            return sel.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "snapshot not found")

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

    @api.patch("/scenarios/{sid}/assets/{aid}")
    async def patch_asset(sid: str, aid: str, req: Request):
        """G20：行内编辑素材元数据（role/entity/binding/authorized/canonical/trim/用途标记）。"""
        body = await req.json()
        allowed = {"role", "entity", "binding", "authorized", "canonical",
                   "trim_start", "trim_end", "duration", "source"}
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(AssetRow, aid)
                if row is None or row.scenario_id != sid:
                    raise HTTPException(404, "asset not found")
                data = dict(row.data)
                for k in allowed:
                    if k in body:
                        data[k] = body[k]
                row.data = data
        await engine.refresh_assets(sid)
        return data

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

        async def _watch() -> None:
            """推进 standalone job 状态到 READY/FAILED 并回写 JobRow（G23 收口）。"""
            import time
            from ..db_models import JobRow
            for _ in range(240):
                await asyncio.sleep(2)
                try:
                    result = await provider.status(handle)
                except Exception as exc:          # noqa: BLE001
                    job.status = JobStatus.FAILED
                    job.error = str(exc)
                    job.finished_at = int(time.time() * 1000)
                    break
                if result.status == "READY":
                    job.status = JobStatus.READY
                    job.output = {"handle": handle.provider_job_id,
                                  "clips": (result.raw or {}).get("clips", [])}
                    job.finished_at = int(time.time() * 1000)
                    break
                if result.status == "FAILED":
                    job.status = JobStatus.FAILED
                    job.error = result.error
                    job.finished_at = int(time.time() * 1000)
                    break
            else:
                job.status = JobStatus.FAILED
                job.error = "status poll timeout"
                job.finished_at = int(time.time() * 1000)
            async with SessionLocal() as db:
                async with db.begin():
                    row = await db.get(JobRow, job.id)
                    if row:
                        row.status = job.status.value
                        row.data = job.model_dump(mode="json")

        asyncio.create_task(_watch())
        return job.model_dump(mode="json")

    @api.get("/dev/jobs")
    async def dev_jobs(limit: int = 50):
        """G23：生成任务列表（Job ID/Provider/状态/起止/output/error）。"""
        from ..db_models import JobRow
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(JobRow).order_by(JobRow.started_at.desc()).limit(limit)
            )).scalars().all()
        return {"items": [r.data for r in rows]}

    # ---------------- Skills / Feedback ----------------
    @api.get("/skills")
    async def list_skills():
        return skills_registry()

    @api.get("/skills/{skill_id}/calls")
    async def skill_calls(skill_id: str, limit: int = 5):
        """G24：Skill 调用审计——最近 N 次调用 span（含禁用阻塞记录）。

        DB 持久化的 span 优先；无记录时回落到进程内 recent（重启后丢失属预期）。
        """
        async with SessionLocal() as db:
            spans = await tracer.spans_for_skill(db, skill_id, limit)
        if not spans:
            spans = [s for s in reversed(tracer.recent)
                     if s.skill_id == skill_id or s.name.startswith(skill_id)][:limit]
        return {"items": [s.model_dump(mode="json") for s in spans]}

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

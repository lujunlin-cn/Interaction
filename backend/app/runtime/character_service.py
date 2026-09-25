"""v0.6 Character Asset System 服务层（FR-083~097）。

职责：
- GlobalCharacter CRUD/搜索（继承原 CharacterService）
- AI 建角色（nano-banana-2 → 2 张 Candidate）
- 选主图 → 二次确认标准多视图（front/3⁄4/side/full_front/full_side）
- 非破坏式 Edit（新 Candidate，不覆盖 source）
- CharacterVersion（change_type 区分）+ 资产生命周期
- ScenarioCharacterSnapshot + Local Override + 升级 diff
- Production Reference Resolver（每 scene 选 2-4 张，可审计）
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import select

from ..db import SessionLocal
from ..db_models import (AssetRow, CharacterAssetRow, CharacterVersionRow,
                         GlobalCharacterRow, ScenarioCharacterSnapshotRow)
from ..domain.ids import uid
from ..domain.schemas import (CharacterAsset, CharacterAssetStatus,
                              CharacterOutfit, CharacterReferenceSelection,
                              CharacterVersion, CharacterVersionDiff,
                              ScenarioCharacterSnapshot, now_ms)
from ..providers.router import ProviderRouter
from ..runtime.tracer import tracer

# 标准多视图的 role 集合（FR-087）：主图 front 之外的可选批量生成视图
STANDARD_VIEW_ROLES = ["three_quarter", "side", "full_front", "full_side"]
CANONICAL_IMAGE_ROLES = ["front"] + STANDARD_VIEW_ROLES

# 变更类型（Q84）：影响 Snapshot/Production 追踪粒度
CHANGE_IDENTITY = "IDENTITY"
CHANGE_APPEARANCE = "APPEARANCE"
CHANGE_METADATA = "METADATA"
CHANGE_ASSET = "ASSET_ADDITION"
CHANGE_VOICE = "VOICE"


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


class CharacterAssetService:
    """v0.6 角色资产/版本/快照/参考解析。与 GlobalCharacter 平表共存：
    GlobalCharacterRow.data 仍存基础字段 + ref_* 槽位（向后兼容）；
    CharacterAssetRow/VersionRow/SnapshotRow 承载 v0.6 结构。"""

    def __init__(self, router: ProviderRouter):
        self.router = router

    # ------------------------------------------------------------------
    # 基础读取
    async def get_character(self, character_id: str) -> Optional[dict]:
        async with SessionLocal() as db:
            row = await db.get(GlobalCharacterRow, character_id)
            if row is None:
                return None
            data = dict(row.data)
            data["version"] = row.version
            return data

    async def _row(self, db, character_id: str) -> GlobalCharacterRow:
        row = await db.get(GlobalCharacterRow, character_id)
        if row is None:
            raise KeyError(character_id)
        return row

    # ------------------------------------------------------------------
    # CharacterAsset 生命周期（FR-095）
    async def add_asset(self, character_id: str, role: str, url: str,
                        status: CharacterAssetStatus = CharacterAssetStatus.CANDIDATE,
                        source_refs: Optional[list[str]] = None,
                        job_id: Optional[str] = None,
                        outfit_id: Optional[str] = None,
                        provenance: Optional[dict] = None) -> CharacterAsset:
        asset = CharacterAsset(
            id=uid("ca"), character_id=character_id, role=role, status=status,
            url=url, source_asset_refs=source_refs or [],
            generation_job_id=job_id, outfit_id=outfit_id,
            provenance=provenance or {})
        async with SessionLocal() as db:
            async with db.begin():
                db.add(CharacterAssetRow(
                    id=asset.id, character_id=character_id,
                    status=asset.status.value, role=role,
                    data=asset.model_dump(mode="json"),
                    created_at=asset.created_at))
        return asset

    async def list_assets(self, character_id: str,
                          status: Optional[str] = None) -> list[CharacterAsset]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(CharacterAssetRow)
                .where(CharacterAssetRow.character_id == character_id)
                .order_by(CharacterAssetRow.created_at))).scalars().all()
        out = [CharacterAsset(**r.data) for r in rows]
        if status:
            out = [a for a in out if a.status.value == status]
        return out

    async def set_asset_status(self, asset_id: str,
                               status: CharacterAssetStatus) -> CharacterAsset:
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(CharacterAssetRow, asset_id)
                if row is None:
                    raise KeyError(asset_id)
                row.status = status.value
                data = dict(row.data)
                data["status"] = status.value
                row.data = data          # JSON 列：重赋值保证 flag_modified
                return CharacterAsset(**row.data)

    async def approve_canonical(self, asset_id: str) -> CharacterAsset:
        """把某 Candidate 提升为 Canonical：同 role 的旧 Canonical 归档（FR-095）。"""
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(CharacterAssetRow, asset_id)
                if row is None:
                    raise KeyError(asset_id)
                asset = CharacterAsset(**row.data)
                # 同 role 旧 Canonical 归档
                rows = (await db.execute(
                    select(CharacterAssetRow).where(
                        CharacterAssetRow.character_id == asset.character_id,
                        CharacterAssetRow.role == asset.role,
                        CharacterAssetRow.status == CharacterAssetStatus.CANONICAL.value)
                )).scalars().all()
                for old in rows:
                    old.status = CharacterAssetStatus.ARCHIVED.value
                    od = dict(old.data)
                    od["status"] = CharacterAssetStatus.ARCHIVED.value
                    old.data = od               # JSON 列重赋值 → flag_modified
                row.status = CharacterAssetStatus.CANONICAL.value
                nd = dict(row.data)
                nd["status"] = CharacterAssetStatus.CANONICAL.value
                row.data = nd
                asset.status = CharacterAssetStatus.CANONICAL
        # canonical 变化 → 新版本（ASSET_ADDITION / IDENTITY 若主图）
        change = CHANGE_IDENTITY if asset.role == "front" else CHANGE_ASSET
        await self._new_version(asset.character_id, change,
                                breaking=(asset.role == "front"))
        return asset

    # ------------------------------------------------------------------
    # AI 生图（FR-085）：nano-banana-2 → 2 张 Candidate
    async def ai_generate_candidates(self, character_id: str,
                                     extra_prompt: str = "",
                                     num_images: int = 2) -> list[CharacterAsset]:
        ch = await self.get_character(character_id)
        if ch is None:
            raise KeyError(character_id)
        prompt = self._build_portrait_prompt(ch, extra_prompt)
        provider = self.router.registry.get("nano_banana_2")
        if provider is None:
            raise RuntimeError("image provider not registered")
        job_id = uid("job")
        result = await provider.generate(
            {"prompt": prompt, "num_images": num_images,
             "resolution": settings.image_generation_resolution,
             "aspect_ratio": settings.generation_aspect_ratio})
        out: list[CharacterAsset] = []
        for img in result.get("images", []):
            url = img.get("url", "")
            if not url:
                continue
            out.append(await self.add_asset(
                character_id, role="front", url=url,
                status=CharacterAssetStatus.CANDIDATE, job_id=job_id,
                provenance={"provider": getattr(provider, "name", "nano_banana_2"), "model": result.get("model", ""),
                            "resolution": result.get("resolution", settings.image_generation_resolution),
                            "aspect_ratio": result.get("aspect_ratio", settings.generation_aspect_ratio),
                            "prompt_hash": _prompt_hash(prompt),
                            "capability": "IMAGE_GENERATION"}))
        await tracer.emit("character.image_generate", "success",
                          input_={"character": character_id, "num": num_images},
                          output={"candidates": len(out)},
                          provider="nano_banana_2")
        return out

    # ------------------------------------------------------------------
    # 标准多视图（FR-087）：选定 front 后，二次确认批量生成
    async def generate_standard_views(self, character_id: str,
                                      front_asset_id: str) -> list[CharacterAsset]:
        ch = await self.get_character(character_id)
        if ch is None:
            raise KeyError(character_id)
        front = await self._get_asset(front_asset_id)
        provider = self.router.registry.get("nano_banana_2")
        if provider is None:
            raise RuntimeError("image provider not registered")
        job_id = uid("job")
        view_prompts = {
            "three_quarter": "three-quarter view portrait",
            "side": "side profile view portrait",
            "full_front": "full body front view",
            "full_side": "full body side view",
        }
        async def _one(role: str, desc: str) -> list[CharacterAsset]:
            prompt = (f"{desc} of the same character, consistent identity, "
                      f"same face, same hairstyle, same outfit. "
                      f"{self._build_portrait_prompt(ch, '')[:200]}")
            result = await provider.edit(
                {"prompt": prompt, "image_urls": [front.url],
                 "resolution": settings.image_generation_resolution,
                 "aspect_ratio": settings.generation_aspect_ratio})
            made: list[CharacterAsset] = []
            for img in result.get("images", [])[:1]:
                if not img.get("url"):
                    continue
                made.append(await self.add_asset(
                    character_id, role=role, url=img["url"],
                    status=CharacterAssetStatus.CANDIDATE, job_id=job_id,
                    source_refs=[front_asset_id],
                    provenance={"provider": getattr(provider, "name", "nano_banana_2"),
                                "model": result.get("model", ""),
                                "resolution": result.get("resolution", settings.image_generation_resolution),
                                "aspect_ratio": result.get("aspect_ratio", settings.generation_aspect_ratio),
                                "prompt_hash": _prompt_hash(prompt),
                                "capability": "IMAGE_EDIT",
                                "standard_view": role}))
            return made

        # 4 视图并行（fal queue 单任务可能 >180s，串行会成倍放大超时面）
        import asyncio
        batches = await asyncio.gather(
            *[_one(r, d) for r, d in view_prompts.items()],
            return_exceptions=True)
        out: list[CharacterAsset] = []
        failed: list[str] = []
        for b in batches:
            if isinstance(b, Exception):
                failed.append(str(b)[:120])
            else:
                out.extend(b)
        if not out and failed:
            raise RuntimeError(f"all views failed: {failed[0]}")
        await tracer.emit("character.standard_views", "success",
                          input_={"character": character_id},
                          output={"views": len(out)}, provider="nano_banana_2")
        return out

    # ------------------------------------------------------------------
    # 非破坏式 Edit（FR-086）：换装/背景/表情/姿势/视角/自由编辑 → 新 Candidate
    async def edit_image(self, character_id: str, source_asset_id: str,
                         instruction: str, role: str = "derived",
                         outfit_id: Optional[str] = None) -> list[CharacterAsset]:
        src = await self._get_asset(source_asset_id)
        provider = self.router.registry.get("nano_banana_2")
        if provider is None:
            raise RuntimeError("image provider not registered")
        # 身份保护默认注入（FR-088：Edit 默认锁脸/年龄/发型/基本体型）
        guard = ("Keep the same face, age, hairstyle and basic body type. "
                 "Only change what the instruction says. Instruction: ")
        prompt = guard + instruction
        job_id = uid("job")
        result = await provider.edit({"prompt": prompt, "image_urls": [src.url],
                                      "resolution": settings.image_generation_resolution,
                                      "aspect_ratio": settings.generation_aspect_ratio})
        out: list[CharacterAsset] = []
        for img in result.get("images", []):
            if not img.get("url"):
                continue
            out.append(await self.add_asset(
                character_id, role=role, url=img["url"],
                status=CharacterAssetStatus.CANDIDATE, job_id=job_id,
                source_refs=[source_asset_id], outfit_id=outfit_id,
                provenance={"provider": getattr(provider, "name", "nano_banana_2"),
                            "model": result.get("model", ""),
                            "resolution": result.get("resolution", settings.image_generation_resolution),
                            "aspect_ratio": result.get("aspect_ratio", settings.generation_aspect_ratio),
                            "prompt_hash": _prompt_hash(prompt),
                            "capability": "IMAGE_EDIT",
                            "instruction": instruction[:200],
                            "identity_guard": True}))
        await tracer.emit("character.image_edit", "success",
                          input_={"character": character_id,
                                  "instruction": instruction[:120]},
                          output={"candidates": len(out)},
                          provider="nano_banana_2")
        return out

    async def _get_asset(self, asset_id: str) -> CharacterAsset:
        async with SessionLocal() as db:
            row = await db.get(CharacterAssetRow, asset_id)
            if row is None:
                raise KeyError(asset_id)
            return CharacterAsset(**row.data)

    def _build_portrait_prompt(self, ch: dict, extra: str) -> str:
        parts = ["Character portrait, neutral background, high quality."]
        if ch.get("appearance"):
            parts.append(f"Appearance: {ch['appearance']}")
        if ch.get("bio"):
            parts.append(f"Character: {ch['bio'][:200]}")
        if ch.get("personality"):
            parts.append(f"Personality reflected in expression: {ch['personality'][:120]}")
        if extra:
            parts.append(extra)
        return " ".join(parts)

    # ------------------------------------------------------------------
    # CharacterVersion（FR-090 / Q84）
    async def _new_version(self, character_id: str, change_type: str,
                           breaking: bool = False) -> CharacterVersion:
        async with SessionLocal() as db:
            async with db.begin():
                row = await self._row(db, character_id)
                data = dict(row.data)
                # 当前最新版本号
                last = (await db.execute(
                    select(CharacterVersionRow)
                    .where(CharacterVersionRow.character_id == character_id)
                    .order_by(CharacterVersionRow.version.desc()).limit(1))
                ).scalars().first()
                n = (last.version + 1) if last else 1
                row.version = n
                data["version"] = n
                canonical = await self._canonical_refs(db, character_id)
            # Standard Reference Pack slots are first-class versioned refs even
            # when they point at uploaded Asset rows rather than CharacterAsset
            # rows.  Keeping them in the version snapshot makes a pinned
            # Scenario Character reproducible after the library advances.
                for slot, key in {
                "front": "ref_front_asset",
                "three_quarter": "ref_three_quarter_asset",
                "side": "ref_side_asset",
                "full_front": "ref_full_front_asset",
                "full_side": "ref_full_side_asset",
                "back": "ref_back_asset",
            }.items():
                    if data.get(key):
                        canonical.setdefault(slot, data[key])
                ver = CharacterVersion(
                    id=uid("cv"), character_id=character_id, version=n,
                    change_type=change_type,
                    identity_spec={"name": data.get("name", ""),
                                   "bio": data.get("bio", ""),
                                   "personality": data.get("personality", ""),
                                   "appearance": data.get("appearance", ""),
                                   "tags": data.get("tags", []),
                                   **{k: data.get(k, "") for k in ("default_desire", "default_fear", "default_secrets", "default_knowledge", "default_relationship")}},
                    canonical_asset_refs=canonical,
                    outfits=[CharacterOutfit(**o) for o in data.get("outfits", [])],
                    pose_refs=list(data.get("ref_pose_assets", [])),
                    motion_refs=list(data.get("ref_motion_assets", [])) or ([data["ref_motion_asset"]] if data.get("ref_motion_asset") else []),
                    canonical_voice_ref=data.get("ref_voice_asset"),
                    alternate_voice_refs=list(data.get("alternate_voice_assets", [])),
                    source_version_id=last.id if last else None,
                    breaking_identity_change=breaking)
                db.add(CharacterVersionRow(
                    id=ver.id, character_id=character_id, version=n,
                    change_type=change_type,
                    data=ver.model_dump(mode="json"), created_at=ver.created_at))
                data["current_version_id"] = ver.id
                row.data = data
                row.updated_at = now_ms()
        return ver

    async def _canonical_refs(self, db, character_id: str) -> dict[str, Any]:
        rows = (await db.execute(
            select(CharacterAssetRow).where(
                CharacterAssetRow.character_id == character_id,
                CharacterAssetRow.status == CharacterAssetStatus.CANONICAL.value)
        )).scalars().all()
        return {r.role: r.id for r in rows}

    async def list_versions(self, character_id: str) -> list[CharacterVersion]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(CharacterVersionRow)
                .where(CharacterVersionRow.character_id == character_id)
                .order_by(CharacterVersionRow.version.desc()))).scalars().all()
        return [CharacterVersion(**r.data) for r in rows]

    async def list_outfits(self, character_id: str) -> list[CharacterOutfit]:
        ch = await self.get_character(character_id)
        if ch is None:
            raise KeyError(character_id)
        return [CharacterOutfit(**o) for o in ch.get("outfits", [])]

    async def add_outfit(self, character_id: str, name: str,
                         description: str = "") -> CharacterOutfit:
        async with SessionLocal() as db:
            async with db.begin():
                row = await self._row(db, character_id)
                data = dict(row.data)
                outfit = CharacterOutfit(id=uid("outfit"), name=name,
                                         description=description,
                                         is_default=not bool(data.get("outfits")))
                data["outfits"] = [*data.get("outfits", []), outfit.model_dump(mode="json")]
                row.data = data
                row.version += 1
                row.updated_at = now_ms()
        await self._new_version(character_id, CHANGE_METADATA)
        return outfit

    async def diff_versions(self, character_id: str,
                            from_v: int, to_v: int) -> CharacterVersionDiff:
        versions = {v.version: v for v in await self.list_versions(character_id)}
        a, b = versions.get(from_v), versions.get(to_v)
        if a is None or b is None:
            raise KeyError(f"version {from_v} or {to_v} not found")
        field_diffs: dict[str, dict] = {}
        for k in set(a.identity_spec) | set(b.identity_spec):
            if a.identity_spec.get(k) != b.identity_spec.get(k):
                field_diffs[k] = {"before": a.identity_spec.get(k),
                                  "after": b.identity_spec.get(k)}
        asset_diffs: dict[str, dict] = {}
        for k in set(a.canonical_asset_refs) | set(b.canonical_asset_refs):
            if a.canonical_asset_refs.get(k) != b.canonical_asset_refs.get(k):
                asset_diffs[k] = {"before": a.canonical_asset_refs.get(k),
                                  "after": b.canonical_asset_refs.get(k)}
        return CharacterVersionDiff(
            from_version=from_v, to_version=to_v,
            change_types=[b.change_type], field_diffs=field_diffs,
            asset_diffs=asset_diffs,
            breaking_identity_change=b.breaking_identity_change)

    # ------------------------------------------------------------------
    # Scenario Snapshot（FR-091 / Q86）
    async def snapshot_for_scenario(self, scenario_version_id: str,
                                    character_id: str, version: int | None = None,
                                    overrides: dict | None = None) -> ScenarioCharacterSnapshot:
        ch = await self.get_character(character_id)
        if ch is None:
            raise KeyError(character_id)
        ver_id = ch.get("current_version_id")
        ver: Optional[CharacterVersion] = None
        if version is not None:
            ver = next((v for v in await self.list_versions(character_id) if v.version == version), None)
            if ver is None:
                raise KeyError(f"character version {version}")
        elif ver_id:
            async with SessionLocal() as db:
                r = await db.get(CharacterVersionRow, ver_id)
                if r:
                    ver = CharacterVersion(**r.data)
        if ver is None:
            ver = await self._new_version(character_id, CHANGE_METADATA)
        snap = ScenarioCharacterSnapshot(
            id=uid("snap"), scenario_version_id=scenario_version_id,
            global_character_id=character_id,
            character_version_id=ver.id, character_version=ver.version,
            frozen_identity=ver.identity_spec, local_overrides=overrides or {},
            frozen_asset_refs={k: v for k, v in ver.canonical_asset_refs.items()})
        async with SessionLocal() as db:
            async with db.begin():
                db.add(ScenarioCharacterSnapshotRow(
                    id=snap.id, scenario_version_id=scenario_version_id,
                    global_character_id=character_id,
                    character_version_id=ver.id,
                    data=snap.model_dump(mode="json"),
                    created_at=snap.created_at))
        return snap

    async def list_snapshots(self, scenario_version_id: str
                             ) -> list[ScenarioCharacterSnapshot]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(ScenarioCharacterSnapshotRow).where(
                    ScenarioCharacterSnapshotRow.scenario_version_id ==
                    scenario_version_id))).scalars().all()
        return [ScenarioCharacterSnapshot(**r.data) for r in rows]

    async def apply_local_override(self, snapshot_id: str,
                                   overrides: dict) -> ScenarioCharacterSnapshot:
        """仅本故事修改（Q103）：写 local_overrides，不污染 Global。"""
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(ScenarioCharacterSnapshotRow, snapshot_id)
                if row is None:
                    raise KeyError(snapshot_id)
                data = dict(row.data)
                data["local_overrides"] = {
                    **data.get("local_overrides", {}), **overrides}
                row.data = data          # 重赋值触发 flag_modified（JSON 列就地改不可见）
                return ScenarioCharacterSnapshot(**row.data)

    async def promote_override_to_global(self, snapshot_id: str) -> CharacterVersion:
        """Q104：Scenario Local Override 人工保存为新全局版本。"""
        async with SessionLocal() as db:
            row = await db.get(ScenarioCharacterSnapshotRow, snapshot_id)
            if row is None:
                raise KeyError(snapshot_id)
            snap = ScenarioCharacterSnapshot(**row.data)
        if not snap.local_overrides:
            raise RuntimeError("no local_overrides to promote")
        async with SessionLocal() as db:
            async with db.begin():
                crow = await self._row(db, snap.global_character_id)
                data = dict(crow.data)
                for k, v in snap.local_overrides.items():
                    if k in ("name", "bio", "personality", "appearance", "tags"):
                        data[k] = v
                    elif k in ("desire", "fear", "secrets", "knowledge", "relationship"):
                        data["default_" + k] = v
                    elif k == "visual_state":
                        data["appearance"] = v
                crow.data = data
                crow.version += 1
                crow.updated_at = now_ms()
        return await self._new_version(snap.global_character_id, CHANGE_METADATA)

    # ------------------------------------------------------------------
    # Production Reference Resolver（FR-093 / Q89-91）
    async def resolve_references(self, snapshot_id: str, scene_or_shot_id: str,
                                 provider_limits: Optional[dict] = None,
                                 developer_override: Optional[dict] = None
                                 ) -> CharacterReferenceSelection:
        """按 Scene 从 Snapshot 选 2-4 张角色图 + voice/motion；输出可审计。"""
        async with SessionLocal() as db:
            row = await db.get(ScenarioCharacterSnapshotRow, snapshot_id)
            if row is None:
                raise KeyError(snapshot_id)
            snap = ScenarioCharacterSnapshot(**row.data)
        limits = provider_limits or {"image": 9, "audio": 3, "video": 3}
        # Developer 覆盖优先
        if developer_override and developer_override.get("image_refs"):
            return CharacterReferenceSelection(
                scene_or_shot_id=scene_or_shot_id,
                character_snapshot_id=snapshot_id,
                selected_image_refs=list(developer_override["image_refs"])[:4],
                voice_ref=developer_override.get("voice_ref"),
                motion_ref=developer_override.get("motion_ref"),
                selection_reason="developer_override",
                developer_override=True,
                provider_limits_snapshot=limits)
        # 从 frozen_asset_refs 按标准视图优先级选（front > three_quarter > side > full_*）
        frozen = snap.frozen_asset_refs
        order = ["front", "three_quarter", "side", "full_front", "full_side"]
        picked = [frozen[r] for r in order if frozen.get(r)]
        max_img = min(4, int(limits.get("image", 4)))
        selected = picked[:max_img]
        reason = (f"standard view priority {order}; picked {len(selected)}/"
                  f"{len(picked)} within provider limit {max_img}")
        voice = snap.local_overrides.get("voice_ref") or \
            snap.frozen_asset_refs.get("voice")
        motion = snap.frozen_asset_refs.get("motion")
        sel = CharacterReferenceSelection(
            scene_or_shot_id=scene_or_shot_id,
            character_snapshot_id=snapshot_id,
            selected_image_refs=selected, voice_ref=voice, motion_ref=motion,
            selection_reason=reason, provider_limits_snapshot=limits)
        await tracer.emit("character.reference_resolve", "success",
                          input_={"snapshot": snapshot_id,
                                  "scene": scene_or_shot_id},
                          output={"images": len(selected),
                                  "voice": bool(voice), "motion": bool(motion)})
        return sel

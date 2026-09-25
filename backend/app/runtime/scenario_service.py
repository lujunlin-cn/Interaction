"""Scenario 服务：草稿 CRUD、Scenario Authoring Skill 起草/修改、发布为不可变版本。"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select

from ..db import SessionLocal
from ..db_models import CharacterAssetRow, CharacterVersionRow, GlobalCharacterRow, ScenarioRow, ScenarioVersionRow
from ..domain.ids import uid
from ..domain.schemas import ScenarioDraft, now_ms
from ..providers.router import ProviderRouter
from ..runtime.tracer import tracer
from .structured_output import decode_object


def _row_to_draft(row: ScenarioRow) -> ScenarioDraft:
    return ScenarioDraft(**row.draft)


class ScenarioService:
    def __init__(self, router: ProviderRouter):
        self.router = router

    async def list(self) -> list[ScenarioDraft]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(ScenarioRow).order_by(ScenarioRow.updated_at.desc()))).scalars().all()
            return [_row_to_draft(r) for r in rows]

    async def get(self, scenario_id: str) -> Optional[ScenarioDraft]:
        async with SessionLocal() as db:
            row = await db.get(ScenarioRow, scenario_id)
            return _row_to_draft(row) if row else None

    async def save_draft(self, draft: ScenarioDraft) -> ScenarioDraft:
        from ..domain.mechanic_spec import validate_mechanics
        draft.mechanics = validate_mechanics(draft.mechanics)
        draft.updated_at = now_ms()
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(ScenarioRow, draft.id)
                if row is None:
                    row = ScenarioRow(id=draft.id, status=draft.status,
                                      draft=draft.model_dump(mode="json"),
                                      updated_at=draft.updated_at)
                    db.add(row)
                else:
                    row.draft = draft.model_dump(mode="json")
                    row.status = draft.status
                    row.updated_at = draft.updated_at
        return draft

    async def create_empty(self, title: str = "未命名 Scenario") -> ScenarioDraft:
        from ..domain.mechanic_spec import validate_mechanics, CONFIGS
        draft = ScenarioDraft(id=uid("scn"), title=title, mechanics=validate_mechanics({k: {"enabled": False} for k in CONFIGS}))
        await self.save_draft(draft)
        return draft

    async def create_from_idea(self, idea: str) -> ScenarioDraft:
        """Model proposes a draft; schema/skill validation precedes persistence."""
        from ..domain.mechanic_spec import validate_mechanics
        prompt = (
            "为用户生成完整中文故事草案，只返回 JSON，每个文本字段尽量不超过60字。description 是面向玩家的公开简介，不能泄露 truth_model/secrets 中的隐藏真相。"
            "字段：title,description,genre,tone,play_style,player_character(角色ID),"
            "world:{rules,lore,locations(每行id｜名称),constraints},"
            "drama:{core_question,central_conflict,truth_model(每行fact_id：真相),secrets,misbeliefs,"
            "pressures(名称｜来源｜故事时间推进),anchors,ending_families(id｜描述),foreshadows,"
            "forbidden_outcomes,timed_interactions},"
            "characters:[{id,identity,personality,desire,fear,secrets,knowledge,relationship,visual_state}]。"
            "角色至少包含player和一位具名NPC，勿照搬其他故事。"
            "未明确玩法时 mechanics 留空对象 {}。只允许 relationship/clue-system/inventory/qte，"
            "如需启用则值为 {enabled:true,config:{}}，绝不创造其他 Skill。"
            "保留用户已经明确的真相、冲突、压力与限制，不擅自反转。所有 world/drama 子字段都是字符串，不是数组。pressure 的驱动只能是行动触发或故事时间推进。timed_interactions 默认为空字符串，故事时间的期限不是现实倒计时；如果启用 qte 才使用 id｜qte｜秒｜超时结果。"
        )
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": f"idea: {idea}"}]
        for attempt in range(2):
            _, rec, resp = await self.router.call_text("authoring", messages=messages,
                output_contract={"purpose": "authoring_draft"}, budget={"max_tokens": 4096, "reasoning_effort": "low"})
            try:
                content = decode_object(resp.content)
                # Lossless representation repair: string arrays become newline text.
                for section in (content.get("world"), content.get("drama"), *(content.get("characters") or [])):
                    if isinstance(section, dict):
                        for key, value in section.items():
                            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                                section[key] = "\n".join(value)
                keys = ("title", "description", "genre", "tone", "play_style", "player_character", "world", "drama", "characters", "mechanics", "theme")
                draft = ScenarioDraft.model_validate({**{k: v for k, v in content.items() if k in keys}, "id": uid("scn"), "authoring_intent": idea})
                if draft.characters and draft.player_character not in {c.id for c in draft.characters}:
                    draft.player_character = draft.characters[0].id
                from ..domain.mechanic_spec import CONFIGS
                draft.mechanics = validate_mechanics({**{k: {"enabled": False} for k in CONFIGS}, **draft.mechanics})
                for line in draft.drama.timed_interactions.splitlines():
                    parts = line.split("｜")
                    if line.strip() and (len(parts) < 4 or parts[1] not in ("qte", "urgent_dialogue") or not parts[2].isdigit()):
                        raise ValueError("timed_interactions 必须为空字符串，或 id｜qte｜秒｜超时结果。普通故事时间期限不是现实倒计时。")
                if not (draft.description.strip() and draft.world.rules.strip() and draft.world.locations.strip()
                        and draft.characters and draft.drama.core_question.strip() and draft.drama.truth_model.strip()
                        and draft.drama.pressures.strip() and draft.drama.ending_families.strip()):
                    raise ValueError("草案缺少必要的故事描述、世界、角色、核心问题、真相、压力或结局。不得返回空对象。")
                break
            except (ValueError, TypeError, AttributeError) as error:
                await tracer.emit("authoring.draft_schema", "failed", input_={"idea": idea},
                    output={"raw_output": resp.content, "error": str(error), "attempt": attempt + 1},
                    provider=rec.selected or "", model=resp.model)
                if attempt:
                    raise
                messages += [{"role": "assistant", "content": resp.content}, {"role": "user", "content": "仅修复格式并保留故事语义。校验错误：" + str(error)}]
        await tracer.emit("authoring.draft", "success", input_={"idea": idea},
                          output={"scenario_id": draft.id, "title": draft.title, "raw_output": resp.content},
                          provider=rec.selected or "", model=resp.model, duration_ms=resp.latency_ms,
                          skill_id="scenario-authoring", skill_version="1.0.0")
        await self.save_draft(draft)
        return draft

    # G16：指令补丁允许写入的路径前缀（locks 与任意路径拒绝）
    _PATCHABLE_PREFIXES = ("description", "title", "genre", "tone", "play_style",
                           "drama.", "world.", "theme.", "characters.",
                           "mechanics.")

    def _apply_typed_patch(self, draft: ScenarioDraft, patches: list[dict],
                           source: str) -> list[dict]:
        """按 {path,before,after,reason} 应用补丁，写入结构化 changes（G16/G17）。

        - path 只接受白名单前缀；characters[i].field 走专用段
        - locks 内字段拒绝
        - before 不一致时按 after 直接覆盖并记录 conflict
        """
        applied: list[dict] = []
        for p in patches:
            path = str(p.get("path", ""))
            after = p.get("after")
            if not path or any(path == lock or path.startswith(lock + ".")
                               or path.startswith(lock + "[") for lock in draft.locks):
                continue
            if not (path in ("description", "title", "genre", "tone", "play_style") or path.startswith(("drama.", "world.", "theme.", "characters.", "mechanics.", "characters["))):
                continue
            before = self._get_path(draft, path)
            ok = self._set_path(draft, path, after)
            if not ok:
                continue
            entry = {"path": path, "before": before, "after": after,
                     "reason": p.get("reason", ""), "source": source,
                     "at": now_ms()}
            draft.changes.append(entry)
            applied.append(entry)
        return applied

    @staticmethod
    def _get_path(draft: ScenarioDraft, path: str):
        try:
            obj = draft.model_dump(mode="json")
            for part in ScenarioService._split_path(path):
                obj = obj[part]
            return obj
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    @staticmethod
    def _split_path(path: str) -> list:
        import re
        if not re.fullmatch(r"[a-z_][a-z_0-9-]*(?:\[\d+\])?(?:\.[a-z_][a-z_0-9-]*(?:\[\d+\])?)*", path):
            raise ValueError("无效字段路径")
        return [int(p) if p.isdigit() else p for p in re.findall(r"[a-z_][a-z_0-9-]*|\d+", path)]

    @staticmethod
    def validate_patch(draft, path, value):
        data = draft.model_dump(mode="json")
        parts = ScenarioService._split_path(path)
        obj = data
        for part in parts[:-1]:
            obj = obj[part]
        if isinstance(obj, dict) and parts[-1] not in obj and parts[0] != "mechanics":
            raise ValueError("未知字段")
        obj[parts[-1]] = value
        candidate = ScenarioDraft.model_validate(data)
        if path == "drama.timed_interactions":
            for line in candidate.drama.timed_interactions.splitlines():
                parts = line.split("｜")
                if line.strip() and (len(parts) != 4 or parts[1] not in ("qte", "urgent_dialogue") or not parts[2].isdigit() or not 1 <= int(parts[2]) <= 120 or not parts[3].strip()):
                    raise ValueError("限时事件必须为 id｜qte 或 urgent_dialogue｜1至120秒｜明确超时结果。第二段必须是 qte 或 urgent_dialogue，不能用中文场景名。")
        from ..domain.mechanic_spec import validate_mechanics
        candidate.mechanics = validate_mechanics(candidate.mechanics)
        return candidate

    @staticmethod
    def _set_path(draft, path, value):
        try:
            candidate = ScenarioService.validate_patch(draft, path, value)
            root = ScenarioService._split_path(path)[0]
            setattr(draft, root, getattr(candidate, root))
            return True
        except (ValueError, KeyError, TypeError, IndexError):
            return False

    async def apply_instruction(self, scenario_id: str, instruction: str) -> ScenarioDraft:
        """Scenario Authoring Skill 修改路径：指令 → typed patches → 校验应用（G16）。"""
        draft = await self.get(scenario_id)
        if draft is None:
            raise KeyError(scenario_id)
        _, rec, resp = await self.router.call_text(
            "authoring",
            messages=[{"role": "system", "content": '输出 JSON {"patches":[{"path":"drama.core_question","after":"新内容","reason":"原因"}]}。只修改指令明确要求且未被 locks 锁定的字段。'}, {"role": "user", "content":
                       f"instruction: {instruction}\n"
                       f"draft_summary: {json.dumps(draft.model_dump(exclude={"changes", "creator_projection"}), ensure_ascii=False)}"}],
            output_contract={"purpose": "authoring_patch"}, budget={"max_tokens": 4096, "reasoning_effort": "low"})
        content = decode_object(resp.content)
        patches = content.get("patches")
        applied: list[dict] = []
        if isinstance(patches, list) and patches:
            applied = self._apply_typed_patch(draft, patches, source="instruct")
        if not applied:
            # 兼容旧 contract：after 只写 description
            after = content.get("after", "")
            if after and "description" not in draft.locks:
                entry = {"path": "description", "before": draft.description,
                         "after": after, "reason": instruction[:120],
                         "source": "instruct", "at": now_ms()}
                draft.description = after
                draft.changes.append(entry)
                applied.append(entry)
        await tracer.emit("authoring.patch", "success",
                          input_={"instruction": instruction[:120]},
                          output={"applied": len(applied)},
                          provider=rec.selected or "")
        await self.save_draft(draft)
        return draft

    # ---------------- G18：Publish Gate 服务端校验 ----------------
    def publish_checklist(self, draft: ScenarioDraft) -> list[dict]:
        """发布前 11 项检查；每项 {id, label, ok, detail}。"""
        checks: list[dict] = []
        def add(cid: str, label: str, ok: bool, detail: str = ""):
            checks.append({"id": cid, "label": label, "ok": bool(ok), "detail": detail})
        add("title", "标题与简介", bool(draft.title.strip() and draft.description.strip()),
            "标题与简介不能为空")
        add("world_rules", "世界规则", bool(draft.world.rules.strip()),
            "world.rules 不能为空")
        char_ids = {c.id for c in draft.characters}
        add("player_character", "玩家角色存在",
            draft.player_character in char_ids or not draft.characters,
            f"player_character={draft.player_character!r} 不在角色表")
        add("char_identity", "角色身份信息",
            all(c.identity.strip() for c in draft.characters) and bool(draft.characters),
            "每个角色需要 identity，且至少一名角色")
        add("core_question", "核心问题", bool(draft.drama.core_question.strip()),
            "drama.core_question 不能为空")
        add("truth_model", "真相模型", bool(draft.drama.truth_model.strip()),
            "drama.truth_model 不能为空")
        add("pressures", "压力线", bool(draft.drama.pressures.strip()),
            "drama.pressures 不能为空")
        add("ending_families", "结局族", bool(draft.drama.ending_families.strip()),
            "drama.ending_families 不能为空")
        # 限时互动声明格式：id｜kind｜秒｜fallback
        timed_ok, timed_detail = True, ""
        for line in draft.drama.timed_interactions.splitlines():
            if not line.strip():
                continue
            parts = [x.strip() for x in line.split("｜")]
            if len(parts) < 4 or parts[1] not in ("qte", "urgent_dialogue") \
                    or not parts[2].isdigit():
                timed_ok, timed_detail = False, f"格式错误：{line[:40]}"
                break
        add("timed", "限时互动声明", timed_ok, timed_detail)
        # 角色绑定全局角色需存在（快照检查在发布时无法查 DB，这里只查字段一致性）
        add("char_snapshot", "角色快照绑定",
            all((not c.global_character_id) or c.global_character_version
                for c in draft.characters),
            "绑定全局角色需记录版本号")
        # 纯文字角色是合法产品路径（Q94）。视觉资产缺失是警告，只有
        # 真正进入视频 Production 时才要求补图或选择文字呈现。
        add("char_assets", "角色视觉资产", True,
            "提示：存在无图片角色；进入视频制作时需要补充视觉身份或选择文字模式" if any(
                c.global_character_id for c in draft.characters) else "纯文字角色可正常发布")
        try:
            from ..domain.mechanic_spec import validate_mechanics
            validate_mechanics(draft.mechanics)
            mechanics_ok = True
        except ValueError:
            mechanics_ok = False
        add("mechanics", "玩法机制", mechanics_ok,
            "玩法机制配置格式无效" if not mechanics_ok else "")
        return checks

    async def publish(self, scenario_id: str, reviewed: bool = False) -> dict:
        """发布：Publish Gate 校验 + 生成不可变 ScenarioVersion（G18）。"""
        draft = await self.get(scenario_id)
        if draft is None:
            raise KeyError(scenario_id)
        checks = self.publish_checklist(draft)
        bound_ids = {c.global_character_id for c in draft.characters
                     if c.global_character_id}
        if bound_ids:
            async with SessionLocal() as db:
                rows = (await db.execute(
                    select(GlobalCharacterRow.id).where(
                        GlobalCharacterRow.id.in_(bound_ids)))).all()
            missing = bound_ids - {r[0] for r in rows}
            for check in checks:
                if check["id"] == "char_snapshot" and missing:
                    check["ok"] = False
                    check["detail"] = "无效全局角色引用：" + ", ".join(sorted(missing))
                if not missing:
                    async with SessionLocal() as db:
                        globals_ = (await db.execute(
                            select(GlobalCharacterRow).where(GlobalCharacterRow.id.in_(bound_ids))
                        )).scalars().all()
                        versions = (await db.execute(
                            select(CharacterVersionRow).where(CharacterVersionRow.character_id.in_(bound_ids))
                        )).scalars().all()
                        version_ids = {v.id for v in versions}
                        pinned_missing = [c.global_character_id for c in draft.characters if c.global_character_id and not any(v.character_id == c.global_character_id and v.version == c.global_character_version for v in versions)]
                        invalid_snapshot = [g.id for g in globals_ if not g.data.get("current_version_id")
                                            or g.data.get("current_version_id") not in version_ids] + pinned_missing
                        canonical = (await db.execute(
                            select(CharacterAssetRow).where(
                                CharacterAssetRow.character_id.in_(bound_ids),
                                CharacterAssetRow.status == "CANONICAL")
                        )).scalars().all()
                        invalid_assets = [c.global_character_id for c in draft.characters if c.global_character_id and not any(
                            v.character_id == c.global_character_id and v.version == c.global_character_version
                            and any(v.data.get("canonical_asset_refs", {}).values()) for v in versions)]
                    for check in checks:
                        if check["id"] == "char_snapshot" and invalid_snapshot:
                            check["ok"] = False
                            check["detail"] = "角色没有有效 Character Version：" + ", ".join(invalid_snapshot)
                        if check["id"] == "char_assets" and invalid_assets:
                            check["ok"] = True
                            check["detail"] = "警告：角色缺少 CANONICAL 资产（视频制作时需补充或使用文字模式）：" + ", ".join(invalid_assets)
        failed = [c for c in checks if not c["ok"]]
        if failed:
            from fastapi import HTTPException
            raise HTTPException(422, detail={"message": "发布检查未通过",
                                             "checklist": checks})
        if not reviewed:
            from fastapi import HTTPException
            raise HTTPException(422, detail={"message": "请先勾选「我已审阅这个故事」",
                                             "checklist": checks})
        draft.status = "PUBLISHED"
        draft.reviewed = True
        async with SessionLocal() as db:
            async with db.begin():
                latest = (await db.execute(
                    select(ScenarioVersionRow)
                    .where(ScenarioVersionRow.scenario_id == scenario_id)
                    .order_by(ScenarioVersionRow.created_at.desc()).limit(1))
                ).scalars().first()
                version_id = uid("ver")
                if latest:
                    major, minor, _patch = (int(x) for x in latest.version.split("."))
                    draft.version = f"{major}.{minor + 1}.0"
                row = await db.get(ScenarioRow, scenario_id)
                row.draft = draft.model_dump(mode="json")
                row.status = "PUBLISHED"
                row.updated_at = now_ms()
                db.add(ScenarioVersionRow(
                    id=version_id, scenario_id=scenario_id, version=draft.version,
                    snapshot=draft.model_dump(mode="json"), created_at=now_ms()))
        await tracer.emit("scenario.publish", "success",
                          output={"scenario": scenario_id, "version": draft.version})
        return {"version_id": version_id, "version": draft.version,
                "checklist": checks}

    async def latest_version(self, scenario_id: str) -> Optional[dict]:
        async with SessionLocal() as db:
            row = (await db.execute(
                select(ScenarioVersionRow)
                .where(ScenarioVersionRow.scenario_id == scenario_id)
                .order_by(ScenarioVersionRow.created_at.desc()).limit(1))).scalars().first()
            if row is None:
                return None
            return {"version_id": row.id, "version": row.version, "created_at": row.created_at}

    async def versions(self, scenario_id: str) -> list[dict]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(ScenarioVersionRow)
                .where(ScenarioVersionRow.scenario_id == scenario_id)
                .order_by(ScenarioVersionRow.created_at.desc()))).scalars().all()
            return [{"version_id": r.id, "version": r.version, "created_at": r.created_at}
                    for r in rows]

    async def duplicate(self, scenario_id: str) -> ScenarioDraft:
        """复制草稿（不复制已发布版本；版本历史留在原 Scenario 上）。"""
        src = await self.get(scenario_id)
        if src is None:
            raise KeyError(scenario_id)
        clone = src.model_copy(update={
            "id": uid("scn"),
            "title": f"{src.title}（副本）",
            "status": "DRAFT",
            "reviewed": False,
            "updated_at": now_ms(),
        }, deep=True)
        await self.save_draft(clone)
        return clone

    async def delete(self, scenario_id: str) -> None:
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(ScenarioRow, scenario_id)
                if row is not None:
                    await db.delete(row)


class CharacterService:
    """全局角色库：跨 Scenario 共享、可检索；版本快照绑定到 Scenario Instance。"""

    async def list(self, q: str = "") -> list[dict]:
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(GlobalCharacterRow).order_by(GlobalCharacterRow.updated_at.desc()))
            ).scalars().all()
        items = []
        for r in rows:
            data = dict(r.data)
            data["version"] = r.version
            if q:
                # G11：搜索覆盖 name/bio/tags/personality/appearance
                hay = " ".join([
                    r.name, data.get("bio", ""), data.get("personality", ""),
                    data.get("appearance", ""), " ".join(data.get("tags", []))])
                if q.lower() not in hay.lower():
                    continue
            items.append(data)
        return items

    async def create(self, data: dict) -> dict:
        cid = data.get("id") or uid("chr")
        now = now_ms()
        async with SessionLocal() as db:
            async with db.begin():
                db.add(GlobalCharacterRow(
                    id=cid, name=data.get("name", "未命名角色"),
                    data={**data, "id": cid, "created_at": now, "updated_at": now},
                    version=1, updated_at=now))
        return {**data, "id": cid, "version": 1}

    async def update(self, character_id: str, patch: dict) -> dict:
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(GlobalCharacterRow, character_id)
                if row is None:
                    raise KeyError(character_id)
                from ..domain.schemas import GlobalCharacter
                editable = set(GlobalCharacter.model_fields) - {"id", "version", "current_version_id", "created_at", "updated_at"}
                patch = {k: v for k, v in patch.items() if k in editable}
                data = {**row.data, **patch, "id": character_id, "updated_at": now_ms()}
                validated = GlobalCharacter.model_validate(data)
                if not validated.name.strip() or not validated.bio.strip():
                    raise ValueError("请填写名字和一句话角色定义")
                row.data = data
                row.name = data.get("name", row.name)
                row.version += 1          # 版本递增；已绑定 Scenario 不自动更新（快照隔离）
                row.updated_at = now_ms()
                data["version"] = row.version
        return data

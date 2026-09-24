"""Scenario 服务：草稿 CRUD、Scenario Authoring Skill 起草/修改、发布为不可变版本。"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select

from ..db import SessionLocal
from ..db_models import GlobalCharacterRow, ScenarioRow, ScenarioVersionRow
from ..domain.ids import uid
from ..domain.schemas import ScenarioDraft, now_ms
from ..providers.router import ProviderRouter
from ..runtime.tracer import tracer


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
        draft = ScenarioDraft(id=uid("scn"), title=title)
        await self.save_draft(draft)
        return draft

    async def create_from_idea(self, idea: str) -> ScenarioDraft:
        """Scenario Authoring Skill：从创作想法生成完整草案。"""
        _, rec, resp = await self.router.call_text(
            "authoring",
            messages=[{"role": "user", "content": f"idea: {idea}"}],
            output_contract={"purpose": "authoring_draft"})
        content = json.loads(resp.content)
        draft = ScenarioDraft(
            id=uid("scn"),
            title=content.get("title", "未命名 Scenario"),
            description=content.get("description", idea),
            genre=content.get("genre", ""),
            tone=content.get("tone", ""),
            play_style=content.get("play_style", ""),
        )
        from ..domain.schemas import DramaSpec, WorldSpec
        if content.get("world"):
            draft.world = WorldSpec(**{k: v for k, v in content["world"].items()
                                       if k in WorldSpec.model_fields})
        if content.get("drama"):
            draft.drama = DramaSpec(**{k: v for k, v in content["drama"].items()
                                       if k in DramaSpec.model_fields})
        if content.get("characters"):
            from ..domain.schemas import ScenarioCharacter
            draft.characters = [
                ScenarioCharacter(**{k: v for k, v in c.items()
                                     if k in ScenarioCharacter.model_fields})
                for c in content["characters"] if isinstance(c, dict) and c.get("id")
            ]
        await tracer.emit("authoring.draft", "success",
                          input_={"idea": idea[:120]}, output={"title": draft.title},
                          provider=rec.selected or "")
        await self.save_draft(draft)
        return draft

    # G16：指令补丁允许写入的路径前缀（locks 与任意路径拒绝）
    _PATCHABLE_PREFIXES = ("description", "title", "genre", "tone", "play_style",
                           "drama.", "world.", "theme.", "mechanics.")

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
            if not (path.startswith(self._PATCHABLE_PREFIXES)
                    or path.startswith("characters[")):
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
        """读取点路径：drama.core_question / world.rules / characters[0].desire / title。"""
        try:
            obj: object = draft
            for part in ScenarioService._split_path(path):
                if isinstance(part, int):
                    obj = obj[part]  # type: ignore[index]
                else:
                    obj = getattr(obj, part)
            return obj
        except Exception:
            return None

    @staticmethod
    def _set_path(draft: ScenarioDraft, path: str, value) -> bool:
        parts = ScenarioService._split_path(path)
        if not parts:
            return False
        try:
            obj: object = draft
            for part in parts[:-1]:
                obj = obj[part] if isinstance(part, int) else getattr(obj, part)
            last = parts[-1]
            if isinstance(last, int):
                obj[last] = value  # type: ignore[index]
            else:
                if not hasattr(obj, last):
                    return False
                setattr(obj, last, value)
            return True
        except Exception:
            return False

    @staticmethod
    def _split_path(path: str) -> list:
        """"characters[0].desire" → ["characters", 0, "desire"]。"""
        import re as _re
        out: list = []
        for seg in path.split("."):
            m = _re.match(r"^(\w+)(?:\[(\d+)\])?$", seg)
            if not m:
                continue
            out.append(m.group(1))
            if m.group(2) is not None:
                out.append(int(m.group(2)))
        return out

    async def apply_instruction(self, scenario_id: str, instruction: str) -> ScenarioDraft:
        """Scenario Authoring Skill 修改路径：指令 → typed patches → 校验应用（G16）。"""
        draft = await self.get(scenario_id)
        if draft is None:
            raise KeyError(scenario_id)
        _, rec, resp = await self.router.call_text(
            "authoring",
            messages=[{"role": "user", "content":
                       f"instruction: {instruction}\n"
                       f"draft_summary: {json.dumps({'title': draft.title, 'description': draft.description, 'drama': draft.drama.model_dump(), 'world': draft.world.model_dump()}, ensure_ascii=False)[:2000]}"}],
            output_contract={"purpose": "authoring_patch"})
        content = json.loads(resp.content)
        patches = content.get("patches")
        applied: list[dict] = []
        if isinstance(patches, list) and patches:
            applied = self._apply_typed_patch(draft, patches, source="instruct")
        if not applied:
            # 兼容旧 contract：after 只写 description
            after = content.get("after", "")
            if after:
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
        mechanics_ok = all(isinstance(k, str) and hasattr(v, "enabled")
                           for k, v in draft.mechanics.items())
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
                data = {**row.data, **patch, "id": character_id, "updated_at": now_ms()}
                row.data = data
                row.name = data.get("name", row.name)
                row.version += 1          # 版本递增；已绑定 Scenario 不自动更新（快照隔离）
                row.updated_at = now_ms()
                data["version"] = row.version
        return data

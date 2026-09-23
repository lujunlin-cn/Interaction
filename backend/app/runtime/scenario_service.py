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
        await tracer.emit("authoring.draft", "success",
                          input_={"idea": idea[:120]}, output={"title": draft.title},
                          provider=rec.selected or "")
        await self.save_draft(draft)
        return draft

    async def apply_instruction(self, scenario_id: str, instruction: str) -> ScenarioDraft:
        """Scenario Authoring Skill 修改路径：指令 → 补丁 → 应用（保留人工编辑）。"""
        draft = await self.get(scenario_id)
        if draft is None:
            raise KeyError(scenario_id)
        _, rec, resp = await self.router.call_text(
            "authoring",
            messages=[{"role": "user", "content":
                       f"instruction: {instruction}\ncurrent: {draft.description}"}],
            output_contract={"purpose": "authoring_patch"})
        content = json.loads(resp.content)
        after = content.get("after", "")
        if after:
            draft.description = after
        await tracer.emit("authoring.patch", "success",
                          input_={"instruction": instruction[:120]},
                          provider=rec.selected or "")
        await self.save_draft(draft)
        return draft

    async def publish(self, scenario_id: str) -> dict:
        """发布：生成不可变 ScenarioVersion（PRD：冻结契约、snapshot 哈希、版本号）。"""
        draft = await self.get(scenario_id)
        if draft is None:
            raise KeyError(scenario_id)
        draft.status = "PUBLISHED"
        draft.reviewed = True
        version_id = uid("ver")
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(ScenarioRow, scenario_id)
                row.draft = draft.model_dump(mode="json")
                row.status = "PUBLISHED"
                row.updated_at = now_ms()
                db.add(ScenarioVersionRow(
                    id=version_id, scenario_id=scenario_id, version=draft.version,
                    snapshot=draft.model_dump(mode="json"), created_at=now_ms()))
        await tracer.emit("scenario.publish", "success",
                          output={"scenario": scenario_id, "version": draft.version})
        return {"version_id": version_id, "version": draft.version}

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
                hay = f"{r.name} {data.get('bio', '')} {' '.join(data.get('tags', []))}"
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

"""RuntimeEngine —— Session / Branch 生命周期、Top-K 调度、两阶段提交的总控。

设计要点（对应 PRD）：
- 状态变更全部走 Proposal → Validate → Commit（StateManager / DramaStateManager）
- 推荐分支 Top-K 锁定后并行生成；只有 READY 的分支才显示给玩家（I05）
- 原子发布 ALL_READY_BEFORE_PUBLISH；单分支失败重试 1 次后 K-1 发布（记录 effective_k）
- Two-Phase Canonicalization：SELECTED → PROVISIONAL → 媒体确认 → CANONICAL
- Dependency Fingerprint + 保守 miss；素材变更/愿望变更导致 INVALIDATED
- 每步写事件日志 + Trace；崩溃后从 SessionRow 恢复
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..db_models import AssetRow, ScenarioVersionRow, SessionRow
from ..domain.drama_manager import DramaStateManager
from ..domain.fingerprint import fingerprint_of
from ..domain.ids import uid
from ..domain.media_language import obvious_language_mismatch
from ..domain.schemas import (
    RuntimeProfile, BaseVersions, Branch, BranchSource, BranchStatus, DramaticDirective, DramaPatchProposal,
    DramaState, Event, ForeshadowEntry, InteractionMode, OutcomeSpec, PatchOperation,
    PhaseHint, PresentationReceipt, PressureInstance, RecommendationEpoch, ResolvedIntent,
    SceneArtifact, ScenePacket, ShotPlan, StatePatchProposal, Wish, WishStatus, WorldState,
    now_ms,
)
from ..domain.state_manager import ProposalRejected, StateManager
from ..providers.router import ProviderBlocked, ProviderError, ProviderRouter
from ..skills.registry import is_enabled as skill_enabled
from ..skills import mechanic as mechanic_skill
from ..skills.gameplay_policy import INTENT_PREVIEW_POLICY, CHOICE_POLICY, CAUSAL_NARRATIVE_POLICY, MECHANIC_REPAIR_POLICY
from ..skills.gameplay import (understand_action, director_context, choice_context,
                              mechanic_context, arbitrate, distinct_candidates)
from .session_state import Arc, BudgetLedger, SessionState, TimedState
from .tracer import tracer
from .language_settings import read_language_settings

PHASE_LABELS = {
    BranchStatus.PLANNING: "正在理解你的行动",
    BranchStatus.NARRATIVE: "正在构思接下来的故事",
    BranchStatus.PRODUCTION: "正在设计镜头",
    BranchStatus.GENERATING: "正在生成画面",
    BranchStatus.ASSEMBLING: "正在合成场景",
    BranchStatus.RETRYING: "正在重试生成",
}

state_manager = StateManager()
drama_manager = DramaStateManager()


class EngineError(Exception):
    pass


def _parse_declared_lines(raw: str) -> dict[str, str]:
    """解析 Scenario 声明文本的「id｜描述」行 → {id: 描述}。"""
    out: dict[str, str] = {}
    for line in (raw or "").splitlines():
        parts = [p.strip() for p in line.split("｜")]
        if parts and parts[0]:
            out[parts[0]] = parts[1] if len(parts) > 1 and parts[1] else parts[0]
    return out


def _clue_labels(state: "SessionState") -> dict[str, str]:
    """线索/事实的中文显示名：从 Scenario 声明解析（foreshadows + truth_model）。

    玩法机制对用户显示自然中文，不暴露技术词；未声明的 id 回退裸 id。
    """
    drama = state.scenario_snapshot.get("drama", {})
    labels = _parse_declared_lines(drama.get("foreshadows", ""))
    for line in (drama.get("truth_model") or "").splitlines():
        if "：" in line:
            key, desc = line.split("：", 1)
            labels.setdefault(key.strip(), desc.strip()[:24])
    labels.update(_mechanic_labels(state, "clue-system"))
    return labels


def _mechanic_labels(state: "SessionState", skill: str) -> dict[str, str]:
    """Presentation metadata only, derived from committed evidence, never speculation."""
    labels = {}
    for branch in state.branches:
        if branch.status != BranchStatus.CANONICAL or not branch.outcome:
            continue
        triggers = (branch.director_result or {}).get("outcome", {}).get("skill_triggers", [])
        explicit = {t.get("target"): t.get("label") for t in triggers if t.get("skill") == skill and t.get("label")}
        evidence = "；".join(branch.outcome.evidence)
        for op in branch.outcome.ops:
            key = str(op.value) if skill == "inventory" and op.op == "addItem" else (op.path[6:] if skill == "clue-system" and op.op == "set" and op.path and op.path.startswith("clues.") else None)
            if key:
                # Legacy proposals lacked labels. Show their recorded evidence
                # as a group instead of guessing a translation of technical IDs.
                label = explicit.get(key) or evidence
                if label:
                    labels[key] = label
    return labels


def _ending_families(state: "SessionState") -> dict[str, str]:
    """{family_id: 显示名} —— Scenario drama.ending_families 的「id｜描述」声明。"""
    drama = state.scenario_snapshot.get("drama", {})
    return _parse_declared_lines(drama.get("ending_families", ""))


def _scenario_locations(state: "SessionState") -> list[str]:
    """Scenario 声明的地点 id 列表（world.locations 的「id｜名称」行）。"""
    raw = state.scenario_snapshot.get("world", {}).get("locations", "")
    return [line.split("｜")[0].strip()
            for line in raw.splitlines() if line.strip()]


def _scenario_location_names(state: "SessionState") -> dict[str, str]:
    return _parse_declared_lines(
            state.scenario_snapshot.get("world", {}).get("locations", ""))


def _public_story_text(state: "SessionState", text: str) -> str:
    """Keep internal location ids out of Standard Player narration."""
    value = text or ""
    for location_id, label in _scenario_location_names(state).items():
        if location_id and label and location_id != label:
            value = value.replace(location_id, label)
    return value


def _opening_info(state: "SessionState") -> dict:
    """前情提要（星战式 crawl）：OPENING_PREPARING 阶段立即可得。

    全部由 scenario_snapshot 组装，零生成；前端在视频 READY 前滚动显示，
    READY 后淡出接管。location_line 优先「名称 · 时间感」，premise_lines
    从 premise/description 抽 2–3 句，identity_line 给玩家身份锚点，
    hook_line 用 core_question 留下悬念钩子。
    """
    snapshot = state.scenario_snapshot
    drama = snapshot.get("drama", {})
    world = snapshot.get("world", {})
    chars = {c.get("id"): c for c in snapshot.get("characters", [])}
    player_char = chars.get(snapshot.get("player_character", "player"), {})

    # 地点行：优先「名称 · 年份/氛围」（生化危机那类 "Raccoon City · Sept 1998"），
    # 退化成第一条 locations 的显示名 + world.era/time 字段兜底。
    loc_names = _scenario_location_names(state)
    first_loc_label = next(iter(loc_names.values()), "") or world.get("name", "")
    era = world.get("era") or world.get("time") or world.get("setting_time") or ""
    location_line = " · ".join(x for x in [first_loc_label, era] if x)

    # 前情段：premise → description → title 逐级退化；按中文句号/换行切 2–3 句
    import re as _re
    raw_premise = (snapshot.get("premise") or snapshot.get("description")
                   or snapshot.get("title") or "")
    premise_lines = [
        ln.strip() for ln in _re.split(r"(?<=[。！？!?])|\n", raw_premise)
        if ln.strip()
    ][:3]

    # 身份锚点：玩家角色 display identity（快照里的 identity 字段）
    identity = (player_char.get("identity") or "你").strip()
    identity_line = f"你是 {identity}。" if identity and not identity.startswith("你") else ""

    # 悬念钩子：core_question 保留问句形态，让玩家知道故事要回答什么
    hook_line = (drama.get("core_question") or "").strip()

    # 主题色：按 genre 给 hue，前端合成 HSL，避免把视觉细节堆到后端
    genre = (snapshot.get("genre") or "").lower()
    accent_map = {
        "horror": "#c8a86b", "生化": "#c8a86b", "悬疑": "#c8a86b",
        "scifi": "#7db3e8", "科幻": "#7db3e8",
        "fantasy": "#b98ae8", "奇幻": "#b98ae8",
        "romance": "#e88aa8", "爱情": "#e88aa8",
        "thriller": "#d4c06a", "惊悚": "#d4c06a",
    }
    accent = "#e2d5a7"  # 默认星战金
    for key, color in accent_map.items():
        if key in genre:
            accent = color
            break

    return {
        "location_line": location_line,
        "premise_lines": premise_lines,
        "identity_line": identity_line,
        "hook_line": hook_line,
        "accent": accent,
    }


def _npc_ids(state: "SessionState") -> list[str]:
    """在场非玩家角色 id（按 Scenario characters 声明顺序）。"""
    player_id = state.scenario_snapshot.get("player_character", "player")
    return [c.get("id") for c in state.scenario_snapshot.get("characters", [])
            if c.get("id") and c.get("id") != player_id]


def _to_patch_ops(raw_ops: list[dict]) -> list[PatchOperation]:
    return [PatchOperation(**op) for op in raw_ops]


class RuntimeEngine:
    def __init__(self, router: ProviderRouter):
        self.router = router
        self.sessions: dict[str, SessionState] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.subscribers: dict[str, list[Any]] = {}
        self._pipeline_tasks: dict[str, asyncio.Task] = {}
        self._timed_tasks: dict[str, asyncio.Task] = {}   # 限时互动倒计时 watchdog

    # ==================================================================
    # Session 生命周期
    # ==================================================================
    def _lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self.locks:
            self.locks[session_id] = asyncio.Lock()
        return self.locks[session_id]

    def _scenario_brief(self, state: SessionState) -> dict:
        """Director/Narrative 调用的 Scenario+当前状态摘要（泛化，不含硬编码故事）。"""
        snapshot = state.scenario_snapshot
        drama = snapshot.get("drama", {})
        chars = {c.get("id"): c for c in snapshot.get("characters", [])}
        return director_context({
            "title": snapshot.get("title", ""),
            "premise": snapshot.get("premise") or snapshot.get("description", ""),
            "genre": snapshot.get("genre", ""),
            "tone": snapshot.get("tone", ""),
            "core_question": (state.current_arc().question if state.current_arc() else "") or drama.get("core_question", ""),
            "central_conflict": (state.current_arc().conflict if state.current_arc() else "") or drama.get("central_conflict", ""),
            "ending_families": _ending_families(state),
            "truth_model": drama.get("truth_model", ""),
            "authored_anchors": drama.get("anchors", ""),
            "forbidden_outcomes": drama.get("forbidden_outcomes", ""),
            "world_rules": snapshot.get("world", {}).get("rules", ""),
            "world_constraints": snapshot.get("world", {}).get("constraints", ""),
            "player": chars.get(snapshot.get("player_character"), {}),
            "locations": _scenario_location_names(state),
            "location": state.world.location,
            "inventory": state.world.inventory,
            "clues": list(state.world.clues.keys()),
            "knowledge": list(state.world.knowledge),
            "canonical_facts": {key: value for key, value in state.world.truth.items() if value},
            "objects": state.world.objects,
            "recent_canonical_beats": [
                {"title": b.outcome.title, "result": b.outcome.text,
                 "presented_narrative": b.narrative, "evidence": b.outcome.evidence}
                for b in state.branches if b.status == BranchStatus.CANONICAL and b.outcome][-4:],
            "wishes": [{"text": wish.raw, "status": wish.status.value}
                       for wish in state.wishes if wish.status == WishStatus.ACTIVE],
            "relationships": state.world.relationships,
            "phase": state.drama.phase.value,
            "npcs": [{**chars.get(cid, {}), "id": cid}
                     for cid in _npc_ids(state)],
        })

    async def _persist(self, state: SessionState) -> None:
        state.touch()
        async with SessionLocal() as db:
            async with db.begin():
                row = await db.get(SessionRow, state.id)
                payload = state.model_dump(mode="json")
                if row is None:
                    row = SessionRow(id=state.id, scenario_id=state.scenario_id,
                                     scenario_version_id=state.scenario_version_id,
                                     status="ENDED" if state.ended else "ACTIVE",
                                     state=payload,
                                     created_at=state.created_at, updated_at=state.updated_at)
                    db.add(row)
                else:
                    row.state = payload
                    row.status = "ENDED" if state.ended else "ACTIVE"
                    row.updated_at = state.updated_at

    async def load_session(self, session_id: str) -> Optional[SessionState]:
        if session_id in self.sessions:
            return self.sessions[session_id]
        async with SessionLocal() as db:
            row = await db.get(SessionRow, session_id)
            if row is None:
                return None
            state = SessionState(**row.state)
            self.sessions[session_id] = state
            return state

    def _event(self, state: SessionState, type_: str, summary: str,
               branch_id: str | None = None, **extra) -> Event:
        arc = state.current_arc()
        evt = Event(
            id=uid("evt"), session_id=state.id, arc_id=arc.id if arc else "",
            type=type_, summary=summary, branch_id=branch_id,
            world_version=state.world.version, drama_revision=state.drama.revision,
            operations=extra.pop("operations", []), extra=extra)
        state.add_event(evt)
        return evt

    async def create_session(self, scenario_version_id: str) -> SessionState:
        async with SessionLocal() as db:
            vrow = await db.get(ScenarioVersionRow, scenario_version_id)
            if vrow is None:
                raise EngineError(f"scenario version not found: {scenario_version_id}")
            import copy
            snapshot = copy.deepcopy(vrow.snapshot)
            scenario_id = vrow.scenario_id
            arows = (await db.execute(
                select(AssetRow).where(AssetRow.scenario_id == scenario_id))).scalars().all()
            # G12：在场角色绑定的全局角色 ref 素材并入 manifest。
            # v0.6（FR-091/Q86）：优先消费 publish 时冻结的 ScenarioCharacterSnapshot
            # （frozen_asset_refs → CharacterAssetRow.url，URL 直进 manifest，不依赖 AssetRow）；
            # 无快照的角色回落到 GlobalCharacterRow 的 ref_* 槽位（向后兼容）。
            from ..db_models import (CharacterAssetRow, GlobalCharacterRow,
                                     ScenarioCharacterSnapshotRow)
            snap_rows = (await db.execute(
                select(ScenarioCharacterSnapshotRow).where(
                    ScenarioCharacterSnapshotRow.scenario_version_id ==
                    scenario_version_id))).scalars().all()
            snap_by_gcid = {r.global_character_id: r for r in snap_rows}
            char_global: dict[str, dict] = {}
            for ch in snapshot.get("characters", []):
                gcid = ch.get("global_character_id")
                if gcid:
                    grow = await db.get(GlobalCharacterRow, gcid)
                    if grow is not None:
                        char_global[ch.get("id", "")] = dict(grow.data)
            g_assets: dict[str, dict] = {}
            # v0.6：快照冻结的 Canonical 资产（URL 直引，角色粒度 entity）
            for ch in snapshot.get("characters", []):
                cid = ch.get("id", "")
                gcid = ch.get("global_character_id")
                srow = snap_by_gcid.get(gcid) if gcid else None
                if srow is None:
                    continue
                ch["appearance"] = (srow.data.get("frozen_identity") or {}).get("appearance", "")
                ch.update({k: v for k, v in (srow.data.get("local_overrides") or {}).items() if k in ("identity", "personality", "desire", "fear", "secrets", "knowledge", "relationship", "visual_state")})
                for role, value in (srow.data.get("frozen_asset_refs") or {}).items():
                    for ca_id in value if isinstance(value, list) else [value]:
                        if not ca_id or f"{cid}:{ca_id}" in g_assets:
                            continue
                        crow = await db.get(CharacterAssetRow, ca_id)
                        arow = None if crow is not None else await db.get(AssetRow, ca_id)
                        if crow is None and arow is None:
                            continue
                        asset = crow.data if crow is not None else arow.data
                        g_assets[f"{cid}:{ca_id}"] = {
                            "id": ca_id, "version": srow.data.get("character_version", 1),
                            "role": "wardrobe" if role == "outfit" else role,
                            "entity": cid, "binding": cid,
                            "character_snapshot_id": srow.id,
                            "name": asset.get("name") or f"{role}·v{srow.data.get('character_version',1)}",
                            "type": asset.get("type") or ("voice" if role == "voice" else "video" if role == "motion" else "image"),
                            "path": asset.get("url") or asset.get("storage_path", "")}
                # voice / motion 同样冻结进快照（frozen_asset_refs 里 role=voice/motion）
            # 兼容路径：没有 v0.6 快照的角色仍走 ref_* 槽位
            ref_asset_ids: list[tuple[str, str]] = []
            for ch in snapshot.get("characters", []):
                cid = ch.get("id", "")
                gcid = ch.get("global_character_id")
                if gcid and gcid in snap_by_gcid:
                    continue                # 已走 v0.6 快照
                gdata = char_global.get(cid)
                if not gdata:
                    continue
                for key, role in (("ref_front_asset", "identity"),
                                  ("ref_side_asset", "identity"),
                                  ("ref_back_asset", "identity"),
                                  ("ref_voice_asset", "voice"),
                                  ("ref_motion_asset", "motion")):
                    aid = gdata.get(key)
                    if aid:
                        ref_asset_ids.append((cid, aid))
                for aid in gdata.get("ref_other_assets", []) or []:
                    ref_asset_ids.append((cid, aid))
            for cid, aid in ref_asset_ids:
                if aid in g_assets:
                    continue
                arow = await db.get(AssetRow, aid)
                if arow is not None:
                    g_assets[aid] = {
                        "id": arow.data.get("id"), "version": arow.data.get("version", 1),
                        "role": arow.data.get("role", "") or "identity",
                        "entity": cid, "binding": cid,
                        "name": arow.data.get("name", ""),
                        "type": arow.data.get("type", ""),
                        "path": arow.data.get("storage_path", "")}
        state = self._bootstrap(scenario_version_id, scenario_id, snapshot)
        frozen_character_ids = {c.get("id") for c in snapshot.get("characters", [])
                                if c.get("global_character_id") in snap_by_gcid}
        state.asset_manifest = [
            {"id": r.data.get("id"), "version": r.data.get("version", 1),
             "role": r.data.get("role", ""), "entity": r.data.get("entity", ""),
             "binding": r.data.get("binding", ""), "name": r.data.get("name", ""),
             "type": r.data.get("type", ""), "path": r.data.get("storage_path", "")}
            for r in arows if not ({r.data.get("entity"), r.data.get("binding")} & frozen_character_ids)
        ] + list(g_assets.values())
        self.sessions[state.id] = state
        await self._persist(state)
        await tracer.emit("session.create", "success", output={"session_id": state.id},
                          session_id=state.id)
        # 首幕先走正式媒体管线，播放开始后 _present 再启动推荐预生成。
        asyncio.get_running_loop().create_task(self._start_opening(state.id))
        return state

    async def _start_opening(self, session_id: str) -> None:
        """建立首幕分支，复用 Narrative -> Production -> Video -> Assembly。"""
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state or state.ended or state.branches:
                return
            snapshot = state.scenario_snapshot
            world = snapshot.get("world", {})
            premise = snapshot.get("premise") or snapshot.get("description") or snapshot.get("title", "故事开场")
            branch = Branch(
                id=uid("opening"), trace_id=uid("trace"), session_id=state.id,
                arc_id=state.current_arc().id if state.current_arc() else "",
                epoch_id=uid("opening_epoch"), source=BranchSource.OPENING,
                label=f"{state.world.location}的开场", summary=str(premise)[:180],
                intent=ResolvedIntent(raw_text="opening", action="opening", confidence=1.0,
                                      desire_source="SCENARIO"),
                base_versions=self._branch_base_versions(state),
                read_set=self.build_read_set(state), fingerprint=self.compute_fingerprint(state),
                expires_at=now_ms() + settings.branch_ttl_seconds * 1000,
            )
            state.branches.append(branch)
            state.epoch = RecommendationEpoch(id=branch.epoch_id, k=1, target_k=1,
                                              status="PLANNING", branch_ids=[branch.id])
            state.player.status = "OPENING_PREPARING"
            self._event(state, "opening_started", f"开始准备开场：{state.world.location}", branch_id=branch.id)
            await self._persist(state)
            await self._push(state)
        self._spawn_pipeline(session_id, branch.id)

    def _bootstrap(self, version_id: str, scenario_id: str, snapshot: dict) -> SessionState:
        drama_spec = snapshot.get("drama", {})
        world_spec = snapshot.get("world", {})
        characters = snapshot.get("characters", [])
        locations = [line.split("｜")[0].strip()
                     for line in world_spec.get("locations", "").splitlines() if line.strip()]
        truth_facts: dict[str, str] = {}
        for line in drama_spec.get("truth_model", "").splitlines():
            if "：" in line:
                key = line.split("：", 1)[0].strip()
                truth_facts[key] = ""            # "" = 未揭示
        pressures: list[PressureInstance] = []
        for line in drama_spec.get("pressures", "").splitlines():
            parts = [p.strip() for p in line.split("｜")]
            if parts and parts[0]:
                driver = "FICTION_TIME" if len(parts) > 2 and "时间" in parts[2] \
                    else "COMMITTED_ACTIONS"
                pressures.append(PressureInstance(
                    id=uid("prs"), title=parts[0],
                    source=parts[1] if len(parts) > 1 else "",
                    driver=driver,
                    deadline_basis=parts[2] if len(parts) > 2 else ""))
        foreshadows: list[ForeshadowEntry] = []
        for line in drama_spec.get("foreshadows", "").splitlines():
            parts = [p.strip() for p in line.split("｜")]
            if parts and parts[0]:
                foreshadows.append(ForeshadowEntry(
                    id=parts[0], origin="AUTHOR_SEEDED",
                    truth=parts[1] if len(parts) > 1 else ""))
        world = WorldState(
            version=1, location=locations[0] if locations else "unknown",
            inventory=[], objects={}, relationships={}, knowledge=[], clues={},
            truth=truth_facts, fiction_minutes=0, health=100, inspected=[])
        for ch in characters:
            if not ch.get("id") or ch["id"] == snapshot.get("player_character", "player"):
                continue
            world.relationships[ch["id"]] = mechanic_skill.INITIAL_RELATIONSHIP
            rel = ch.get("relationship", "")
            if "信任" in rel and "/" in rel:
                try:
                    value = int(rel.split("信任")[1].split("/")[0].strip())
                    if ch.get("id") != "player":
                        world.relationships[ch["id"]] = value
                except (ValueError, IndexError):
                    pass
        drama = DramaState(plan_version=1, phase=PhaseHint.SETUP, foreshadows=foreshadows)
        state = SessionState(
            id=uid("sess"), scenario_id=scenario_id, scenario_version_id=version_id,
            scenario_snapshot=snapshot, world=world, drama=drama, pressures=pressures,
            budget=BudgetLedger(total=settings.budget_total, per_turn=settings.budget_per_turn),
            arcs=[Arc(id=uid("arc"), seq=1)],
        )
        self._event(state, "session_created", f"创建会话：{snapshot.get('title', scenario_id)}")
        return state

    # ==================================================================
    # 上下文与指纹
    # ==================================================================
    def build_read_set(self, state: SessionState) -> dict[str, Any]:
        # 注意：knowledge 不参与指纹。knowledge 只由「呈现回执」追加（玩家看完当前场景），
        # 它与分支选择属于同一逻辑提交；若计入指纹，回执会让播放期间预生成的所有候选
        # 保守误失效（预测式生成的核心路径因此作废）。
        return {
            "world": {
                "location": state.world.location,
                "inventory": sorted(state.world.inventory),
                "relationships": dict(state.world.relationships),
                "objects": dict(state.world.objects),
                "clues": dict(state.world.clues),
                "truth": dict(state.world.truth),
                "fiction_minutes": state.world.fiction_minutes,
            },
            "drama": {"plan_version": state.drama.plan_version, "phase": state.drama.phase.value},
            "wish": {"seq": state.wish_seq},
            "assets": {"refs": self._asset_refs(state)},
            "provider": {"contract": "v1"},
        }

    def _asset_refs(self, state: SessionState) -> list[str]:
        return sorted(f"{a.get('id')}:{a.get('version', 1)}" for a in state.asset_manifest)

    async def refresh_assets(self, scenario_id: str) -> None:
        """素材变更后：刷新该 Scenario 所有活跃会话的素材快照（指纹随之变化 → 保守失效）。

        已呈现/已推荐的资产不受 allow_media_invalidate=False 的保护策略影响（PRD Q48A）。
        """
        async with SessionLocal() as db:
            rows = (await db.execute(
                select(AssetRow).where(AssetRow.scenario_id == scenario_id))).scalars().all()
            manifest = [{"id": r.data.get("id"), "version": r.data.get("version", 1),
                         "role": r.data.get("role", ""), "entity": r.data.get("entity", ""),
                         "binding": r.data.get("binding", ""), "name": r.data.get("name", ""),
                         "type": r.data.get("type", ""), "path": r.data.get("storage_path", "")}
                        for r in rows]
        for state in list(self.sessions.values()):
            if state.scenario_id != scenario_id:
                continue
            async with self._lock(state.id):
                frozen = [a for a in state.asset_manifest if a.get("character_snapshot_id")]
                frozen_ids = {c.get("id") for c in state.scenario_snapshot.get("characters", [])
                              if c.get("global_character_id")}
                state.asset_manifest = [a for a in manifest if not (
                    {a.get("entity"), a.get("binding")} & frozen_ids)] + frozen
                fp = self.compute_fingerprint(state)
                if state.allow_media_invalidate:
                    self._invalidate_stale(state, fp)
                self._event(state, "assets_changed", "素材库已更新")
                await self._persist(state)
                await self._push(state)

    def compute_fingerprint(self, state: SessionState) -> str:
        return fingerprint_of(self.build_read_set(state))

    def build_context(self, state: SessionState, directive: dict) -> dict:
        """Hierarchical Working Context：system / scenario / arc / scene / branch 五层。"""
        arc = state.current_arc()
        return {
            "system": {"tone": state.scenario_snapshot.get("tone", ""),
                       "rules": state.scenario_snapshot.get("world", {}).get("rules", "")},
            "scenario": {
                "core_question": state.scenario_snapshot.get("drama", {}).get("core_question", "")},
            "arc": {"seq": arc.seq if arc else 1, "phase": state.drama.phase.value},
            "scene": {"location": state.world.location,
                      "recent_events": [e.summary for e in state.events[-5:]]},
            "branch": directive,
        }

    def _branch_base_versions(self, state: SessionState) -> BaseVersions:
        arc = state.current_arc()
        return BaseVersions(world=state.world.version, drama=state.drama.revision,
                            arc=arc.id if arc else "", wish=state.wish_seq)

    # ==================================================================
    # 候选推荐（Director Agent 视角）
    # ==================================================================
    def _generic_candidates(self, state: SessionState) -> list[dict]:
        """确定性通用候选：按 Scenario 声明的 locations/characters 参数化。

        三类稳定模板（观察 / 对话 / 主动退出），不绑定任何具体故事语义。
        """
        world = state.world
        loc_names = _scenario_location_names(state)
        loc_ids = _scenario_locations(state)
        npcs = _npc_ids(state)
        chars = {c.get("id"): c for c in state.scenario_snapshot.get("characters", [])}
        here = loc_names.get(world.location, world.location)
        english = read_language_settings().video_language == "en"
        candidates: list[dict] = [
            dict(label=f"Examine {here}" if english else f"仔细观察{here}的细节", confidence=0.6,
                 summary="Gather observable information first" if english else "不承诺立场，先收集眼前可观察的信息", kind="investigation"),
        ]
        for cid in npcs[:1]:
            name = chars.get(cid, {}).get("identity", cid).split(" /")[0]
            candidates.append(
                dict(label=f"Talk to {name}" if english else f"和{name}谈谈，听 TA 怎么说", confidence=0.6,
                     summary="Hear what they have noticed and decide together" if english else "听听对方发现了什么，再一起决定下一步", kind="social"))
        other_locs = [l for l in loc_ids if l != world.location]
        if other_locs:
            dest = loc_names.get(other_locs[-1], other_locs[-1])
            candidates.append(
                dict(label=f"Leave for {dest}" if english else f"离开这里，去{dest}", confidence=0.55,
                     summary="Look for a route out of the current predicament" if english else "寻找离开眼前困境的路线", kind="withdrawal"))
        else:
            candidates.append(
                dict(label="Withdraw from the situation" if english else "主动退出眼前的故事", confidence=0.55,
                     summary="Stop participating in the conflict" if english else "不再参与眼前的矛盾", kind="withdrawal"))
        return candidates

    async def candidate_actions(self, state: SessionState) -> list[dict]:
        """推荐候选 = Director 按当前 World/Drama/Scenario 上下文生成 + Jev 排序
        + 确定性通用兜底（Provider 全不可用时仍保证玩家有可选项）。"""
        world = state.world
        snapshot = state.scenario_snapshot
        drama = snapshot.get("drama", {})
        loc_names = _scenario_location_names(state)
        npcs = _npc_ids(state)
        chars = {c.get("id"): c for c in snapshot.get("characters", [])}
        context = {
            "title": snapshot.get("title", ""),
            "tone": snapshot.get("tone", ""),
            "core_question": drama.get("core_question", ""),
            "location": world.location,
            "location_name": loc_names.get(world.location, world.location),
            "locations": loc_names,
            "inventory": world.inventory,
            "clues": list(world.clues.keys()),
            "relationships": world.relationships,
            "npcs": [{"id": cid, "identity": chars.get(cid, {}).get("identity", "")}
                     for cid in npcs],
            "phase": state.drama.phase.value,
            "wishes": [w.raw for w in state.wishes if w.status == WishStatus.ACTIVE],
            "recent_events": [e.summary for e in state.events[-5:]],
            "instruction": read_language_settings().text_instruction() + "生成 3-5 个玩家此刻可采取的行动候选，"
                           "返回 JSON: {\"candidates\": [{\"label\",\"summary\",\"kind\"}]}，"
                           "kind ∈ investigation/social/risk/withdrawal",
        }
        decision_context = choice_context(self._scenario_brief(state), state.preferences.model_dump(),
                                          [p.model_dump() for p in state.pressures])
        context.update(decision_context)
        context["instruction"] += CHOICE_POLICY
        candidates: list[dict] = []
        if not skill_enabled("choice-evaluation"):
            return self._generic_candidates(state)
        try:
            _, rec, resp = await self.router.call_text(
                "director",
                messages=[{"role": "user", "content":
                           f"scenario_context: {json.dumps(context, ensure_ascii=False)}"}],
                output_contract={"purpose": "candidate_actions"},
                branch_id=None)
            content = json.loads(resp.content)
            for c in (content.get("candidates") or []):
                label = str(c.get("label", "")).strip()
                if label:
                    candidates.append(dict(
                        label=label[:40],
                        summary=str(c.get("summary", ""))[:80],
                        confidence=float(c.get("confidence", 0.6)),
                        kind=str(c.get("kind", "investigation"))))
            await tracer.emit("director.candidates", "success",
                              input_={"context": context}, output={"count": len(candidates), "candidates": candidates},
                              provider=rec.selected or "", session_id=state.id)
        except (ProviderBlocked, ProviderError, ValueError, KeyError) as e:
            await tracer.emit("director.candidates", "degraded",
                              output={"reason": str(e)[:200]}, session_id=state.id)
        if not candidates:
            candidates = self._generic_candidates(state)

        candidates, duplicate_decisions = distinct_candidates(candidates)
        latest = next((b for b in reversed(state.branches) if b.status == BranchStatus.CANONICAL
                       and b.source != BranchSource.OPENING), None)
        if latest and len(candidates) > 1:
            remaining = [c for c in candidates if c["label"].strip() != latest.label.strip()]
            if remaining:
                candidates = remaining
        # Jev/Decision 排序（Mock 决策或真实 API）；不可用则保持现有顺序
        try:
            _, rec, answer = await self.router.call_decision(
                state=decision_context,
                questions=[{"id": "rank", "candidates": [c["label"] for c in candidates]}])
            ranked = answer.scores or {}
            if ranked:
                candidates.sort(key=lambda c: -ranked.get(c["label"], 0.0))
            await tracer.emit("decision.rank", "success",
                              input_={"candidates": [c["label"] for c in candidates], "context": decision_context},
                              output={"ranked": ranked, "other_probability": ranked.get("OTHER"),
                                      "deduplicated": duplicate_decisions}, provider=rec.selected or "",
                              model=answer.model, duration_ms=answer.latency_ms,
                              skill_id="choice-evaluation", skill_version="1.0.0", session_id=state.id)
        except (ProviderBlocked, ProviderError) as e:
            await tracer.emit("decision.rank", "degraded", output={"reason": str(e)},
                              session_id=state.id)
        return candidates

    async def prepare_recommendations(self, state: SessionState) -> None:
        """Scheduler：指纹校验 → 失效 → Top-K 锁定 → 预算预留 → 并行生成。"""
        current_fp = self.compute_fingerprint(state)
        self._invalidate_stale(state, current_fp)

        if state.epoch and not state.epoch.published and state.epoch.status != "FAILED":
            return  # 已有锁定批次在生成
        if state.epoch and state.epoch.published:
            ready_left = [bid for bid in state.epoch.ready_ids
                          if (b := state.branch(bid)) and b.status == BranchStatus.READY]
            if ready_left:
                return  # 还有可展示的推荐，等玩家选择

        candidates = (await self.candidate_actions(state))[: settings.effective_target_k]
        state.hint_chips = [c["label"] for c in candidates[:3]]
        # 限时互动触发（I02/I03）：Scenario 预先声明 + 时机条件（至少已完成两个有效行动）
        timed_node = self._next_timed_node(state)
        branch_ids: list[str] = []
        epoch_id = uid("epoch")
        mode = InteractionMode.TIMED if timed_node else InteractionMode.UNTIMED
        source = BranchSource.TIMED if timed_node else BranchSource.RECOMMENDATION
        for cand in candidates:
            estimated = settings.effective_shots_per_branch * settings.shot_unit_cost
            if state.budget.available() < estimated:
                break  # 预算不足：减少 K，不静默超支
            branch = Branch(
                id=uid("br"), trace_id=uid("trace"), session_id=state.id,
                arc_id=state.current_arc().id if state.current_arc() else "",
                epoch_id=epoch_id, source=source,
                label=cand["label"], summary=cand["summary"], probability=cand["confidence"],
                intent=ResolvedIntent(raw_text=cand["label"], action=cand["label"],
                                      confidence=cand["confidence"],
                                      desire_source="UNKNOWN"),
                interaction_mode=mode,
                base_versions=self._branch_base_versions(state),
                read_set=self.build_read_set(state), fingerprint=current_fp,
                expires_at=now_ms() + settings.branch_ttl_seconds * 1000,
            )
            state.branches.append(branch)
            state.budget.reserved += estimated
            branch_ids.append(branch.id)
        state.epoch = RecommendationEpoch(
            id=epoch_id, k=len(branch_ids), target_k=settings.effective_target_k,
            status="PLANNING", branch_ids=branch_ids, timed=bool(timed_node),
            # Decision content is safe to show as soon as Jev has locked it.
            # Media readiness is a separate gate and may lag behind.
            # Jev decision text is independent from media readiness. Timed
            # choices follow the same contract and open at Decision Lead.
            options_exposed=True,
            options_exposed_at=now_ms())
        if timed_node:
            # 确定性超时 fallback 分支（Scenario 预先声明，不允许模型临场改判）
            timeout_s = settings.timed_timeout_override or timed_node["timeout_s"]
            fb = Branch(
                id=uid("br"), trace_id=uid("trace"), session_id=state.id,
                arc_id=state.current_arc().id if state.current_arc() else "",
                epoch_id=epoch_id, source=BranchSource.FALLBACK,
                label="保持沉默，不作回应", summary=timed_node["fallback"],
                interaction_mode=InteractionMode.TIMED,
                outcome=OutcomeSpec(title="没有回应", text=timed_node["fallback"],
                                    kind="social"),
                base_versions=self._branch_base_versions(state),
                read_set=self.build_read_set(state), fingerprint=current_fp,
                expires_at=now_ms() + settings.branch_ttl_seconds * 1000,
            )
            state.branches.append(fb)
            state.budget.reserved += settings.effective_shots_per_branch * settings.shot_unit_cost
            state.timed = TimedState(
                active=True, node_id=timed_node["id"], kind=timed_node["kind"],
                branch_ids=branch_ids, timeout_seconds=timeout_s,
                fallback_branch_id=fb.id, selection_open=False,
                fired_nodes=[*state.timed.fired_nodes, timed_node["id"]])
            self._event(state, "timed_started",
                        f"限时互动开始（{int(timeout_s)} 秒）", node=timed_node["id"])
            self._spawn_pipeline(state.id, fb.id)
        self._event(state, "epoch_locked",
                    f"锁定 {len(branch_ids)} 条候选分支（指纹 {current_fp[:12]}）",
                    epoch=epoch_id)
        await tracer.emit("scheduler.lock_topk", "success",
                          output={"k": len(branch_ids), "fingerprint": current_fp[:12]},
                          session_id=state.id)
        await self._persist(state)
        for bid in branch_ids:      # Q59：Top-K 锁定后并行生成
            self._spawn_pipeline(state.id, bid)

    def _invalidate_stale(self, state: SessionState, current_fp: str) -> None:
        in_flight = (BranchStatus.PREDICTED, BranchStatus.PLANNING, BranchStatus.NARRATIVE,
                     BranchStatus.PRODUCTION, BranchStatus.GENERATING,
                     BranchStatus.ASSEMBLING, BranchStatus.RETRYING)
        for b in state.branches:
            if b.status in in_flight:
                if b.expires_at and now_ms() > b.expires_at:
                    b.status = BranchStatus.EXPIRED
                    self._release_budget(state, b)
                    self._event(state, "branch_expired", f"分支过期：{b.label}", branch_id=b.id)
                elif b.fingerprint != current_fp:
                    b.status = BranchStatus.INVALIDATED
                    b.invalidated_reason = "fingerprint_mismatch"
                    self._release_budget(state, b)
                    self._event(state, "branch_invalidated",
                                f"世界已变化，候选失效：{b.label}", branch_id=b.id)

    def _release_budget(self, state: SessionState, branch: Branch) -> None:
        spent = state.budget.spent_by_branch.get(branch.id, 0)
        estimated = settings.effective_shots_per_branch * settings.shot_unit_cost
        releasable = max(0, estimated - spent)
        state.budget.reserved = max(0, state.budget.reserved - releasable)

    # ==================================================================
    # 限时互动（I02/I03：TIMED 互动是 Scenario 声明的互动模式，不是 UI 特效）
    # ==================================================================
    def _next_timed_node(self, state: SessionState) -> Optional[dict]:
        """从 Scenario 声明中解析下一个待触发的限时节点。

        触发条件（确定性）：本篇章未触发过、QTE 玩法启用、已达到声明的行动次数，
        且正式世界位置符合已声明的地点限制。超时结果由 Scenario 预先声明。
        """
        if not state.scenario_snapshot.get("mechanics", {}).get("qte", {}).get("enabled", True):
            return None
        arc = state.current_arc()
        turns_done = len([t for t in state.turns
                          if arc and t.get("arc_seq") == arc.seq
                          and not t.get("opening")])
        config = state.scenario_snapshot.get("mechanics", {}).get("qte", {}).get("config", {})
        trigger_after = config.get("trigger_after_actions", 1)
        if turns_done < trigger_after:
            return None   # 至少完成一个关键行动后才可能进入限时节点
        trigger_locations = config.get("trigger_location_ids", [])
        if trigger_locations and state.world.location not in trigger_locations:
            return None
        raw = state.scenario_snapshot.get("drama", {}).get("timed_interactions", "")
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split("｜")]
            if len(parts) >= 4 and parts[0] and parts[0] not in state.timed.fired_nodes:
                try:
                    timeout_s = float(parts[2])
                except ValueError:
                    continue
                return {"id": parts[0], "kind": parts[1] or "qte",
                        "timeout_s": timeout_s, "fallback": parts[3]}
        return None

    def _schedule_timed_watchdog(self, session_id: str) -> None:
        old = self._timed_tasks.get(session_id)
        if old and not old.done():
            old.cancel()
        self._timed_tasks[session_id] = asyncio.get_running_loop().create_task(
            self._timed_watchdog(session_id))

    async def _timed_watchdog(self, session_id: str) -> None:
        """服务端倒计时权威：到点未选择 → 执行 Scenario 预声明的确定性 fallback。"""
        try:
            while True:
                await asyncio.sleep(0.25)
                async with self._lock(session_id):
                    state = await self.load_session(session_id)
                    if not state or not state.timed.active:
                        return
                    if not state.timed.deadline_ms:
                        if state.player.position() < state.player.decision_open_at and state.player.status not in ("READY", "WAITING_DECISION", "ENDED"):
                            continue
                        state.timed.selection_open = True
                        state.timed.deadline_ms = now_ms() + int(state.timed.timeout_seconds * 1000)
                        await self._persist(state)
                        await self._push(state)
                    remaining = state.timed.deadline_ms - now_ms()
                    if remaining > 0:
                        continue
                    state.timed.active = False
                    state.counters.fallback_used += 1
                    fb = state.branch(state.timed.fallback_branch_id or "")
                    self._event(state, "timed_fallback_executed",
                                "倒计时结束：按这个故事已经设定好的结果继续",
                                branch_id=fb.id if fb else None)
                    if fb and self.valid_branch(state, fb):
                        await self._commit_selected(state, fb)
                    else:
                        # 媒体未就绪：同一确定性结果退化为文本呈现（结果不变，形式降级）
                        text = (fb.outcome.text if fb and fb.outcome
                                else "你保持沉默，故事按预设的结果继续。")
                        state.player.status = "READY"
                        state.player.scene_title = fb.outcome.title if fb and fb.outcome \
                            else "没有回应"
                        state.player.scene_text = text
                        state.player.caption = text[:60]
                        state.player.video_url = ""
                        state.player.duration = 0.0
                        state.player.playing = False
                        state.epoch = None
                        state.messages.append({"kind": "system", "text": text,
                                               "at": now_ms()})
                        state.messages = state.messages[-50:]
                        asyncio.get_running_loop().create_task(self._safe_prepare(session_id))
                        await self._persist(state)
                        await self._push(state)
                    await tracer.emit("timed.fallback", "success",
                                      output={"node": state.timed.node_id},
                                      session_id=session_id)
                    return
        except asyncio.CancelledError:
            return

    def _cancel_timed(self, state: SessionState) -> None:
        state.timed.active = False
        state.timed.deadline_ms = None
        task = self._timed_tasks.get(state.id)
        if task and not task.done():
            task.cancel()

    async def _maybe_open_timed_window(self, state: SessionState) -> None:
        """Open a timed choice at Decision Lead, without waiting for H3."""
        if (not state.timed.active or state.timed.selection_open
                or not state.epoch or not state.epoch.timed
                or not state.epoch.options_exposed):
            return
        lead_open = (state.player.position() >= state.player.decision_open_at
                     or state.player.status in ("READY", "WAITING_DECISION", "ENDED"))
        if not lead_open:
            return
        state.timed.selection_open = True
        state.timed.deadline_ms = now_ms() + int(state.timed.timeout_seconds * 1000)
        await self._persist(state)
        await self._push(state)
        self._schedule_timed_watchdog(state.id)

    # ==================================================================
    # Branch 生成流水线
    # ==================================================================
    def _spawn_pipeline(self, session_id: str, branch_id: str) -> None:
        task = self._pipeline_tasks.get(branch_id)
        if task and not task.done():
            return  # one running pipeline per branch, including recovery retries
        self._pipeline_tasks[branch_id] = asyncio.get_running_loop().create_task(
            self._run_pipeline(session_id, branch_id))

    async def _phase_sleep(self) -> None:
        await asyncio.sleep(settings.branch_phase_delay_ms / 1000.0)

    async def _set_phase(self, state: SessionState, branch: Branch,
                         status: BranchStatus) -> None:
        branch.status = status
        branch.pipeline_events.append({"at": now_ms(), "status": status.value})
        self._event(state, "branch_phase", PHASE_LABELS.get(status, status.value),
                    branch_id=branch.id, status=status.value)
        await self._persist(state)
        await self._push(state)

    async def _run_pipeline(self, session_id: str, branch_id: str, retried: bool = False) -> None:
        try:
            await self._pipeline_inner(session_id, branch_id, retried)
        except Exception as e:  # noqa: BLE001 — 管线兜底：分支失败，不拖垮会话
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                if state:
                    branch = state.branch(branch_id)
                    if branch and branch.status != BranchStatus.READY:
                        branch.status = BranchStatus.FAILED
                        branch.last_error = str(e)
                        if branch.source in (BranchSource.OPENING, BranchSource.FREE):
                            state.player.status = "FAILED_RECOVERABLE"
                        self._release_budget(state, branch)
                        self._event(state, "branch_failed", f"生成失败：{branch.label}",
                                    branch_id=branch_id, error=str(e))
                        await self._persist(state)
                        await self._maybe_publish(state)
                        await self._push(state)

    async def _pipeline_inner(self, session_id: str, branch_id: str, retried: bool) -> None:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id) if state else None
            if not state or not branch:
                return
            if branch.status not in (BranchStatus.PREDICTED, BranchStatus.RETRYING):
                return
            resume_media = branch.status == BranchStatus.RETRYING and bool(branch.jobs)
            if resume_media:
                await self._set_phase(state, branch, BranchStatus.GENERATING)
            else:
                await self._set_phase(state, branch, BranchStatus.PLANNING)

        if not resume_media:
            await self._phase_sleep()
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                if branch.status != BranchStatus.PLANNING:
                    return
                await self._plan_branch(state, branch)
                await self._set_phase(state, branch, BranchStatus.NARRATIVE)

            await self._phase_sleep()
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                if branch.status != BranchStatus.NARRATIVE:
                    return
                await self._narrate_branch(state, branch)
                if state.text_mode and branch.source in (BranchSource.OPENING, BranchSource.FREE):
                    await self._text_artifact(state, branch)
                    await self._commit_selected(state, branch)
                    return
                await self._set_phase(state, branch, BranchStatus.PRODUCTION)

            await self._phase_sleep()
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                if branch.status != BranchStatus.PRODUCTION:
                    return
                await self._shoot_branch(state, branch)
                if (not settings.pre_generate_recommendation_media
                        and branch.source in (BranchSource.RECOMMENDATION, BranchSource.TIMED)):
                    duration = sum(s.duration for s in branch.shots) or settings.effective_shot_duration
                    branch.artifact = SceneArtifact(
                        id=uid("deferred_scene"), branch_id=branch.id,
                        quality_status="DEFERRED", duration=duration,
                        provenance={"deferred_media": True,
                                    "reason": "recommendation_media_on_demand",
                                    "provider": settings.fal_h3_model})
                    branch.pipeline_events.append({"at": now_ms(), "status": "READY",
                                                   "media": "DEFERRED"})
                    branch.status = BranchStatus.READY
                    branch.ready_at = now_ms()
                    self._event(state, "recommendation_ready_without_media",
                                f"推荐已就绪，等待选择后生成视频：{branch.label}",
                                branch_id=branch.id)
                    await self._persist(state)
                    await self._maybe_publish(state)
                    await self._push(state)
                    return
                await self._set_phase(state, branch, BranchStatus.GENERATING)

        # 问题6：FREE/OPENING 分支进入媒体生成期后，并行跑间奏叙事，
        # 把执行描写补进 outcome.effects，供前端在等待期逐句淡入。
        interstitial: Optional[asyncio.Task] = None
        if not resume_media and branch.source in (BranchSource.FREE, BranchSource.OPENING):
            interstitial = asyncio.get_running_loop().create_task(
                self._interstitial_effects(session_id, branch_id))

        gen_error: Optional[str] = None
        retryable = True
        try:
            if resume_media:
                await self._generate_branch_media(session_id, branch_id, resume=True)
            else:
                await self._generate_branch_media(session_id, branch_id)
        except Exception as e:  # noqa: BLE001
            gen_error = f"{type(e).__name__}: {e}"
            retryable = not branch.jobs and not getattr(e, "submit_uncertain", False) and getattr(e, "kind", "") not in {
                "BILLING_LOCKED", "QUOTA_EXHAUSTED", "AUTH_FAILED",
                "PAID_GENERATION_DISABLED", "INVALID_REQUEST", "CIRCUIT_OPEN", "REFERENCE_UNAVAILABLE",
            }
        finally:
            # Optional text must never delay a completed video or survive a
            # cancelled generation. Do not await a task needing the session lock.
            if interstitial and not interstitial.done():
                interstitial.cancel()
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if branch.status != BranchStatus.GENERATING:
                if interstitial:
                    interstitial.cancel()
                return
            if gen_error:
                if interstitial:
                    interstitial.cancel()
                if not retried and retryable:
                    # 快速重试 1 次：新 job，不沿用半成品
                    branch.status = BranchStatus.RETRYING
                    branch.retry += 1
                    self._event(state, "branch_retry", f"重试生成：{branch.label}",
                                branch_id=branch.id, error=gen_error)
                    await self._persist(state)
                    await self._push(state)
                    self._pipeline_tasks[branch_id] = asyncio.get_running_loop().create_task(
                        self._run_pipeline(session_id, branch_id, retried=True))
                    return
                branch.status = BranchStatus.FAILED
                branch.fail_stage = "GENERATING"
                branch.last_error = gen_error
                self._release_budget(state, branch)
                self._event(state, "branch_failed", f"生成失败：{branch.label}",
                            branch_id=branch.id, error=gen_error)
                await self._persist(state)
                await self._maybe_publish(state)
                if branch.source in (BranchSource.OPENING, BranchSource.FREE):
                    state.player.status = "FAILED_RECOVERABLE"
                await self._persist(state)
                await self._push(state)
                return
            await self._set_phase(state, branch, BranchStatus.ASSEMBLING)

        await self._phase_sleep()
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if branch.status != BranchStatus.ASSEMBLING:
                return
            await self._assemble_branch(state, branch)
            branch.status = BranchStatus.READY
            branch.ready_at = now_ms()
            branch.pipeline_events.append({"at": now_ms(), "status": "READY"})
            spent = settings.effective_shots_per_branch * settings.shot_unit_cost
            state.budget.spent_by_branch[branch.id] = spent
            state.budget.reserved = max(0, state.budget.reserved - spent)
            state.budget.used += spent
            self._event(state, "branch_ready", f"候选已就绪：{branch.label}", branch_id=branch.id)
            await self._persist(state)
            await self._maybe_publish(state)
            if branch.source == BranchSource.OPENING and branch.status == BranchStatus.READY:
                # 首幕是系统启动动作：媒体可播放后自动呈现，不暴露为推荐。
                await self._commit_selected(state, branch)
                return
            # 自由输入分支：玩家已通过输入作出选择，就绪且仍然有效 → 自动选中播放
            if branch.source == BranchSource.FREE \
                    and state.pending_freeform_id == branch.id \
                    and not state.selection_lock:
                state.pending_freeform_id = None
                if self.valid_branch(state, branch):
                    await self._commit_selected(state, branch)
            await self._push(state)

    # ------------------------------------------------------------------
    # 各阶段实现（Provider 调用经 Router，Agent 不直接绑 SDK）
    # ------------------------------------------------------------------
    async def _director_output(self, messages, mechanics, session_id, branch_id=None):
        from .director_output import normalize_director_output, DirectorOutcome, DirectorOutput
        schema = {"outcome": DirectorOutcome.model_json_schema(), "directive": DramaticDirective.model_json_schema()}
        messages = [{"role": "system", "content": "严格返回 JSON {outcome, directive}。outcome 必须含 title 和 text。QUICK_ACK 只用于轻量观察；改变地点、关系、获得重要证据、主动退出或形成结局使用 FULL_BEAT。决定关闭篇章时给 ending（合法结局方向或退出后果），ending 非空必须使用 FULL_BEAT，不得仅用确认文案假装故事已结束。不能改写核心真相。schema: " + json.dumps(schema, ensure_ascii=False)}] + messages
        enabled = [k for k, v in mechanics.items() if isinstance(v, dict) and v.get("enabled")]
        messages[0]["content"] += " 已启用玩法：" + json.dumps(enabled) + "。关系、线索和物品变化用相应 skill_triggers 提案，同一变化只提出一次。target 使用场景中的角色/物品/线索标识，location 使用 locations 字典的键。"
        messages[0]["content"] += (
            ' State operations use dot paths, never JSON Pointer: location, health, fiction_minutes, objects.<id>, relationships.<id>, clues.<id>.'
            ' Example movement: {"op":"set","path":"location","value":"declared_location_id"}.'
            ' Inventory/clue/relationship changes belong in skill_triggers; do not duplicate them in ops.'
            ' Inventory targets must be tangible carried objects, not flags, abstract outcomes, or system identifiers; use natural-language item names.'
            ' Record changed facility conditions under objects, not inventory. Actual movement must include a location set using the declared location ID.'
            ' Never invent possession, evidence or a relationship delta just to populate a field. Explain the observable causal basis in text/evidence.'
            " outcome 必须显式给出 ops、evidence、skill_triggers 三个数组；没有变化时返回空数组。"
            ' FULL_BEAT 时 outcome 另需返回 "effects": 2-4 句逐步展开的执行描写（第 1 句复述玩家动作本身，后续写环境/他人的即时反应），只描写执行过程，不预言本幕最终结局；每句不超过 40 字，只用玩家角色此刻能知道的信息（不得出现未揭示的秘密名词）。QUICK_ACK 时 effects 返回空数组。'
            "如果你决定人物信任改变、发现线索或获得物品，必须在 skill_triggers 给出相应的类型化提案，"
            "不能仅在 text 或 directive.secondary_functions 中描述变化。"
            '关系提案格式：{"skill":"relationship","target":"场景角色ID","value":变化量}；'
            '线索提案格式：{"skill":"clue-system","target":"线索ID","stage":"DISCOVERED"}；'
            '物品提案格式：{"skill":"inventory","target":"物品ID","action":"add"}。'
            "只为已启用的玩法提出与当前行动有因果依据的变化，不为凑齐字段发明事实。"
            "根据recent_canonical_beats承接已经发生的情节，不重复铺垫已经完成的步骤。"
            "本次应裁定玩家行动的具体结果或明确阻碍，不能只写准备执行。"
            "text若写人物实际抵达新地点，ops必须同步location；只有意图或受阻时不移动。"
            "新物品和线索trigger.label必须用玩家语言给出可读名称；不要把内部ID当显示名。"
            "这是行动裁定而不是最终旁白；text控制在200字以内，把预算留给完整的结构化提案与directive。"
        )
        state = self.sessions.get(session_id)
        branch = state.branch(branch_id) if state and branch_id else None
        language = self._branch_language(branch) if branch else read_language_settings()
        messages[0]["content"] += language.text_instruction()
        for attempt in range(2):
            _, rec, resp = await self.router.call_text("director", messages=messages,
                output_contract={"purpose": "director_plan", "media_language": language.model_dump(), "mechanics": mechanics,
                                 "json_schema": DirectorOutput.model_json_schema()}, branch_id=branch_id)
            try:
                result = normalize_director_output(resp.content)
                original = json.loads(resp.content) if resp.content.lstrip().startswith("{") else result
                if original.get("directive", {}).get("target_changes") != result["directive"].get("target_changes"):
                    await tracer.emit("director.schema_repaired", "success", output={"raw_output": resp.content, "normalized": result["directive"]},
                        provider=rec.selected or "", model=resp.model, session_id=session_id, branch_id=branch_id)
                return result, rec
            except (ValueError, TypeError) as error:
                await tracer.emit("director.schema", "failed", input_={"attempt": attempt + 1},
                    output={"error": str(error), "raw_output": resp.content}, provider=rec.selected or "",
                    model=resp.model, session_id=session_id, branch_id=branch_id)
                if attempt:
                    raise
                # A truncated draft can consume all remaining local context.
                # Retry against the original authoritative input, never append
                # an incomplete model draft as new story evidence.
                messages = messages + [{"role": "user", "content":
                    "上一稿格式无效。请根据原始输入重新返回完整且简洁的JSON，不增加原始输入之外的事实；"
                    "text控制在200字以内。校验错误：" + str(error)[:500]}]

    async def _plan_branch(self, state: SessionState, branch: Branch) -> None:
        if branch.source == BranchSource.OPENING:
            mechanics = state.scenario_snapshot.get("mechanics", {})
            content, rec = await self._director_output(
                [{"role": "user", "content": "raw_player_input: opening\n"
                  "为这个故事设计第一幕：建立当前地点、实际在场人物与核心冲突，给玩家留下行动空间。"
                  "这是开始展示已发布的故事，不是玩家已完成的行动：不得增加物品、线索、关系或揭露尚未知晓的秘密，"
                  "不得提前形成结局；ops、evidence、skill_triggers 必须为空，ending 必须为 null。\n"
                  "遵守已确认 authored_anchors 中的开场安排与人物出场方式；"
                  "远程或广播人物不能无原因改为现场出现。player 指定玩家身份，不得替换或遗漏。"
                  f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}"}],
                mechanics, state.id, branch.id)
            outcome = content.get("outcome") or {}
            directive = content.get("directive") or {}
            if outcome.get("ops") or outcome.get("evidence") or outcome.get("skill_triggers") or outcome.get("ending"):
                raise EngineError("Opening Director attempted an unauthorized state change")
            branch.directive = DramaticDirective(
                id=uid("dir"), primary_function=directive.get("primary_function", "ESTABLISH_OPENING"),
                player_input=branch.label,
                secondary_functions=directive.get("secondary_functions", []),
                target_changes=directive.get("target_changes", []), avoid=directive.get("avoid", []),
                hard_constraints=[*directive.get("hard_constraints", []), "不修改正式世界状态", "建立人物、地点与核心冲突"])
            branch.outcome = OutcomeSpec(
                title=outcome["title"], text=outcome["text"],
                ops=[], evidence=[], kind="opening")
            branch.context = self.build_context(state, directive)
            branch.packet = self._build_scene_packet(state, branch)
            branch.routes.append(rec)
            await tracer.emit("director.plan", "success", input_={"label": branch.label, "opening": True},
                              output={"directive": branch.directive.model_dump(), "outcome": branch.outcome.model_dump(),
                                  "skill_decisions": branch.skill_decisions},
                              provider=rec.selected or "", model=rec.model or "",
                              session_id=state.id, branch_id=branch.id)
            return
        mechanics = state.scenario_snapshot.get("mechanics", {})
        if branch.source == BranchSource.FALLBACK and branch.outcome is not None:
            # 确定性超时结果：不经过 Director 生成，直接构建提交工件
            branch.directive = DramaticDirective(id=uid("dir"), player_input=branch.label)
            branch.state_patch_proposal = None
            branch.drama_patch_proposal = DramaPatchProposal(
                proposal_id=uid("dprop"), scope="CANONICAL_CANDIDATE",
                base_revision=state.drama.revision, source=f"branch:{branch.id}",
                operations=self._drama_ops_for(state, branch),
                idempotency_key=f"dcommit:{branch.id}")
            branch.packet = self._build_scene_packet(state, branch)
            return
        # 期望输出 schema 注入 prompt（真实 LLM 需要显式契约才知道产 skill_triggers）
        mech_ids = [k for k, v in (mechanics or {}).items()
                    if isinstance(v, dict) and v.get("enabled", True)] or \
                   ["relationship", "clue-system", "inventory"]
        schema_hint = (
            "返回 JSON：{\"outcome\": {\"title\": str, \"text\": str, "
            "\"ops\": [{\"op\": \"set|increment|addItem|removeItem|inspect\", "
            "\"path\": str, \"value\": any}], \"evidence\": [str], "
            "\"ending\": str|null, \"kind\": str, "
            "\"skill_triggers\": [{\"skill\": \"" + "|".join(mech_ids) + "\", "
            "\"target\": str, \"action\": \"add|remove\", \"stage\": "
            "\"DISCOVERED|VERIFIED|USED\", \"value\": int}]}, "
            "\"directive\": {\"primary_function\": str, \"secondary_functions\": [str], "
            "\"target_changes\": [{\"description\": str}], \"hard_constraints\": [str], \"avoid\": [str]}}。"
            "skill_triggers 仅在玩家行动明确触发玩法机制时给出（如获得物品→inventory、"
            "发现线索→clue-system、关心角色→relationship）；不触发则为空数组。")
        if branch.source == BranchSource.FREE and branch.director_result:
            content = branch.director_result
            rec = branch.routes[-1]
        else:
            content, rec = await self._director_output(
                [{"role": "user", "content":
                  f"raw_player_input: {branch.label}\n"
                  f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}\n{schema_hint}"}],
                mechanics, state.id, branch.id)
        outcome = content.get("outcome") or {}
        adjudication = await self._arbitrate_mechanics(state, branch, content)
        outcome = content.get("outcome") or {}
        branch.director_result = content
        directive_data = content.get("directive") or {}
        branch.directive = DramaticDirective(
            id=uid("dir"),
            primary_function=directive_data.get("primary_function", "RESPOND_TO_PLAYER_ACTION"),
            secondary_functions=directive_data.get("secondary_functions", []),
            target_changes=directive_data.get("target_changes", []),
            hard_constraints=directive_data.get("hard_constraints", []),
            avoid=directive_data.get("avoid", []),
            player_input=branch.label)
        branch.outcome = OutcomeSpec(
            title=outcome.get("title", branch.label),
            text=outcome.get("text", branch.summary),
            ops=_to_patch_ops(outcome.get("ops", [])),
            evidence=outcome.get("evidence", []),
            ending=outcome.get("ending"),
            kind=outcome.get("kind", "investigation"),
            effects=[str(s)[:80] for s in (outcome.get("effects") or [])
                     if isinstance(s, str) and s.strip()][:4])
        branch.summary = branch.summary or branch.outcome.title
        # 问题6：FULL_BEAT 必须有执行描写兜底，保证生成等待期有文字可播。
        if not branch.outcome.effects:
            branch.outcome.effects = [f"你开始{branch.label}。"]
        branch.outcome.ops = _to_patch_ops(adjudication.operations)
        branch.skill_decisions = adjudication.decisions
        for result in adjudication.invocations:
            sid = result["skill_id"]
            await tracer.emit(f"skill.{sid}", "success", input_=result["input"],
                output={"proposal": result["proposal"], "disposition": "proposed_not_committed"},
                session_id=state.id, branch_id=branch.id, trace_id=branch.trace_id,
                skill_id=sid, skill_version=result["skill_version"])
        # 预构建双域 Proposal（提交时刷新 base_version 再校验）
        if branch.outcome.ops:
            branch.state_patch_proposal = StatePatchProposal(
                proposal_id=uid("prop"), base_version=state.world.version,
                base_drama_revision=state.drama.revision,
                source=f"branch:{branch.id}", operations=branch.outcome.ops,
                idempotency_key=f"commit:{branch.id}")
        branch.drama_patch_proposal = DramaPatchProposal(
            proposal_id=uid("dprop"), scope="CANONICAL_CANDIDATE",
            base_revision=state.drama.revision, source=f"branch:{branch.id}",
            operations=self._drama_ops_for(state, branch),
            idempotency_key=f"dcommit:{branch.id}")
        # Reject illegal proposals before any paid media submission. Validation
        # is a copy-only dry run; formal state changes still occur at commit.
        if branch.state_patch_proposal:
            state_manager.validate(state.world, branch.state_patch_proposal, state.committed_keys,
                drama_revision=state.drama.revision, locations=_scenario_locations(state) or None)
        branch.context = self.build_context(state, directive_data)
        branch.packet = self._build_scene_packet(state, branch)
        # The revelation boundary exists only after ScenePacket is built.
        branch.outcome.effects = [
            s for s in branch.outcome.effects
            if not self._forbidden_hits(state, branch, s)][:4] or \
            ["正在准备你的行动。"]
        if not branch.routes or branch.routes[-1] != rec:
            branch.routes.append(rec)
        await tracer.emit("turn.context", "success", input_={"world_before": state.world.model_dump(),
            "drama_before": state.drama.model_dump(), "action_semantics": branch.action_semantics,
            "context": self._scenario_brief(state)}, output={"proposal": branch.state_patch_proposal.model_dump() if branch.state_patch_proposal else None},
            session_id=state.id, branch_id=branch.id, trace_id=branch.trace_id)
        await tracer.emit("director.plan", "success", input_={"label": branch.label},
                          output={"directive": branch.directive.model_dump(), "outcome": branch.outcome.model_dump(),
                                  "skill_decisions": branch.skill_decisions},
                          provider=rec.selected or "", model=rec.model or "",
                          session_id=state.id, branch_id=branch.id)

    async def _arbitrate_mechanics(self, state: SessionState, branch: Branch, content: dict):
        """One bounded semantic correction, before Narrative or paid Production."""
        import time
        started = time.perf_counter()
        if not skill_enabled("mechanic-arbitration"):
            raise EngineError("Mechanic arbitration is disabled")
        mechanics = state.scenario_snapshot.get("mechanics", {})
        context = mechanic_context(self._scenario_brief(state), state.world.model_dump())
        for attempt in range(2):
            result = arbitrate(content.get("outcome") or {}, context, mechanics, branch.id,
                               state.world.version, state.drama.revision)
            await tracer.emit("skill.mechanic-arbitration", "rejected" if result.errors else "success",
                input_={"why": "reconcile Director mechanic proposals before narrative", "context": context,
                        "triggers": (content.get("outcome") or {}).get("skill_triggers", []), "attempt": attempt},
                output=result.model_dump(), session_id=state.id, branch_id=branch.id, trace_id=branch.trace_id,
                skill_id="mechanic-arbitration", skill_version="1.0.0",
                duration_ms=int((time.perf_counter()-started)*1000))
            if not result.errors:
                return result
            if attempt:
                raise EngineError("Mechanic proposals conflict with recorded state: " + "; ".join(result.errors))
            corrected, route = await self._director_output(
                [{"role": "user", "content":
                    f"raw_player_input: {branch.intent.action or branch.label}\n"
                    f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}\n"
                    f"action_semantics: {json.dumps(branch.action_semantics, ensure_ascii=False)}\n"
                    + MECHANIC_REPAIR_POLICY + json.dumps(result.errors, ensure_ascii=False)}], mechanics, state.id, branch.id)
            content.clear(); content.update(corrected)
            branch.routes.append(route)

    def _build_scene_packet(self, state: SessionState, branch: Branch) -> ScenePacket:
        """ScenePacket（FR-068）：Narrative 的最小授权上下文。

        allowed_revelations 之外的秘密不进包；forbidden 清单只用于输出校验。
        """
        chars = {c.get("id"): c for c in state.scenario_snapshot.get("characters", [])}
        revealed = [k for k, v in state.world.truth.items() if v]
        allowed = list(branch.outcome.evidence) if branch.outcome else []
        allowed_set = set(allowed) | set(revealed)
        forbidden = [k for k in state.world.truth if k not in allowed_set]
        return ScenePacket(
            branch_id=branch.id,
            beat=branch.outcome.title if branch.outcome else branch.label,
            dramatic_function=(branch.directive.primary_function
                               if branch.directive else "RESPOND_TO_PLAYER_ACTION"),
            character_views={
                cid: {"personality": c.get("personality", ""),
                      "emotion": "克制",
                      "knows": c.get("knowledge", "")}
                for cid, c in chars.items() if cid and cid != "player"},
            scene_truth=revealed,
            allowed_revelations=allowed,
            forbidden_revelations=forbidden,
            relationship_context=dict(state.world.relationships),
            known_state={"location": state.world.location,
                         "location_name": _scenario_location_names(state).get(state.world.location, state.world.location),
                         "inventory": list(state.world.inventory),
                         "clues": dict(state.world.clues),
                         "knowledge": list(state.world.knowledge)},
            authorized_changes=[op.model_dump(mode="json") for op in branch.state_patch_proposal.operations]
                if branch.state_patch_proposal else [],
            style={"tone": state.scenario_snapshot.get("tone", ""),
                   "genre": state.scenario_snapshot.get("genre", "")})

    def _forbidden_hits(self, state: SessionState, branch: Branch, text: str) -> list[str]:
        """泄密校验：未授权真相的标志性短语不得出现在叙事正文（AT-48）。"""
        if not branch.packet or not branch.packet.forbidden_revelations:
            return []
        truth_model = state.scenario_snapshot.get("drama", {}).get("truth_model", "")
        values: dict[str, str] = {}
        for line in truth_model.splitlines():
            if "：" in line:
                k, v = line.split("：", 1)
                values[k.strip()] = v.strip()
        hits: list[str] = []
        import re as _re
        # Public names may be mentioned without disclosing the facts attached
        # to them. English names otherwise cross the six-character threshold.
        public_names = {
            word.casefold()
            for character in state.scenario_snapshot.get("characters", [])
            for field in ("name", "identity")
            for word in _re.findall(r"[A-Za-z]+", character.get(field, "") or "")
        }
        for key in branch.packet.forbidden_revelations:
            value = values.get(key, "")
            for seg in _re.split(r"[，。；、,.;！？\s]+", value):
                seg = seg.strip()
                # ≥6 字才视为泄密特征片段：短片段（如角色名 "Alice"、地名）会出现在
                # 任何正常叙事里，阈值过低会把合法文本误判为泄密（G07 泛化后暴露）。
                if len(seg) >= 6 and seg.casefold() not in public_names and seg in text:
                    hits.append(f"{key}→{seg}")
        return hits

    def _drama_ops_for(self, state: SessionState, branch: Branch) -> list[dict]:
        ops: list[dict] = []
        for f in state.drama.foreshadows:
            if f.status.value in ("PROPOSED", "PLANTED"):
                ops.append({"op": "advance_foreshadow", "entry_id": f.id, "to": "PLANTED"
                            if f.status.value == "PROPOSED" else "REINFORCED"})
                break
        ending = branch.outcome.ending if branch.outcome else None
        ops.append({"op": "set_phase",
                    "phase": "RESOLUTION" if ending else "ESCALATION",
                    "reason": f"branch {branch.id}"})
        ops.append({"op": "record_progress",
                    "progress": {"branch": branch.id, "label": branch.label,
                                 "at": now_ms()}})
        return ops

    @staticmethod
    def _branch_language(branch: Branch):
        if branch.media_language is None:
            branch.media_language = read_language_settings()
        return branch.media_language

    async def _narrate_branch(self, state: SessionState, branch: Branch) -> None:
        language = self._branch_language(branch)
        outcome = branch.outcome
        characters = state.scenario_snapshot.get("characters", [])
        proper_names = tuple(name for c in characters for name in (
            str(c.get("identity") or ""), str(c.get("name") or ""),
            *re.findall(r"[A-Za-z][A-Za-z .'-]{2,}", str(c.get("identity") or ""))))
        base_messages = [{"role": "system", "content": "只返回 JSON {title:字符串,text:本幕短叙事,caption:简短字幕,dialogue:[{speaker:角色ID,line:台词}]}。"
                         "caption 必须是本幕内容的字幕，不可复制行动建议。dialogue 只包含本幕确实说出的简短台词，"
                         "不得为凑台词添加新的剧情事实；无台词返回空数组。speaker 必须使用场景中的角色ID。"
                         "旁白无 speaker，不泄露授权范围以外的信息，不替玩家做下一步决定。"
                         + CAUSAL_NARRATIVE_POLICY + language.text_instruction() + "允许的角色：" + json.dumps(
                             [{"id": c.get("id"), "identity": c.get("identity", "")} for c in characters], ensure_ascii=False)
                         + "场景包：" + json.dumps(branch.packet.model_dump(exclude={"forbidden_revelations"}) if branch.packet else {}, ensure_ascii=False)}, {"role": "user", "content":
                          f"scene_title: {outcome.title if outcome else branch.label}\n"
                          f"scene_text: {outcome.text if outcome else branch.summary}\n"
                          f"action_summary (not a subtitle): {branch.summary}"}]
        narrative_brief = {
            "player": {"id": state.scenario_snapshot.get("player_character")},
            "npcs": [{"id": c.get("id"), "identity": c.get("identity")} for c in characters
                     if c.get("id") != state.scenario_snapshot.get("player_character")],
        }
        # Adversarial offline fixture only; secrets never enter live Narrative.
        if settings.provider_mode == "mock":
            from ..providers.fixtures import get as fixture_settings
            if fixture_settings().get("leak_secret"):
                narrative_brief["truth_model"] = state.scenario_snapshot.get("drama", {}).get("truth_model", "")
        leaked: list[str] = []
        resp = None
        rec = None
        for attempt in (0, 1):
            # attempt 1 = 泄密后重写：不告知秘密内容，只收紧授权范围
            messages = base_messages if attempt == 0 else base_messages + [
                {"role": "user", "content":
                 "上一稿包含了超出本幕授权范围的信息。请只描写玩家此刻可观察到的内容，"
                 "不要解释任何未揭示的背景。"}]
            _, rec, resp = await self.router.call_text(
                "narrative", messages=messages,
                output_contract={"purpose": "narrative_beat", "media_language": language.model_dump(), "context": branch.context,
                                 "packet": branch.packet.model_dump(mode="json", exclude={"forbidden_revelations"})
                                 if branch.packet else {}, "scenario_brief": narrative_brief},
                branch_id=branch.id)
            from .structured_output import decode_object
            try:
                content = decode_object(resp.content)
                text = content.get("text") or content.get("scene_text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Narrative output requires non-empty text")
                caption = content.get("caption")
                if not isinstance(caption, str) or not caption.strip():
                    raise ValueError("Narrative output requires a caption in the selected subtitle language")
                if obvious_language_mismatch(caption, language.subtitle_language, proper_names):
                    raise ValueError("Narrative caption uses the wrong subtitle language")
                dialogue = content.get("dialogue", [])
                known_speakers = {c.get("id") for c in state.scenario_snapshot.get("characters", [])}
                if not isinstance(dialogue, list) or any(
                    not isinstance(line, dict) or not isinstance(line.get("line"), str)
                    or not line["line"].strip() or not isinstance(line.get("speaker"), str)
                    or line["speaker"] not in known_speakers for line in dialogue
                ):
                    raise ValueError("Narrative dialogue requires known speakers and non-empty lines")
                if any(obvious_language_mismatch(line["line"], language.video_language, proper_names) for line in dialogue):
                    raise ValueError("Narrative dialogue uses the wrong video language")
            except ValueError as error:
                await tracer.emit("narrative.schema", "failed", output={"error": str(error), "raw_output": resp.content, "attempt": attempt + 1},
                                  provider=rec.selected or "", model=resp.model, session_id=state.id, branch_id=branch.id)
                if attempt:
                    branch.fail_stage = "NARRATIVE"
                    raise EngineError("Narrative output failed schema validation") from error
                base_messages += [{"role": "user", "content": "上次输出字段无效。请返回完整 JSON {title,text,caption,dialogue}；text/caption不能为空，dialogue为数组且speaker必须来自场景。遵守指定语言与授权信息范围。"}]
                continue
            leaked = self._forbidden_hits(state, branch, "\n".join([text, caption, *[line["line"] for line in dialogue]]))
            if not leaked:
                focus = content.get("visual_focus", "")
                branch.causal_presentation = {"visual_focus": focus[:300] if isinstance(focus, str) else ""}
                branch.narrative = text
                branch.caption = caption
                branch.dialogue = [{"speaker": line["speaker"], "line": line["line"]} for line in dialogue]
                branch.caption_speaker = ""
                if dialogue and isinstance(dialogue[0], dict) and dialogue[0].get("line") == branch.caption:
                    branch.caption_speaker = str(dialogue[0].get("speaker") or "")
                break
            self._event(state, "narrative_blocked",
                        "叙事越权揭示未授权真相，已拦截" if attempt == 0
                        else "叙事重写后仍越权，分支失败",
                        branch_id=branch.id, hits=leaked)
        if leaked:
            # 泄密拒绝：分支失败（schema_failure 语义），不进入媒体生成
            branch.fail_stage = "NARRATIVE"
            raise EngineError(f"narrative leak rejected: {leaked[0]}")
        branch.routes.append(rec)
        await tracer.emit("narrative.beat", "success",
                          input_={"packet": branch.packet.model_dump(exclude={"forbidden_revelations"}) if branch.packet else {},
                                  "action_semantics": branch.action_semantics},
                          output={"text": branch.narrative, "caption": branch.caption,
                                  "visual_focus": branch.causal_presentation.get("visual_focus"),
                                  "chars": len(branch.narrative), "media_language": language.model_dump(), "dialogue_count": len(branch.dialogue)},
                          provider=rec.selected or "", session_id=state.id, branch_id=branch.id)

    async def _interstitial_effects(self, session_id: str, branch_id: str) -> None:
        """间奏叙事（问题6）：媒体 GENERATING 期间并行补写执行描写。

        Director 在 PLANNING 已给出 2-4 句 effects 兜底；这里用 narrative 低预算
        再补 2-3 句"环境/他人的即时反应"继续覆盖等待时间。全程 best-effort：
        任何失败静默降级（锁内状态可能已推进），绝不阻塞主 pipeline。
        """
        try:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id) if state else None
                if not state or not branch or branch.status != BranchStatus.GENERATING:
                    return
                if not branch.outcome:
                    return
                existing = list(branch.outcome.effects)
                packet = branch.packet.model_dump(exclude={"forbidden_revelations"}) if branch.packet else {}
            language = self._branch_language(branch)
            _, rec, resp = await self.router.call_text(
                "narrative",
                messages=[
                    {"role": "system", "content":
                     "只返回 JSON {lines:[字符串,...]}。为玩家正在执行的动作补 2-3 句"
                     "环境/他人的即时反应（每句不超过 40 字），延续已有描写的氛围，"
                     "只写执行过程中可观察到的细节，不预言本幕结局，不引入新的事实或"
                     "未揭示的秘密名词。"
                     + language.text_instruction()
                     + "场景包：" + json.dumps(packet, ensure_ascii=False)},
                    {"role": "user", "content":
                     f"action: {branch.label}\n"
                     f"already_written: {json.dumps(existing, ensure_ascii=False)}"}],
                output_contract={"purpose": "interstitial_effects",
                                 "media_language": language.model_dump()},
                branch_id=branch_id)
            from .structured_output import decode_object
            content = decode_object(resp.content)
            fresh = [str(s)[:80] for s in (content.get("lines") or [])
                     if isinstance(s, str) and s.strip()]
            if not fresh:
                return
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id) if state else None
                if not state or not branch or not branch.outcome \
                        or branch.status not in (BranchStatus.GENERATING, BranchStatus.ASSEMBLING):
                    return
                merged = list(branch.outcome.effects)
                for s in fresh:
                    if s not in merged and not self._forbidden_hits(state, branch, s):
                        merged.append(s)
                branch.outcome.effects = merged[:6]
                await self._persist(state)
                await self._push(state)
            await tracer.emit("narrative.interstitial", "success",
                              output={"added": len(fresh),
                                      "total": len(branch.outcome.effects)},
                              provider=rec.selected or "", session_id=session_id,
                              branch_id=branch_id)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001  间奏是增强项，失败不阻碍主流程
            await tracer.emit("narrative.interstitial", "failed",
                              output={"error": str(error)},
                              provider="runtime", session_id=session_id,
                              branch_id=branch_id)

    def _bound_references(self, state: SessionState, cast: list[str] | None = None) -> list[dict]:
        """Select balanced, cast-scoped references within real provider limits."""
        if not skill_enabled("visual-continuity"):
            return []
        characters = {c.get("id") for c in state.scenario_snapshot.get("characters", []) if c.get("id")}
        active = list(dict.fromkeys(cast if cast is not None else [
            c.get("id") for c in state.scenario_snapshot.get("characters", []) if c.get("id")]))
        order = {"front": 0, "identity": 0, "wardrobe": 1, "three_quarter": 2,
                 "pose": 3, "side": 4, "full_front": 5, "full_side": 6, "other": 7}
        buckets: dict[str, list[dict]] = {cid: [] for cid in active}
        audio, video, environment = [], [], []
        seen_paths: set[tuple[str, str]] = set()
        for asset in state.asset_manifest:
            entity = asset.get("entity") or asset.get("binding") or ""
            if entity in characters and entity not in active:
                continue
            role = asset.get("role") or "reference"
            kind = "audio" if role == "voice" or asset.get("type") in ("audio", "voice") else \
                   "video" if role == "motion" or asset.get("type") == "video" else "image"
            if not asset.get("path"):
                continue
            dedupe_key = (kind, asset["path"])
            if dedupe_key in seen_paths:
                continue
            seen_paths.add(dedupe_key)
            ref = {"asset_id": asset.get("id"), "name": asset.get("name", ""), "role": role,
                   "entity": entity, "path": asset["path"], "version": asset.get("version", 1),
                   "type": kind, "character_snapshot_id": asset.get("character_snapshot_id")}
            if kind == "audio":
                audio.append(ref)
            elif kind == "video":
                video.append(ref)
            elif entity in buckets:
                buckets[entity].append(ref)
            elif not entity and role in ("scene", "background", "location", "reference"):
                environment.append(ref)
        from ..providers.real import FalH3MaxProvider
        limits = FalH3MaxProvider.REFERENCE_LIMITS
        image_limit = min(limits["image"], settings.max_test_reference_images) if settings.developer_test_override_enabled else limits["image"]
        video_limit = min(limits["video"], settings.max_test_reference_videos) if settings.developer_test_override_enabled else limits["video"]
        for bucket in buckets.values():
            bucket.sort(key=lambda ref: order.get(ref["role"], 9))
        # Round-robin ensures a third actor gets identity coverage before a
        # first actor spends the whole provider allowance on four views.
        images = [bucket[index] for index in range(4) for bucket in buckets.values() if len(bucket) > index]
        selected_images = (images + environment)[:max(0, image_limit)]
        extras = [group[index] for index in range(max(limits["audio"], video_limit))
                  for group in (audio[:limits["audio"]], video[:max(0, video_limit)]) if len(group) > index]
        return selected_images + extras[:max(0, limits["mixed"] - len(selected_images))]

    def _shot_policy(self, branch: Branch) -> dict:
        count = max(1, int(settings.effective_shots_per_branch))
        maximum = float(settings.max_video_shot_duration)
        if settings.developer_test_override_enabled:
            maximum = min(maximum, float(settings.developer_test_shot_duration))
        special = branch.source == BranchSource.OPENING or bool(branch.outcome and branch.outcome.ending)
        target = (settings.opening_shot_duration if branch.source == BranchSource.OPENING else
                  settings.ending_shot_duration if branch.outcome and branch.outcome.ending else
                  settings.effective_shot_duration)
        if not math.isfinite(maximum) or maximum <= 0:
            raise EngineError("Video duration limit must be positive and finite")
        minimum = min(8.0, maximum) if special else min(1.0, maximum)
        return {"count": 1 if special else count, "minimum": minimum, "maximum": maximum,
                "target": min(maximum, max(minimum, float(target))),
                "developer_test_override": settings.developer_test_override_enabled}

    async def _shoot_branch(self, state: SessionState, branch: Branch) -> None:
        language = self._branch_language(branch)
        policy = self._shot_policy(branch)
        characters = state.scenario_snapshot.get("characters", [])
        cast_ids = sorted({c["id"] for c in characters if c.get("id")})
        cast_schema = {"type": "array", "items": {"type": "string", "enum": cast_ids}} if cast_ids else {"type": "array", "maxItems": 0}
        schema = {
            "type": "object", "additionalProperties": False, "required": ["shots"],
            "properties": {"shots": {
                "type": "array", "minItems": policy["count"], "maxItems": policy["count"],
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["title", "prompt", "subtitle", "duration", "cast", "dialogue_indices"],
                    "properties": {
                        "title": {"type": "string"}, "prompt": {"type": "string", "minLength": 1},
                        "subtitle": {"type": "string"}, "cast": cast_schema,
                        "dialogue_indices": {"type": "array", "items": {"type": "integer", "enum": list(range(len(branch.dialogue)))}} if branch.dialogue else {"type": "array", "maxItems": 0},
                        "duration": {"type": "number", "minimum": policy["minimum"], "maximum": policy["maximum"]},
                    },
                },
            }},
        }
        _, rec, resp = await self.router.call_text(
            "production",
            messages=[{"role": "system", "content":
                f"返回 JSON，包含 shots 数组，必须正好 {policy['count']} 个镜头。每个 title/prompt/subtitle 为字符串，"
                f"duration 目标 {policy['target']} 秒，允许 {policy['minimum']} 至 {policy['maximum']} 秒。"
                "每个镜头必须给 cast:[角色ID]，只包含画面中真正可见的角色；广播、画外音不算可见角色。"
                f"cast 中每一项只能逐字使用这些 ID，禁止用姓名或自创缩写替代：{json.dumps(cast_ids)}。"
                "dialogue_indices 选择该镜头要使用的授权台词序号(从0开始)；不说话返回空数组，"
                "跨镜头不得重复同一句台词，不得虚构或翻译台词。prompt只描述画面与音效，不包含新台词或文字字幕。"
                "每个短镜头只呈现visual_focus中的一个核心可见动作。复杂行动的完整结果由正文承接；"
                "不得用无关走动代替玩家行动，不得增加地点跳转或新决定。"
                + language.text_instruction() + "prompt 使用完整具体影视描述，人物与场景保持连续。角色：" + json.dumps(
                    [{k: c.get(k, "") for k in ("id", "identity", "appearance", "visual_state")} for c in characters], ensure_ascii=False)},
                {"role": "user", "content": f"raw_player_input: {branch.label}\n"
                 f"scene_title: {branch.outcome.title if branch.outcome else branch.label}\n"
                 f"scene_text: {branch.narrative}\n"
                 f"visual_focus: {branch.causal_presentation.get('visual_focus') or (branch.outcome.title if branch.outcome else branch.label)}\n"
                 f"approved_caption: {branch.caption}\n"
                 f"authorized_dialogue: {json.dumps(branch.dialogue, ensure_ascii=False)}"}],
            output_contract={"purpose": "production_shots", "media_language": language.model_dump(), "shot_policy": policy, "json_schema": schema}, branch_id=branch.id)
        from .structured_output import decode_object
        content = decode_object(resp.content)
        raw_shots = content.get("shots")
        if not isinstance(raw_shots, list) or len(raw_shots) != policy["count"]:
            await tracer.emit("production.shots", "rejected", output={"reason": "shot_count_mismatch",
                "expected": policy["count"], "actual": len(raw_shots) if isinstance(raw_shots, list) else None},
                provider=rec.selected or "", session_id=state.id, branch_id=branch.id)
            raise EngineError("Production shot count differs from the approved generation limit")
        known = {c.get("id") for c in characters if c.get("id")}
        character_by_id = {c.get("id"): c for c in characters if c.get("id")}
        visual_identity_cast = {c["id"] for c in characters if c.get("id") and c.get("global_character_id")}
        visual_identity_cast.update(a.get("entity") or a.get("binding") for a in state.asset_manifest
            if a.get("path") and a.get("type", "image") not in ("voice", "audio", "video")
            and a.get("role") not in ("voice", "motion"))
        shots = []
        normalizations = []
        used_dialogue: set[int] = set()
        for index, shot in enumerate(raw_shots):
            if not isinstance(shot, dict):
                raise EngineError("Production returned an invalid shot")
            duration = float(shot.get("duration", policy["target"]))
            if not math.isfinite(duration) or duration <= 0:
                raise EngineError("Production duration must be positive and finite")
            bounded = min(policy["maximum"], max(policy["minimum"], duration))
            if settings.provider_mode != "mock" and getattr(self.router, "profile", RuntimeProfile.AGENT_LOCAL) == RuntimeProfile.AGENT_LOCAL:
                # Fal's duration schema is integer-valued. Keep the planned
                # beat within the approved bounds before paid submission.
                minimum_integer, maximum_integer = math.ceil(policy["minimum"]), math.floor(policy["maximum"])
                if minimum_integer > maximum_integer:
                    raise EngineError("Approved shot duration range contains no Fal-supported integer")
                bounded = min(maximum_integer, max(minimum_integer, math.floor(bounded)))
            if bounded != duration:
                normalizations.append({"shot": index + 1, "requested_duration": duration, "duration": bounded})
            cast = shot.get("cast")
            if not isinstance(cast, list) or any(not isinstance(cid, str) or cid not in known for cid in cast):
                if settings.provider_mode != "mock":
                    await tracer.emit("production.shots", "rejected",
                        output={"reason": "invalid_cast", "cast": cast, "allowed_ids": cast_ids,
                                "raw_output": resp.content},
                        provider=rec.selected or "", model=resp.model,
                        session_id=state.id, branch_id=branch.id)
                    raise EngineError("Production requires a valid explicit shot cast before paid submission")
                cast = list(known)  # Offline fixtures predate cast; never inferred for a paid provider.
            prompt = str(shot.get("prompt") or "")
            # A production model can describe Leon in the prompt but return
            # Victor's ID in `cast`. That would make the resolver send the
            # wrong face/outfit to H3. When unambiguous identity aliases are
            # present, derive the visible cast from the prompt and keep the
            # order in which those identities appear.
            aliases: list[tuple[int, str]] = []
            lowered_prompt = prompt.casefold()
            for character in characters:
                cid = character.get("id")
                if not cid or not character.get("global_character_id"):
                    continue
                identity = str(character.get("identity") or "")
                candidates = [identity]
                candidates.extend(part.strip() for part in re.findall(r"[A-Za-z][A-Za-z .'-]{2,}", identity))
                candidates.extend(re.findall(r"[\u4e00-\u9fff]{2,}", identity))
                hits = [a.casefold() for a in candidates if len(a.strip()) >= 2 and a.casefold() in lowered_prompt]
                if hits:
                    aliases.append((min(lowered_prompt.index(a) for a in hits), cid))
            if aliases:
                mentioned = [cid for _, cid in sorted(aliases)]
                # Put explicit visual identities in prompt order. Preserve
                # any non-visual entity such as T-103 after them.
                cast = mentioned + [cid for cid in cast if cid not in mentioned
                                    and not any(c.get("id") == cid and c.get("global_character_id")
                                                for c in characters)]
            refs = self._bound_references(state, cast)
            covered = {ref["entity"] for ref in refs if ref["type"] == "image"}
            if settings.provider_mode == "live" and any(cid in visual_identity_cast and cid not in covered for cid in cast):
                raise EngineError("A visible character has no image reference within the provider limit")
            text_only_cast = [cid for cid in cast if cid not in covered and cid not in visual_identity_cast]
            if not prompt.strip():
                raise EngineError("Production requires a non-empty shot prompt")
            visual_descriptions = [{"character_id": cid,
                "identity": character_by_id[cid].get("identity", ""),
                "appearance": character_by_id[cid].get("appearance", ""),
                "visual_state": character_by_id[cid].get("visual_state", ""),
                "reference_mode": "text_description" if cid in text_only_cast else "identity_reference"}
                for cid in cast]
            if visual_descriptions:
                prompt += "\nPinned cast appearance and current visual state: " + json.dumps(visual_descriptions, ensure_ascii=False)
            if refs:
                names = {c.get("id"): c.get("identity") or c.get("name") or c.get("id") for c in characters}
                binding_parts = []
                for kind, label in (("image", "Image"), ("audio", "Audio"), ("video", "Video")):
                    for i, ref in enumerate(ref for ref in refs if ref["type"] == kind):
                        binding_parts.append(f"{label} {i + 1}: {ref['entity']} — {names.get(ref['entity'], ref.get('name') or 'environment')} ({ref['role']})")
                binding = "; ".join(binding_parts)
                prompt += "\nReference identity map: " + binding + ". Keep each character's face, body and outfit separate."
            dialogue_indices = shot.get("dialogue_indices", [])
            if not isinstance(dialogue_indices, list) or any(
                type(i) is not int or not 0 <= i < len(branch.dialogue) for i in dialogue_indices
            ):
                raise EngineError("Production contains an invalid authorized dialogue reference")
            if len(set(dialogue_indices)) != len(dialogue_indices) or used_dialogue.intersection(dialogue_indices):
                raise EngineError("Production repeats authorized dialogue across shots")
            used_dialogue.update(dialogue_indices)
            spoken_lines = [{"speaker": character_by_id[line["speaker"]].get("identity") or line["speaker"], "line": line["line"]}
                            for i in dialogue_indices for line in [branch.dialogue[i]]]
            prompt += language.video_instruction(spoken_lines)
            shots.append(ShotPlan(id=f"shot_{index + 1}", index=index + 1,
                title=shot.get("title", f"镜头 {index + 1}"), duration=bounded, trim_end=bounded,
                subtitle=branch.caption if len(raw_shots) == 1 and branch.caption else shot.get("subtitle", ""), prompt=prompt, references=refs,
                params={"cast": list(dict.fromkeys(cast)), "media_language": language.model_dump(), "dialogue_indices": dialogue_indices, "text_only_cast": text_only_cast, "shot_policy": policy,
                        "requested_duration": duration, "normalized_duration": bounded != duration}))
        branch.shots = shots
        branch.references = list({(ref.get("asset_id"), ref.get("entity"), ref.get("role")): ref
                                  for shot in shots for ref in shot.references}.values())
        branch.shot_count = len(shots)
        branch.routes.append(rec)
        await tracer.emit("production.shots", "success", output={"shots": len(shots), "policy": policy, "media_language": language.model_dump(),
            "normalizations": normalizations, "cast": [shot.params["cast"] for shot in shots],
            "text_only_cast": [shot.params["text_only_cast"] for shot in shots]},
            provider=rec.selected or "", session_id=state.id, branch_id=branch.id, skill_id="h3-production")

    async def _generate_branch_media(self, session_id: str, branch_id: str, *, resume: bool = False) -> None:
        if not skill_enabled("h3-production"):
            await tracer.emit("h3-production.blocked", "blocked",
                              output={"reason": "skill disabled"},
                              session_id=session_id, branch_id=branch_id,
                              skill_id="h3-production")
            raise EngineError("生成被阻塞：H3 Production Skill 已禁用（开发者模式可恢复）")
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            shots = [{"id": s.id, "title": s.title, "subtitle": s.subtitle,
                      "duration": s.duration, "references": s.references, "prompt": s.prompt,
                      "params": s.params}
                     for s in branch.shots]
            references = branch.references
            generation_resolution = settings.video_generation_resolution
            generation_aspect = settings.generation_aspect_ratio
            policy = self._shot_policy(branch)
            if len(shots) != policy["count"] or any(not math.isfinite(s["duration"]) or
                    not policy["minimum"] <= s["duration"] <= policy["maximum"] for s in shots):
                raise ProviderError("INVALID_REQUEST", "Shot plan exceeds the approved generation limits")
            if branch.jobs and not resume:
                raise ProviderError("INVALID_REQUEST", "This branch already has submitted media jobs; inspect existing jobs before retrying")
            if any(event.get("event") == "video_submit_uncertain" for event in branch.pipeline_events):
                raise ProviderError("INVALID_REQUEST", "A previous submit may have created a paid job; reconcile its usage record before retrying")
        provider, rec = self.router.video_provider(branch_id, local=self.router.profile == RuntimeProfile.VIDEO_LOCAL)
        # H3 Max reference-to-video requires at least one reference asset. A
        # scenario may intentionally start without assets; in hybrid mode use
        # the explicit Mock fallback for the Opening so the player still gets
        # a playable first scene. Real asset-backed shots remain H3/Sol-H3.
        if (not references and getattr(provider, "name", "") == "h3_max"
                and settings.provider_mode == "hybrid"):
            fallback = self.router.registry.get("mock_video")
            if fallback is not None:
                provider = fallback
                rec = rec.model_copy(update={
                    "selected": "mock_video", "status": "fallback",
                    "reason": [*rec.reason, {"provider": "h3_max", "reason": "no_reference_assets"}],
                    "phase": "video.opening_fallback"})
        # Real providers receive one request per Shot.  The previous code sent
        # the whole ShotPlan as one request, which produced one clip and made a
        # concatenated artifact look like multi-shot generation.
        async def submit_one(shot: dict):
            submitted_at = now_ms()
            prompt = shot.get("prompt") or shot.get("title", "")
            shot_refs = shot.get("references") or []
            if getattr(provider, "name", "") == "h3_max" and not shot_refs:
                raise ProviderError("INVALID_REQUEST", "H3 reference-to-video requires a reference; use text continuation or add an existing asset")
            try:
                handle = await provider.submit({
                    "job_id": f"{branch_id}_{shot['id']}", "shots": [shot],
                    "references": shot_refs, "prompt": prompt,
                    "resolution": generation_resolution,
                    "aspect_ratio": generation_aspect})
            except Exception as error:
                if getattr(error, "submit_uncertain", False):
                    async with self._lock(session_id):
                        current = await self.load_session(session_id)
                        current.branch(branch_id).pipeline_events.append({"event": "video_submit_uncertain",
                            "shot_id": shot["id"], "provider": rec.selected, "submitted_at": submitted_at,
                            "usage_id": getattr(error, "usage_id", None), "error_class": getattr(error, "kind", "")})
                        await self._persist(current)
                await tracer.emit("video.submit", "failed", input_={"shot_id": shot["id"], "prompt": prompt, "references": shot_refs, "media_language": shot.get("params", {}).get("media_language")},
                    output={"error": repr(error), "submitted_at": submitted_at}, provider=rec.selected or "",
                    session_id=session_id, branch_id=branch_id)
                raise
            await tracer.emit("video.submit", "success", input_={"shot_id": shot["id"], "prompt": prompt, "references": shot_refs, "media_language": shot.get("params", {}).get("media_language")},
                output={"provider_job_id": handle.provider_job_id, "submitted_at": submitted_at,
                        "reference_transport": handle.metadata.get("reference_transport", [])}, provider=rec.selected or "",
                session_id=session_id, branch_id=branch_id)
            async with self._lock(session_id):
                current = await self.load_session(session_id)
                current_branch = current.branch(branch_id)
                current_branch.jobs.append(handle.provider_job_id)
                current_branch.pipeline_events.append({"event": "video_submit", "shot_id": shot["id"],
                    "provider": rec.selected, "provider_job_id": handle.provider_job_id, "submitted_at": submitted_at,
                    "handle": handle.model_dump(mode="json"),
                    "reference_transport": handle.metadata.get("reference_transport", [])})
                await self._persist(current)
            return shot, handle, submitted_at, prompt
        if resume:
            from ..providers.base import VideoJobHandle
            submitted = []
            for shot in shots:
                event = next((event for event in reversed(branch.pipeline_events)
                              if event.get("event") == "video_submit" and event.get("shot_id") == shot["id"]
                              and event.get("provider_job_id") in branch.jobs), None)
                if not event or event.get("provider") != provider.name:
                    raise ProviderError("INVALID_REQUEST", "Existing media job cannot be safely recovered; no new job submitted")
                if event.get("handle"):
                    handle = VideoJobHandle(**event["handle"])
                elif getattr(provider, "recover_handle", None):
                    handle = provider.recover_handle(event["provider_job_id"])
                    handle.metadata["reference_transport"] = event.get("reference_transport", [])
                else:
                    raise ProviderError("INVALID_REQUEST", "Existing provider job has no recovery handle; no new job submitted")
                submitted.append((shot, handle, event["submitted_at"], shot.get("prompt") or shot.get("title", "")))
            await tracer.emit("video.resume", "success", output={"jobs": [item[1].provider_job_id for item in submitted],
                "new_submits": 0}, provider=provider.name, session_id=session_id, branch_id=branch_id)
        else:
            submitted = await asyncio.gather(*(submit_one(shot) for shot in shots))
        clips: list[str] = []
        shot_provenance: list[dict] = []
        handles = []
        for shot, handle, submitted_at, prompt in submitted:
            handles.append(handle)
            for _ in range(240):
                result = await provider.status(handle)
                if result.status == "READY":
                    shot_clips = (result.raw or {}).get("clips", [])
                    clips.extend(shot_clips)
                    actual_duration = (self._ffprobe_duration(Path(shot_clips[0]))
                                       if shot_clips else None)
                    shot_provenance.append({"shot_id": shot["id"],
                                            "provider": handle.provider,
                                            "provider_job_id": handle.provider_job_id,
                                            "request_id": handle.provider_job_id,
                                            "prompt": prompt,
                                            "media_language": shot.get("params", {}).get("media_language"),
                                            "references": shot.get("references", []),
                                            "reference_transport": handle.metadata.get("reference_transport", []),
                                            "cast": shot.get("params", {}).get("cast", []),
                                            "text_only_cast": shot.get("params", {}).get("text_only_cast", []),
                                            "resolution": generation_resolution,
                                            "aspect_ratio": generation_aspect,
                                            "submitted_at": submitted_at,
                                            "completed_at": now_ms(),
                                            "output_clips": shot_clips,
                                            "output_clip": shot_clips[0] if shot_clips else None,
                                            "clips": shot_clips,
                                            "duration": actual_duration or float(shot.get("duration") or 0),
                                            "declared_duration": float(shot.get("duration") or 0),
                                            "status": result.status,
                                            "timings": result.timings,
                                            "provider_raw": result.raw})
                    break
                if result.status == "FAILED":
                    raise EngineError(f"video generation failed ({shot['id']}): {result.error}")
                await asyncio.sleep(0.5)
            else:
                raise EngineError(f"video generation timeout ({shot['id']})")
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            branch.media_clips = clips
            branch.jobs = [h.provider_job_id for h in handles]
            branch.pipeline_events.append({"event": "real_multi_shot_jobs",
                                           "shots": shot_provenance})
            branch.routes.append(rec.model_copy(update={"phase": "video.multi_shot"}))
            await tracer.emit("video.generate", "success",
                              output={"clips": len(clips), "jobs": len(handles),
                                      "shot_ids": [s["id"] for s in shots],
                                      "jobs_provenance": shot_provenance},
                              provider=rec.selected or "",
                              session_id=session_id, branch_id=branch_id)
            await self._persist(state)

    async def _text_artifact(self, state, branch):
        """Explicit user-selected text presentation. Never a video recommendation."""
        if not branch.narrative.strip() or not branch.outcome:
            raise EngineError("这个行动尚未形成有效文字结果，请修改或重试。")
        folder = settings.media_path / "text"
        folder.mkdir(parents=True, exist_ok=True)
        artifact_id = uid("text_scene")
        path = folder / f"{artifact_id}.txt"
        path.write_text(branch.narrative, encoding="utf-8")
        branch.artifact = SceneArtifact(id=artifact_id, branch_id=branch.id, media_type="text",
            assembled_path=f"text/{artifact_id}.txt", quality_status="READY", duration=0,
            provenance={"presentation": "user_requested_text", "video_error": branch.last_error,
                        "providers": [r.selected for r in branch.routes], "video_jobs": list(branch.jobs)})
        branch.status = BranchStatus.READY
        self._release_budget(state, branch)
        await tracer.emit("presentation.text", "success", output={"artifact_id": artifact_id, "path": str(path), "video_generated": False},
                          session_id=state.id, branch_id=branch.id)

    async def _assemble_branch(self, state: SessionState, branch: Branch) -> None:
        """确定性装配：FFmpeg concat → 受控媒体目录（Assembly 不走生成模型）。"""
        if not skill_enabled("video-assembly"):
            await tracer.emit("video-assembly.blocked", "blocked",
                              output={"reason": "skill disabled"},
                              session_id=state.id, branch_id=branch.id,
                              skill_id="video-assembly")
            raise EngineError("装配被阻塞：Video Assembly Skill 已禁用（开发者模式可恢复）")
        scene_id = uid("scene")
        out_dir = settings.media_path / "scenes"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{scene_id}.mp4"
        clips = [Path(c) for c in branch.media_clips if Path(c).exists()]
        clip_durations = [self._ffprobe_duration(c) for c in clips]
        clip_durations = [d for d in clip_durations if d is not None]
        await asyncio.get_running_loop().run_in_executor(
            None, self._ffmpeg_concat, clips, target)
        shot_provenance = [e.get("shots", []) for e in branch.pipeline_events
                           if e.get("event") == "real_multi_shot_jobs"]
        branch.artifact = SceneArtifact(
            id=scene_id, branch_id=branch.id,
            clip_refs=[c.name for c in clips],
            assembled_path=f"scenes/{scene_id}.mp4", quality_status="READY",
            provenance={"assembler": "ffmpeg-concat",
                        "media_language": branch.media_language.model_dump() if branch.media_language else None,
                        "providers": [r.selected for r in branch.routes],
                        "jobs": branch.jobs,
                        "shot_provenance": shot_provenance,
                        "concat_inputs": [str(c) for c in clips],
                        "clip_durations": clip_durations,
                        "final_output": str(target),
                        "final_duration": self._ffprobe_duration(target)},
            duration=self._ffprobe_duration(target) or sum(clip_durations) or
                    sum(s.duration for s in branch.shots) or settings.effective_shot_duration)
        await tracer.emit("assembly.concat", "success",
                          output={"scene": scene_id, "clips": len(clips)},
                          provider="runtime", session_id=state.id, branch_id=branch.id)

    @staticmethod
    def _ffmpeg_concat(clips: list[Path], target: Path) -> None:
        if not clips:
            raise EngineError("no clips to assemble")
        if len(clips) == 1:
            shutil.copyfile(clips[0], target)
            return
        list_file = target.with_suffix(".txt")
        # concat demuxer 相对路径基于 list 文件目录解析 → 统一写绝对路径
        list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
        # 各镜头参数可能有差异，重编码保证拼接稳定
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                       "-loglevel", "error", str(target)],
                       check=True, timeout=180, capture_output=True)

    @staticmethod
    def _ffprobe_duration(path: Path) -> float | None:
        """Read the actual media duration used in SceneArtifact evidence."""
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                text=True, timeout=15)
            return float(out.strip())
        except (OSError, subprocess.SubprocessError, ValueError):
            return None

    # ==================================================================
    # 原子发布（ALL_READY_BEFORE_PUBLISH / K-1）
    # ==================================================================
    async def _maybe_publish(self, state: SessionState) -> None:
        epoch = state.epoch
        if not epoch or epoch.published or epoch.status == "FAILED":
            return
        # Timed decision labels may be shown at Decision Lead while their
        # media is still being planned/generated. The countdown must not be
        # held behind the H3 readiness barrier.
        if epoch.timed:
            await self._maybe_open_timed_window(state)
        branches = [state.branch(bid) for bid in epoch.branch_ids]
        branches = [b for b in branches if b]
        if branches and all(b.source == BranchSource.OPENING for b in branches):
            return  # Opening is auto-presented; it is never a user recommendation.
        in_flight = (BranchStatus.PREDICTED, BranchStatus.PLANNING, BranchStatus.NARRATIVE,
                     BranchStatus.PRODUCTION, BranchStatus.GENERATING,
                     BranchStatus.ASSEMBLING, BranchStatus.RETRYING)
        if any(b.status in in_flight for b in branches):
            return  # 还有分支在生成，继续等
        ready = [b.id for b in branches if b.status == BranchStatus.READY]
        if not ready:
            epoch.status = "FAILED"
            state.player.status = "FAILED"
            self._event(state, "epoch_failed", "本批候选全部生成失败", epoch=epoch.id)
            await self._persist(state)
            return
        epoch.effective_k = len(ready)
        epoch.ready_ids = ready
        epoch.published = True
        epoch.status = "READY"
        epoch.published_at = now_ms()
        self._event(state, "epoch_published",
                    f"推荐已就绪（{len(ready)}/{epoch.target_k}）", epoch=epoch.id)
        await tracer.emit("scheduler.publish", "success",
                          output={"effective_k": len(ready), "target_k": epoch.target_k},
                          session_id=state.id)
        await self._persist(state)
        # 限时批次：全部 READY 后才开放选择并启动倒计时（I02：倒计时窗口从可选时开始）
        if state.timed.active and epoch.timed:
            lead_open = state.player.position() >= state.player.decision_open_at or state.player.status in ("READY", "WAITING_DECISION", "ENDED")
            state.timed.selection_open = lead_open
            state.timed.deadline_ms = (now_ms() + int(state.timed.timeout_seconds * 1000)) if lead_open else None
            await self._persist(state)
            await self._push(state)
            self._schedule_timed_watchdog(state.id)

    # ==================================================================
    # 玩家选择与两阶段提交
    # ==================================================================
    def valid_branch(self, state: SessionState, branch: Branch) -> bool:
        arc = state.current_arc()
        # An active, published UNTIMED decision is held while the user thinks
        # (PRD 04.7). TTL applies once an unselected branch leaves that decision
        # and becomes reusable cache; it must not silently erase visible choices.
        held_decision = bool(
            not state.ended and state.epoch and state.epoch.published
            and state.epoch.status == "READY" and not state.epoch.timed
            and branch.id in state.epoch.ready_ids
            and branch.interaction_mode == InteractionMode.UNTIMED
        )
        return (
            branch.session_id == state.id
            and (arc is None or branch.arc_id == arc.id)
            and branch.status == BranchStatus.READY
            and (held_decision or not branch.expires_at or now_ms() <= branch.expires_at)
            and branch.fingerprint == self.compute_fingerprint(state)
            and branch.artifact is not None
            and branch.artifact.quality_status in ("READY", "DEFERRED")
            and (branch.artifact.quality_status == "READY"
                 or branch.artifact.provenance.get("deferred_media") is True)
        )

    async def _materialize_deferred_selection(self, session_id: str, branch_id: str) -> None:
        """Generate only the recommendation the player actually selected."""
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if not branch or not branch.artifact or branch.artifact.quality_status != "DEFERRED":
                return
            branch.status = BranchStatus.GENERATING
            branch.pipeline_events.append({"at": now_ms(), "status": "GENERATING",
                                           "media": "ON_DEMAND"})
            await self._persist(state)
            await self._push(state)
        try:
            await self._generate_branch_media(session_id, branch_id)
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                await self._assemble_branch(state, branch)
                branch.status = BranchStatus.READY
                branch.ready_at = now_ms()
                spent = settings.effective_shots_per_branch * settings.shot_unit_cost
                state.budget.spent_by_branch[branch.id] = spent
                state.budget.reserved = max(0, state.budget.reserved - spent)
                state.budget.used += spent
                await self._persist(state)
                await self._push(state)
        except Exception as error:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                branch.status = BranchStatus.FAILED
                branch.fail_stage = "GENERATING"
                branch.last_error = f"{type(error).__name__}: {error}"
                state.selection_lock = False
                state.player.status = "FAILED_RECOVERABLE"
                self._release_budget(state, branch)
                await self._persist(state)
                await self._push(state)
            raise

    async def _await_selected_branch(self, session_id: str, branch_id: str) -> None:
        """Keep an early Jev selection pending until its branch is ready."""
        try:
            for _ in range(1200):
                async with self._lock(session_id):
                    state = await self.load_session(session_id)
                    branch = state.branch(branch_id) if state else None
                    if not state or not branch:
                        return
                    if branch.status == BranchStatus.READY:
                        break
                    if branch.status in (BranchStatus.FAILED, BranchStatus.INVALIDATED,
                                         BranchStatus.EXPIRED, BranchStatus.CANCELLED):
                        state.selection_lock = False
                        state.pending_selected_branch_id = None
                        state.player.status = "WAITING_DECISION"
                        await self._persist(state)
                        await self._push(state)
                        return
                await asyncio.sleep(0.25)
            else:
                raise EngineError("推荐视频准备超时")
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if branch.artifact and branch.artifact.quality_status == "DEFERRED":
                await self._materialize_deferred_selection(session_id, branch_id)
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                await self._commit_selected(state, branch)
        except Exception as error:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                if state:
                    state.selection_lock = False
                    state.pending_selected_branch_id = None
                    state.player.status = "FAILED_RECOVERABLE"
                    state.messages.append({"kind": "system",
                                           "text": "已选择该方向，但视频准备失败，可以重试。",
                                           "at": now_ms()})
                    await self._persist(state)
                    await self._push(state)

    async def select_branch(self, session_id: str, branch_id: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            prior = state.branch(branch_id)
            if (prior and prior.status == BranchStatus.CANONICAL and prior.commit_event
                    and state.player.branch_id == branch_id):
                return {"status": "CANONICAL", "branch_id": branch_id, "idempotent": True}
            if state.selection_lock and state.pending_selected_branch_id == branch_id:
                return {"status": "SELECTING", "branch_id": branch_id, "idempotent": True}
            if state.player.status == "GENERATING_NEXT" and not state.pending_freeform_id:
                raise EngineError("这一幕正在重新生成，请稍候")
            if state.selection_lock:
                raise EngineError("另一个选择正在提交中")
            if state.timed.active and not state.timed.selection_open:
                raise EngineError("选项正在准备中，倒计时开始后即可选择")
            branch = state.branch(branch_id)
            early_selectable = bool(
                branch and state.epoch and state.epoch.options_exposed
                and branch.id in state.epoch.branch_ids
                and branch.source in (BranchSource.RECOMMENDATION, BranchSource.TIMED)
                and branch.status in (BranchStatus.PREDICTED, BranchStatus.PLANNING,
                                      BranchStatus.NARRATIVE, BranchStatus.PRODUCTION,
                                      BranchStatus.GENERATING, BranchStatus.ASSEMBLING))
            if not branch or (not self.valid_branch(state, branch) and not early_selectable):
                raise EngineError("该选项已失效，请选择其他方向")
            if early_selectable:
                state.selection_lock = True
                state.pending_selected_branch_id = branch_id
                if state.timed.active:
                    # Selecting a timed option closes the current countdown
                    # immediately, even while its deferred media is pending.
                    self._cancel_timed(state)
                state.player.status = "GENERATING_NEXT"
                self._event(state, "branch_selected_early",
                            f"玩家先选了推荐，等待该方向的场景准备：{branch.label}",
                            branch_id=branch_id)
                await self._persist(state)
                await self._push(state)
                asyncio.get_running_loop().create_task(
                    self._await_selected_branch(session_id, branch_id))
                return {"status": "SELECTING", "branch_id": branch_id}
            state.selection_lock = True
            state.pending_selected_branch_id = branch_id
            branch.status = BranchStatus.SELECTED
            state.counters.spend_attempts += 1
            if state.timed.active:
                self._cancel_timed(state)     # 玩家在窗口内作出选择：倒计时结束
            self._event(state, "branch_selected", f"玩家选择：{branch.label}",
                        branch_id=branch_id)
            await self._persist(state)
            await self._push(state)

        if branch.artifact and branch.artifact.quality_status == "DEFERRED":
            await self._materialize_deferred_selection(session_id, branch_id)

        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            await self._commit_selected(state, branch)
            return {"status": branch.status.value}

    async def _commit_selected(self, state: SessionState, branch: Branch) -> None:
        """Two-Phase Canonicalization：SELECTED → PROVISIONAL → 媒体确认 → CANONICAL。

        调用方必须持有 session 锁。PROVISIONAL 显式持久化+推送（可观察）；
        任何一步失败 → FAILED + 回滚事件，不污染正式状态。
        """
        if branch.status == BranchStatus.CANONICAL and branch.commit_event:
            return
        try:
            branch.status = BranchStatus.SELECTED
            # Phase 1：PROVISIONAL —— 媒体可播放性确认前的可见中间态
            branch.status = BranchStatus.PROVISIONAL
            await self._persist(state)
            await self._push(state)
            if not branch.artifact or not branch.artifact.assembled_path:
                raise EngineError("media not confirmed playable")
            media_file = settings.media_path / branch.artifact.assembled_path
            if not media_file.exists():
                raise EngineError("media file missing")
            if branch.artifact.media_type == "text" and (not state.text_mode or media_file.read_text(encoding="utf-8") != branch.narrative or not branch.narrative.strip()):
                raise EngineError("text presentation not confirmed")
            # Phase 2：媒体确认 → 双域原子提交 → CANONICAL
            await self._commit_branch(state, branch)
            branch.status = BranchStatus.CANONICAL
            locations = _scenario_location_names(state)
            origin = (branch.read_set.get("world") or {}).get("location")
            destination = state.world.location
            transition = (f"从{locations.get(origin, '先前的位置')}来到{locations.get(destination, '当前区域')}。"
                          if origin and origin != destination else "")
            branch.causal_presentation.update({"action": branch.intent.action or branch.label,
                "result": branch.outcome.text if branch.outcome else branch.narrative,
                "transition": transition, "scene_id": branch.artifact.id})
            branch.last_error = None
            branch.fail_stage = None
            branch.rollback_reason = None
            branch.commit_event = f"commit:{branch.id}"
            state.counters.spend_success += 1
            self._invalidate_others(state, branch)
            self._event(state, "branch_canonical", f"已确认：{branch.label}",
                        branch_id=branch.id, operations=[op.model_dump() for op in branch.outcome.ops] if branch.outcome else [])
            await tracer.emit("commit.canonical", "success",
                              output={"branch": branch.id, "scene_id": branch.artifact.id,
                                      "world_after": state.world.model_dump(), "drama_after": state.drama.model_dump(),
                                      "operations": [op.model_dump() for op in branch.outcome.ops] if branch.outcome else [],
                                      "skill_decisions": branch.skill_decisions},
                              session_id=state.id, branch_id=branch.id)
        except (EngineError, ProposalRejected) as e:
            branch.status = BranchStatus.FAILED
            branch.rollback_reason = str(e)
            branch.last_error = str(e)
            branch.fail_stage = "COMMIT"
            state.player.status = "FAILED_RECOVERABLE"
            self._event(state, "commit_rolled_back", f"提交回滚：{branch.label}",
                        branch_id=branch.id, error=str(e))
            await tracer.emit("commit.canonical", "failed", output={"error": str(e)},
                              session_id=state.id, branch_id=branch.id)
        finally:
            state.selection_lock = False
            state.pending_selected_branch_id = None
        if branch.status == BranchStatus.CANONICAL:
            self._present(state, branch)
        await self._persist(state)
        await self._push(state)

    def _invalidate_others(self, state: SessionState, chosen: Branch) -> None:
        for b in state.branches:
            if (b.id != chosen.id and state.epoch and b.id in state.epoch.branch_ids
                    and b.status in (BranchStatus.PREDICTED, BranchStatus.PLANNING,
                                     BranchStatus.NARRATIVE, BranchStatus.PRODUCTION,
                                     BranchStatus.GENERATING, BranchStatus.ASSEMBLING,
                                     BranchStatus.READY, BranchStatus.RETRYING)):
                b.status = BranchStatus.INVALIDATED
                b.invalidated_reason = "not_selected"
                self._release_budget(state, b)
                task = self._pipeline_tasks.get(b.id)
                if task and not task.done():
                    task.cancel()

    async def _commit_branch(self, state: SessionState, branch: Branch) -> None:
        """双域原子提交：world + drama 全部 validate 通过后才一次性落版本（G03）。

        任一域校验失败，两个域都不被修改；幂等键同事务追加。
        """
        new_world: Optional[WorldState] = None
        new_drama: Optional[DramaState] = None
        new_keys: list[str] = []
        if branch.state_patch_proposal:
            proposal = branch.state_patch_proposal.model_copy(
                update={"base_version": state.world.version,
                        "base_drama_revision": state.drama.revision})
            new_world = state_manager.validate(
                state.world, proposal, state.committed_keys,
                drama_revision=state.drama.revision,
                locations=_scenario_locations(state) or None)
            new_keys.append(proposal.idempotency_key)
        if branch.drama_patch_proposal:
            proposal = branch.drama_patch_proposal.model_copy(
                update={"base_revision": state.drama.revision})
            new_drama = drama_manager.validate_and_apply(
                state.drama, proposal, state.committed_keys)
            new_keys.append(proposal.idempotency_key)
        # 双域均通过 → 一次性赋值（原子提交点）
        if new_world is not None:
            state.world = new_world
        if new_drama is not None:
            state.drama = new_drama
        state.committed_keys.extend(k for k in new_keys if k)
        self._update_preferences(state, branch)
        self._advance_pressures(state, branch)
        self._evaluate_wishes(state, branch)

    def _update_preferences(self, state: SessionState, branch: Branch) -> None:
        kind = branch.outcome.kind if branch.outcome else "investigation"
        signals = state.preferences.signals
        signals[kind] = signals.get(kind, 0) + 1
        state.preferences.version += 1

    def _advance_pressures(self, state: SessionState, branch: Branch) -> None:
        for p in state.pressures:
            if p.driver == "COMMITTED_ACTIONS":
                p.progress = min(100.0, p.progress + 25)
        if state.world.fiction_minutes > 0:
            for p in state.pressures:
                if p.driver == "FICTION_TIME":
                    p.progress = min(100.0, p.progress + state.world.fiction_minutes / 4)

    def _present(self, state: SessionState, branch: Branch) -> None:
        duration = branch.artifact.duration if branch.artifact else settings.effective_shot_duration
        state.player.status = "PLAYING"
        state.player.scene_title = branch.outcome.title if branch.outcome else branch.label
        state.player.scene_text = branch.narrative
        state.player.caption = branch.caption
        state.player.video_url = f"/media/{branch.artifact.assembled_path}" if branch.artifact and branch.artifact.media_type == "video" else ""
        state.player.branch_id = branch.id
        state.player.duration = duration
        state.player.lead = max(0.0, duration - settings.decision_lead_seconds)
        state.player.decision_open_at = state.player.lead
        state.player.position_base = 0.0
        state.player.playing = True
        state.player.clock_started_at = now_ms()
        state.player.receipt_committed = False
        if branch.artifact and branch.artifact.media_type == "text":
            state.player.status = "WAITING_DECISION"
            state.player.playing = False
        state.epoch = None  # 本批推荐已消费
        # 关键行动记录（结局页「本篇章关键行动」回顾）
        arc = state.current_arc()
        state.turns.append({
            "at": now_ms(), "arc_seq": arc.seq if arc else 1,
            "label": branch.label,
            "title": state.player.scene_title,
            "artifact_id": branch.artifact.id if branch.artifact else None,
            "video_url": state.player.video_url, "duration": duration,
            "timed": branch.interaction_mode == InteractionMode.TIMED,
            "opening": branch.source == BranchSource.OPENING,
        })
        state.turns = state.turns[-100:]
        # 预生成下一批（预测式）：播放开始即可后台准备
        outcome = branch.outcome
        if outcome and outcome.ending and outcome.ending in _ending_families(state):
            self._close_arc(state, outcome.ending)
        else:
            asyncio.get_running_loop().create_task(self._safe_prepare(state.id))

    def _close_arc(self, state: SessionState, ending_family: str) -> None:
        arc = state.current_arc()
        if arc:
            arc.status = "CLOSED"
            arc.ending_family = ending_family
            arc.closed_at = now_ms()
        state.ended = True
        state.player.status = "ENDED"
        if state.timed.active:
            self._cancel_timed(state)
        self._event(state, "arc_closed", f"篇章收束：{ending_family}")

    # ==================================================================
    # 呈现回执与播放进度
    # ==================================================================
    async def commit_receipt(self, session_id: str) -> None:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state or state.player.receipt_committed or not state.player.branch_id:
                return
            branch = state.branch(state.player.branch_id)
            receipt = PresentationReceipt(
                id=uid("rcpt"), branch_id=state.player.branch_id,
                artifact_id=branch.artifact.id if branch and branch.artifact else None)
            state.receipts.append(receipt)
            state.player.receipt_committed = True
            if branch and branch.outcome:
                # 只有「玩家实际看到」的内容才进 knowledge（未呈现 ≠ 已知）
                for ev in branch.outcome.evidence:
                    if ev not in state.world.knowledge:
                        state.world.knowledge.append(ev)
            self._event(state, "receipt_committed", "玩家已看完当前场景",
                        branch_id=state.player.branch_id)
            await self._persist(state)

    async def _regenerate_presentation(self, session_id, branch_id):
        try:
            await self._generate_branch_media(session_id, branch_id)
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                branch = state.branch(branch_id)
                await self._assemble_branch(state, branch)
                state.player.video_url = f"/media/{branch.artifact.assembled_path}"
                state.player.duration = branch.artifact.duration
                state.player.position_base = 0
                state.player.playing = False
                state.player.status = "PLAYING"
                await self._persist(state)
                await self._push(state)
        except Exception as error:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                state.branch(branch_id).last_error = str(error)
                state.player.status = "FAILED_RECOVERABLE"
                await tracer.emit("media.regenerate", "failed", output={"error": str(error)}, session_id=session_id, branch_id=branch_id)
                await self._persist(state)
                await self._push(state)

    async def player_command(self, session_id: str, command: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            player = state.player
            if command == "regenerate":
                old = state.branch(player.branch_id) if player.branch_id else None
                if old and old.status == BranchStatus.CANONICAL:
                    running = self._pipeline_tasks.get(old.id)
                    if running and not running.done():
                        return {"position": player.position(), "status": player.status}
                    player.status = "GENERATING_NEXT"
                    self._pipeline_tasks[old.id] = asyncio.create_task(self._regenerate_presentation(session_id, old.id))
                    await self._persist(state)
                    await self._push(state)
                    return {"position": player.position(), "status": player.status}
                command = "retry"
            if command == "text_continue":
                state.text_mode = True
                failed = state.branch(state.pending_freeform_id) if state.pending_freeform_id else next((b for b in reversed(state.branches) if b.source == BranchSource.OPENING and b.status == BranchStatus.FAILED), None)
                if failed and failed.status != BranchStatus.FAILED:
                    failed = None
                if failed and failed.outcome and failed.narrative and failed.fingerprint == self.compute_fingerprint(state):
                    await self._text_artifact(state, failed)
                    await self._commit_selected(state, failed)
                    return {"position": player.position(), "status": player.status}
                player.video_url = ""
                player.playing = False
                player.position_base = player.duration
                player.status = "ENDED" if state.ended else "WAITING_DECISION"
                raw_text = failed.intent.raw_text if failed else ""
                state.pending_freeform_id = None
                state.messages.append({"kind": "system", "text": "已切换文字模式。尚未形成结果的行动已保留在输入框，可以修改后继续。" if failed else "已切换文字模式，故事可以继续。", "at": now_ms()})
                await self._persist(state)
                await self._push(state)
                return {"position": player.position(), "status": player.status, "needs_action": bool(failed), "raw_text": raw_text}
            if command == "retry":
                if player.status not in ("FAILED", "FAILED_RECOVERABLE"):
                    raise EngineError("当前没有可恢复的生成失败")
                failed = next((b for b in reversed(state.branches)
                               if b.status == BranchStatus.FAILED), None)
                if failed and failed.fail_stage == "COMMIT" and failed.artifact:
                    if failed.fingerprint != self.compute_fingerprint(state):
                        raise EngineError("故事状态已变化，请重新确认行动")
                    self._event(state, "commit_retry", "重新校验已完成场景，复用现有视频", branch_id=failed.id)
                    await self._commit_selected(state, failed)
                    return {"position": player.position(), "status": player.status}
                player.status = "OPENING_PREPARING" if not player.branch_id else "GENERATING_NEXT"
                if failed:
                    # A provider-declared failure is safe to retry with a new
                    # paid job. Preserve the old handle in pipeline_events for
                    # audit, but remove it from the active submission guard.
                    # Unknown submit outcomes remain blocked.
                    definite_media_failure = (
                        failed.fail_stage == "GENERATING"
                        and any(kind in (failed.last_error or "") for kind in (
                            "REFERENCE_UNAVAILABLE", "PROVIDER_ERROR",
                            "INVALID_RESPONSE", "AUTH_FAILED",
                            "BILLING_LOCKED", "QUOTA_EXHAUSTED",
                        ))
                        and not any(event.get("event") == "video_submit_uncertain"
                                    for event in failed.pipeline_events)
                    )
                    if definite_media_failure and failed.jobs:
                        failed.pipeline_events.append({
                            "event": "video_retry_supersedes_failed_job",
                            "provider_job_ids": list(failed.jobs),
                            "at": now_ms(),
                        })
                        failed.jobs = []
                    if failed.fail_stage == "PLANNING":
                        # Invalid model output must be replanned under the
                        # current contract, not replayed forever from cache.
                        failed.director_result = None
                    failed.status = BranchStatus.RETRYING
                    failed.last_error = None
                    self._spawn_pipeline(session_id, failed.id)
                else:
                    asyncio.get_running_loop().create_task(self._safe_prepare(session_id))
                await self._persist(state)
                await self._push(state)
                return {"position": player.position(), "status": player.status}
            if command == "skip" and player.status in ("FAILED", "FAILED_RECOVERABLE"):
                player.status = "WAITING_DECISION"
                player.video_url = ""
                player.duration = 0.0
                player.position_base = 0.0
                player.playing = False
                state.messages.append({"kind": "system", "text": "已切换文字模式，你可以继续行动。", "at": now_ms()})
                state.messages = state.messages[-50:]
                asyncio.get_running_loop().create_task(self._safe_prepare(session_id))
                await self._persist(state)
                await self._push(state)
                return {"position": 0, "status": player.status}
            if command == "pause":
                player.position_base = player.position()
                player.playing = False
            elif command == "play":
                player.clock_started_at = now_ms()
                player.playing = True
            elif command == "skip":
                player.position_base = player.duration
                player.playing = False
            pos = player.position()
            if pos >= player.duration and player.status == "PLAYING":
                player.status = "WAITING_DECISION"   # 场景播完，等待玩家选择下一步
            await self._maybe_open_timed_window(state)
            await self._persist(state)
            await self._push(state)
            return {"position": pos, "status": player.status}

    # ==================================================================
    # 自由输入
    # ==================================================================
    async def _preview_intent(self, state: SessionState, text: str, observation: dict) -> dict:
        """AI pre-fills a review card only; interpretation never executes an action."""
        if not skill_enabled("intent-reconciliation"):
            return {"action": text, "desire": "", "strategy": ""}
        context = choice_context(self._scenario_brief(state), {}, [])
        try:
            _, route, response = await self.router.call_text("director", messages=[
                {"role": "system", "content":
                    INTENT_PREVIEW_POLICY + read_language_settings().text_instruction()},
                {"role": "user", "content": json.dumps({"raw_player_input": text,
                    "observation": observation, "visible_context": context}, ensure_ascii=False)}],
                output_contract={"purpose": "intent_preview"})
            from .structured_output import decode_object
            result = decode_object(response.content)
            if any(not isinstance(result.get(k), str) for k in ("action", "desire", "strategy")) or not result["action"].strip():
                raise ValueError("invalid intent preview")
            result = {k: result[k][:300] for k in ("action", "desire", "strategy")}
            await tracer.emit("skill.intent-reconciliation", "success",
                input_={"raw_input": text, "why": "AI pre-filled confirmation; not an execution"}, output=result,
                session_id=state.id, provider=route.selected or "", model=response.model,
                duration_ms=response.latency_ms, skill_id="intent-reconciliation", skill_version="2.0.0")
            return result
        except (ProviderBlocked, ProviderError, ValueError, TypeError):
            await tracer.emit("skill.intent-reconciliation", "fallback", input_={"raw_input": text},
                output={"reason": "preview_unavailable_original_preserved"}, session_id=state.id,
                skill_id="intent-reconciliation", skill_version="2.0.0")
            return {"action": text, "desire": "", "strategy": ""}

    async def free_action(self, session_id: str, text: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            if state.player.status == "GENERATING_NEXT" and not state.pending_freeform_id:
                raise EngineError("这一幕正在重新生成，请稍候")
            if state.selection_lock:
                raise EngineError("正在提交上一个选择，请稍候")
            pending = state.branch(state.pending_freeform_id) if state.pending_freeform_id else None
            if pending and pending.status not in (BranchStatus.CANONICAL, BranchStatus.FAILED, BranchStatus.CANCELLED, BranchStatus.INVALIDATED, BranchStatus.EXPIRED):
                raise EngineError("正在继续上一个行动，请稍候")
            if state.ended:
                raise EngineError("本篇章已结束")
            if state.timed.active:
                # 限时窗口内的自由输入视为玩家已行动：倒计时消解，不触发超时 fallback
                self._cancel_timed(state)
            state.pending_intent = None
            self._event(state, "player_input", f"玩家行动：{text}", raw_input=text)
            mechanics = state.scenario_snapshot.get("mechanics", {})
            try:
                _, _drec, answer = await self.router.call_decision(
                    state={"location": state.world.location, "raw_player_input": text},
                    questions=[{"id": "intent", "text": text}])
                intent_obs = answer.details or {}
                await tracer.emit("decision.intent", "success", input_={"raw_player_input": text},
                                  output={"observation": intent_obs}, provider=_drec.selected or "", model=answer.model,
                                  session_id=state.id)
            except (ProviderBlocked, ProviderError):
                intent_obs = {"confidence": 0.9, "impact": "LOW",
                              "clarification_required": False}
            needs_preview = intent_obs.get("clarification_required") or (
                float(intent_obs.get("confidence", 0.8)) < 0.75 and intent_obs.get("impact") != "LOW")
            if needs_preview:
                intent_obs.update(await self._preview_intent(state, text, intent_obs))
            if intent_obs.get("clarification_required"):
                # 高影响低置信：可编辑澄清卡（保留玩家原文，不覆盖）
                state.pending_intent = {
                    "raw_text": text,
                    "action": intent_obs.get("action") or text,
                    "desire": intent_obs.get("desire") or "",
                    "strategy": intent_obs.get("strategy") or "",
                    "confidence": float(intent_obs.get("confidence", 0.0)),
                    "kind": "clarification",
                }
                self._event(state, "clarification_requested", "需要玩家澄清意图",
                            raw_input=text)
                await self._persist(state)
                await self._push(state)
                return {"status": "CLARIFICATION_REQUIRED",
                        "question": intent_obs.get("clarification") or "你具体想怎么做？",
                        "echo": dict(state.pending_intent)}
            confidence = float(intent_obs.get("confidence", 0.8))
            impact = intent_obs.get("impact", "MEDIUM")
            if confidence < 0.75 and impact != "LOW":
                # 中置信度：意图回显卡（FR-046 我这样理解你的意思 → 确认/修改后继续）
                state.pending_intent = {
                    "raw_text": text,
                    "action": intent_obs.get("action") or text,
                    "desire": intent_obs.get("desire") or "",
                    "strategy": intent_obs.get("strategy") or "",
                    "confidence": confidence,
                    "kind": "echo",
                }
                self._event(state, "intent_echo", "等待玩家确认理解", raw_input=text,
                            confidence=confidence)
                await self._persist(state)
                await self._push(state)
                return {"status": "INTENT_ECHO", "echo": dict(state.pending_intent)}
            return await self._plan_free_action(state, text, intent_obs)

    async def confirm_intent(self, session_id: str, approved: bool,
                             action: str = "", desire: str = "", strategy: str = "") -> dict:
        """意图回显/澄清的确认入口（FR-046）：玩家确认或修改理解后继续。

        玩家原文始终保留（pending_intent.raw_text / 事件日志 raw_input）；
        确认后的 desire_source 记为 PLAYER_CONFIRMED。
        """
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            pending = state.pending_intent
            if not pending:
                raise EngineError("没有待确认的意图")
            state.pending_intent = None
            if not approved:
                self._event(state, "intent_rejected", "玩家放弃这次行动",
                            raw_input=pending.get("raw_text", ""))
                state.messages.append({"kind": "system",
                                       "text": "好的，这次行动已取消。你可以换一种表达。",
                                       "at": now_ms()})
                state.messages = state.messages[-50:]
                await self._persist(state)
                await self._push(state)
                return {"status": "CANCELLED"}
            raw = pending.get("raw_text", "")
            intent_obs = {
                "action": action.strip() or pending.get("action") or raw,
                "desire": desire.strip() or pending.get("desire") or None,
                "strategy": strategy.strip() or pending.get("strategy") or None,
                "desire_source": "PLAYER_CONFIRMED",
                "confidence": 0.95, "impact": "MEDIUM",
            }
            self._event(state, "intent_confirmed", "玩家确认了系统的理解",
                        raw_input=raw, desire=intent_obs["desire"] or "")
            return await self._plan_free_action(state, raw, intent_obs,
                                                label_override=intent_obs["action"])

    async def _plan_free_action(self, state: SessionState, text: str,
                                intent_obs: dict, label_override: str = "") -> dict:
        """自由输入的规划路径：Director 判定三档响应 → QUICK_ACK 立即提交 / 完整分支生成。"""
        mechanics = state.scenario_snapshot.get("mechanics", {})
        packet = understand_action(text, intent_obs, label_override)
        async def trace_intent(branch: Branch | None = None):
            await tracer.emit("skill.intent-reconciliation", "success",
                input_={"raw_input": text, "why": "preserve original and confirmed player intent"},
                output=packet.model_dump(), session_id=state.id,
                branch_id=branch.id if branch else None, trace_id=branch.trace_id if branch else None,
                skill_id="intent-reconciliation", skill_version="2.0.0")
        try:
            content, rec = await self._director_output(
                [{"role": "user", "content": f"raw_player_input: {packet.action}\n"
                  f"action_semantics: {packet.model_dump_json()}\n"
                  f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}"}],
                mechanics, state.id)
        except Exception as error:
            branch = Branch(id=uid("br"), trace_id=uid("trace"), session_id=state.id,
                arc_id=state.current_arc().id if state.current_arc() else "",
                source=BranchSource.FREE, label=label_override or text,
                intent=ResolvedIntent(raw_text=text, action=label_override or text),
                base_versions=self._branch_base_versions(state), read_set=self.build_read_set(state),
                fingerprint=self.compute_fingerprint(state),
                expires_at=now_ms() + settings.branch_ttl_seconds * 1000,
                status=BranchStatus.FAILED, fail_stage="PLANNING", last_error=str(error))
            await trace_intent(branch)
            state.branches.append(branch)
            state.pending_freeform_id = branch.id
            state.player.status = "FAILED_RECOVERABLE"
            self._event(state, "branch_failed", "行动暂时没有生成成功", branch_id=branch.id, error=str(error))
            await self._persist(state)
            await self._push(state)
            return {"status": "FAILED_RECOVERABLE"}
        outcome = content.get("outcome") or {}
        mode = "FULL_BEAT" if outcome.get("ending") else outcome.get("mode", "FULL_BEAT")
        await tracer.emit("director.action", "success", input_={"raw_player_input": text},
                          output={"response_mode": mode, "outcome": outcome, "directive": content.get("directive")}, provider=rec.selected or "", model=rec.model or "", session_id=state.id)
        if mode == "QUICK_ACK" and outcome.get("skill_triggers"):
            mode = "FULL_BEAT"
        if mode == "QUICK_ACK":
            await trace_intent()
            # 轻量回应：确定性 patch 直接提交，不产生媒体分支
            ops = _to_patch_ops(outcome.get("ops", []))
            if ops:
                proposal = StatePatchProposal(
                    proposal_id=uid("prop"), base_version=state.world.version,
                    base_drama_revision=state.drama.revision, source="quick_ack",
                    operations=ops, idempotency_key=f"ack:{uid('k')}")
                try:
                    state.world = state_manager.validate(
                        state.world, proposal, state.committed_keys,
                        drama_revision=state.drama.revision,
                        locations=_scenario_locations(state) or None)
                    state.committed_keys.append(proposal.idempotency_key)
                except ProposalRejected:
                    pass
            ack = outcome.get("text", "好的。")
            self._event(state, "quick_ack", ack, raw_input=text,
                        response_mode="QUICK_ACK")
            # 小动作反馈流 + MERGED_TRANSITION 汇总（FR-048：小动作连续发生时合并）
            state.messages.append({"kind": "ack", "text": ack, "at": now_ms()})
            state.merge_buffer.append({"text": text, "ack": ack, "at": now_ms()})
            merged = False
            if len(state.merge_buffer) >= 3:
                parts = [m["text"] for m in state.merge_buffer[-3:]]
                summary = "你把这几个小动作连了起来：" + "；".join(parts) + \
                          "。这些探索已记录在故事里。"
                state.messages.append({"kind": "merged", "text": summary, "at": now_ms()})
                self._event(state, "merged_transition", summary,
                            response_mode="MERGED_TRANSITION")
                state.merge_buffer = []
                merged = True
            state.messages = state.messages[-50:]
            await self._persist(state)
            await self._push(state)
            return {"status": "QUICK_ACK", "ack": ack, "merged": merged}
        state.merge_buffer = []   # 完整 beat 打断小动作序列
        # 完整分支
        branch = Branch(
            director_result=content, routes=[rec], action_semantics=packet.model_dump(),
            id=uid("br"), trace_id=uid("trace"), session_id=state.id,
            arc_id=state.current_arc().id if state.current_arc() else "",
            source=BranchSource.FREE, label=text,
            summary=outcome.get("title", text),
            probability=float(intent_obs.get("confidence", 0.8)),
            intent=ResolvedIntent(
                raw_text=text, action=label_override or text,
                desire=intent_obs.get("desire"), strategy=intent_obs.get("strategy"),
                desire_source=intent_obs.get("desire_source", "UNKNOWN"),
                confidence=float(intent_obs.get("confidence", 0.8)),
                impact=intent_obs.get("impact", "MEDIUM")),
            base_versions=self._branch_base_versions(state),
            read_set=self.build_read_set(state),
            fingerprint=self.compute_fingerprint(state),
            expires_at=now_ms() + settings.branch_ttl_seconds * 1000)
        await trace_intent(branch)
        state.branches.append(branch)
        state.player.status = "GENERATING_NEXT"
        state.pending_freeform_id = branch.id   # 就绪后自动选中（玩家已通过输入选择）
        if not (state.epoch and state.epoch.published):
            state.epoch = RecommendationEpoch(
                id=uid("epoch"), k=1, target_k=1, status="PLANNING",
                branch_ids=[branch.id])
        await self._persist(state)
        await self._push(state)
        self._spawn_pipeline(state.id, branch.id)
        return {"status": "GENERATING", "branch_id": branch.id,
                "label": PHASE_LABELS[BranchStatus.PLANNING]}

    async def cancel_generation(self, session_id: str) -> dict:
        """取消当前生成（原型检查项）：在途分支置 CANCELLED、释放预算、输入保留在前端草稿。"""
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            cancelled: list[str] = []
            for b in state.pipeline_branches():
                task = self._pipeline_tasks.get(b.id)
                if task and not task.done():
                    task.cancel()
                b.status = BranchStatus.CANCELLED
                self._release_budget(state, b)
                self._event(state, "branch_cancelled", f"已取消生成：{b.label}",
                            branch_id=b.id)
                cancelled.append(b.id)
            if state.pending_freeform_id in cancelled:
                state.pending_freeform_id = None
            if state.epoch and not state.epoch.published:
                state.epoch.status = "FAILED"
                state.epoch = None
            if state.timed.active:
                self._cancel_timed(state)
            if not cancelled:
                return {"status": "NOTHING_TO_CANCEL"}
            await self._persist(state)
            await self._push(state)
        asyncio.get_running_loop().create_task(self._safe_prepare(session_id))
        return {"status": "CANCELLED", "count": len(cancelled)}

    # ==================================================================
    # 愿望系统
    # ==================================================================
    async def add_wish(self, session_id: str, text: str) -> Wish:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            wish = Wish(id=uid("wish"), raw=text,
                        normalized_preference=self._normalize_wish(text),
                        version=state.wish_seq + 1)
            state.wishes.append(wish)
            state.wish_seq += 1
            # 愿望影响 Drama 上下文：指纹变化 → 未就绪分支保守失效
            fp = self.compute_fingerprint(state)
            self._invalidate_stale(state, fp)
            self._event(state, "wish_added", f"玩家愿望：{text}", wish=wish.id)
            await self._persist(state)
            await self._push(state)
            return wish

    async def withdraw_wish(self, session_id: str, wish_id: str) -> None:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            for w in state.wishes:
                if w.id == wish_id and w.status == WishStatus.ACTIVE:
                    w.status = WishStatus.WITHDRAWN
                    w.history.append({"at": now_ms(), "action": "withdraw"})
            state.wish_seq += 1
            fp = self.compute_fingerprint(state)
            self._invalidate_stale(state, fp)
            await self._persist(state)
            await self._push(state)

    # ------------------------------------------------------------------
    # Wish Ledger（G25 / PRD Q41 / FR-053）：八态生命周期按真实提交事件推进，
    # 候选视频或模型一句"已考虑"不算达成。
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_wish(text: str) -> str:
        """把玩家原文归成可匹配的偏好关键词（规则化，不调 LLM）。"""
        import re as _re
        t = text.strip()
        for pat, tag in ((r"离开|逃走|脱身|平安|活下去|活着", "leave_alive"),
                         (r"真相|知道|明白|发现|找到", "learn_truth"),
                         (r"救|保护|帮|照顾|安慰", "protect_npc"),
                         (r"原谅|和解|信任|在一起|关系", "relationship"),
                         (r"收集|找到所有|线索|证据", "collect_evidence")):
            if _re.search(pat, t):
                return tag
        return "generic"

    def _evaluate_wishes(self, state: SessionState, branch: Branch) -> None:
        """分支 CANONICAL 前按真实 outcome 推进 ACTIVE wish 的状态（G25）。

        判定依据：outcome.ending（结局族）、kind、evidence、ops 的实际落地内容。
        只迁移 ACTIVE 愿望；每条 history 记 action/reason/evidence/branch/at。
        """
        if branch.outcome is None:
            return
        outcome = branch.outcome
        ending = outcome.ending or ""
        kind = outcome.kind or ""
        evidence = set(outcome.evidence or [])
        ops_text = json.dumps([o.model_dump() for o in outcome.ops], ensure_ascii=False)

        def bump(w: Wish, status: WishStatus, reason: str, ev: list[str]) -> None:
            w.status = status
            w.version += 1
            w.evidence.extend(ev)
            w.history.append({"at": now_ms(), "action": status.value,
                              "reason": reason, "branch": branch.id,
                              "evidence": ev})
            self._event(state, "wish_updated",
                        f"愿望{self._wish_status_label(status)}：{w.raw}",
                        wish=w.id, branch_id=branch.id)

        for w in state.wishes:
            if w.status != WishStatus.ACTIVE:
                continue
            pref = w.normalized_preference or self._normalize_wish(w.raw)
            # 结局触发的达成/部分达成判定
            if ending:
                if pref == "leave_alive":
                    if "departure" in ending or "exit" in ending or "leave" in ending \
                            or "escape" in ending:
                        bump(w, WishStatus.FULFILLED, "达成离开结局", [ending])
                    else:
                        bump(w, WishStatus.PARTIALLY_FULFILLED,
                             f"走向了 {ending}，未真正离开", [ending])
                elif pref == "learn_truth":
                    if "truth" in ending or "reveal" in ending:
                        bump(w, WishStatus.FULFILLED, "达成真相揭示结局", [ending])
                    else:
                        bump(w, WishStatus.PARTIALLY_FULFILLED,
                             f"结局 {ending} 未完全揭示真相", [ending])
                elif pref == "relationship":
                    bump(w, WishStatus.PARTIALLY_FULFILLED,
                         f"故事以 {ending} 收束", [ending])
                continue
            # 非结局分支：按 kind/evidence/ops 部分推进
            if pref == "learn_truth" and (evidence & {"truth_revealed"} or evidence):
                bump(w, WishStatus.PARTIALLY_FULFILLED, "获得了新线索", sorted(evidence))
            elif pref == "collect_evidence" and (evidence or "clues." in ops_text):
                bump(w, WishStatus.PARTIALLY_FULFILLED, "收集到线索",
                     sorted(evidence) or ["clues"])
            elif pref == "protect_npc" and kind == "social":
                bump(w, WishStatus.PARTIALLY_FULFILLED, "关心了角色", ["social"])
            elif pref == "relationship" and "relationships." in ops_text:
                bump(w, WishStatus.PARTIALLY_FULFILLED, "关系发生变化", ["relationships"])
            elif pref == "leave_alive" and kind == "withdrawal":
                bump(w, WishStatus.PARTIALLY_FULFILLED, "尝试离开", ["withdrawal"])

    @staticmethod
    def _wish_status_label(status: WishStatus) -> str:
        return {"FULFILLED": "已实现", "PARTIALLY_FULFILLED": "部分实现",
                "CONFLICTED": "与规则冲突", "FAILED": "未能实现",
                "SUPERSEDED": "被替换", "WITHDRAWN": "已撤回",
                "DEFERRED": "已延期", "ACTIVE": "生效中"}.get(status.value, status.value)

    # ==================================================================
    # 结局后续杯（continue world）
    # ==================================================================
    async def continue_world(self, session_id: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state or not state.ended:
                raise EngineError("本篇章尚未结束")
            state.pending_continuation = True
            await self._persist(state)
            await self._push(state)
        from .structured_output import decode_object
        try:
            messages = [{"role": "system", "content": "仅返回 JSON {question:中文新篇章问题,conflict:中文新矛盾}。延续已发生的事实，不撤销旧结局，不把未选择的未来当作事实。"},
                        {"role": "user", "content": "new_arc: " + json.dumps({"world": state.world.model_dump(mode="json"), "last_ending": state.arcs[-1].model_dump(mode="json")}, ensure_ascii=False)}]
            for attempt in range(2):
                _, _rec, resp = await self.router.call_text("authoring", messages=messages,
                    output_contract={"purpose": "new_arc"}, budget={"max_tokens": 1200, "reasoning_effort": "low"})
                try:
                    content = decode_object(resp.content)
                    if not all(isinstance(content.get(k), str) and content[k].strip() for k in ("question", "conflict")):
                        raise ValueError("new arc requires question and conflict")
                    break
                except ValueError:
                    if attempt:
                        raise
                    messages.append({"role": "user", "content": "请返回完整的 question 和 conflict 两个非空字符串字段。"})
        except Exception as error:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                state.pending_continuation = False
                await self._persist(state)
                await self._push(state)
            await tracer.emit("arc.continue", "failed", output={"error": repr(error)}, session_id=session_id)
            raise EngineError("新篇章暂时没有准备成功，世界已保存，可以重试。") from error
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            seq = len(state.arcs) + 1
            state.arcs.append(Arc(id=uid("arc"), seq=seq, question=content["question"], conflict=content["conflict"]))
            state.ended = False
            state.pending_continuation = False
            state.player.status = "WAITING_DECISION"
            state.drama.phase = PhaseHint.SETUP
            self._event(state, "arc_opened",
                        f"新篇章开启：{content.get('question', '')}")
            await self._persist(state)
            await self._push(state)
        # Continuing creates and saves the Arc only (PRD 07.16).  The player's
        # next explicit action enters the normal FREE pipeline; opening an Arc
        # must not immediately purchase another speculative Top-K batch.
        return {"status": "CONTINUED", "arc": seq}

    async def _safe_prepare(self, session_id: str) -> None:
        try:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                if state and not state.ended and not state.text_mode:
                    await self.prepare_recommendations(state)
                    await self._persist(state)
                    await self._push(state)
        except Exception as e:  # noqa: BLE001
            await tracer.emit("scheduler.prepare", "failed", output={"error": str(e)},
                              session_id=session_id)

    # ==================================================================
    # 推送与视图
    # ==================================================================
    async def _push(self, state: SessionState) -> None:
        subs = self.subscribers.get(state.id, [])
        if not subs:
            return
        view = self.player_view(state)
        dead = []
        for ws in subs:
            try:
                await ws.send_json({"type": "state", "view": view})
            except Exception:
                dead.append(ws)
        for ws in dead:
            subs.remove(ws)

    def player_view(self, state: SessionState) -> dict:
        """玩家视图：先暴露已锁定的 Jev 选项，媒体就绪状态单独呈现。"""
        recommendations = []
        position = state.player.position()
        # Recommendation exposure is a server-side timing contract.  Once the
        # decision lead is reached, locked Jev labels may be exposed while
        # branch media is still planning or generating; media_ready is shown
        # separately and does not gate the decision UI.
        lead_open = (state.player.status in ("WAITING_DECISION", "READY", "ENDED")
                     or position >= state.player.decision_open_at)
        pending_demand = state.branch(state.pending_freeform_id) if state.pending_freeform_id else None
        demand_running = pending_demand and pending_demand.status not in (BranchStatus.FAILED, BranchStatus.CANONICAL, BranchStatus.CANCELLED, BranchStatus.INVALIDATED, BranchStatus.EXPIRED)
        if (lead_open and not state.text_mode and not demand_running
                and not state.selection_lock and state.epoch
                and (state.epoch.published or state.epoch.options_exposed)):
            ids = state.epoch.ready_ids if state.epoch.published else state.epoch.branch_ids
            for bid in ids:
                b = state.branch(bid)
                if (b and b.source in (BranchSource.RECOMMENDATION, BranchSource.TIMED)
                        and b.status not in (BranchStatus.FAILED, BranchStatus.INVALIDATED,
                                             BranchStatus.EXPIRED, BranchStatus.CANCELLED,
                                             BranchStatus.SELECTED, BranchStatus.PROVISIONAL, BranchStatus.CANONICAL)):
                    recommendations.append({
                        "branch_id": b.id, "label": _public_story_text(state, b.label),
                        "summary": _public_story_text(state, b.summary), "confidence": b.probability,
                        "source": b.source.value,
                        "media_ready": bool(b.artifact and b.artifact.quality_status == "READY")})
        pos = position
        if pos >= state.player.duration and state.player.status == "PLAYING":
            state.player.status = "WAITING_DECISION"
            state.player.playing = False
            state.player.position_base = state.player.duration
        snapshot = state.scenario_snapshot
        chars = {c.get("id"): c for c in snapshot.get("characters", [])}
        player_char = chars.get(snapshot.get("player_character", "player"), {})
        # 已选分支（提交窗口内用于「已选收起」呈现）
        selected = None
        if state.pending_selected_branch_id:
            pending_selected = state.branch(state.pending_selected_branch_id)
            if pending_selected:
                selected = {"branch_id": pending_selected.id,
                            "label": _public_story_text(state, pending_selected.label),
                            "status": "SELECTING"}
        for b in reversed(state.branches[-10:]):
            if selected is None and b.status in (BranchStatus.SELECTED, BranchStatus.PROVISIONAL,
                            BranchStatus.CANONICAL):
                selected = {"branch_id": b.id, "label": _public_story_text(state, b.label),
                            "status": b.status.value}
                break
        # 已知状态（呈现回执后才进 knowledge；这里给工具栏展示）
        clue_labels = _clue_labels(state)
        clues = [{"id": k, "label": clue_labels.get(k, k)}
                 for k, v in state.world.clues.items() if v]
        knowledge = [{"id": k, "label": clue_labels.get(k, k)}
                     for k in state.world.knowledge]
        relationships = [
            {"id": cid, "name": chars.get(cid, {}).get("identity", cid).split(" /")[0],
             "value": v}
            for cid, v in state.world.relationships.items()]
        # 限时互动视图（服务器墙钟权威，前端只渲染剩余时间）
        timed_view = None
        if state.timed.active:
            remaining_ms = (max(0, state.timed.deadline_ms - now_ms())
                            if state.timed.deadline_ms else None)
            timed_view = {
                "active": True, "kind": state.timed.kind,
                "timeout_seconds": state.timed.timeout_seconds,
                "remaining_ms": remaining_ms,
                "selection_open": state.timed.selection_open,
                "fallback_hint": "倒计时结束后，会按这个故事已经设定好的结果继续。",
            }
        arc = state.current_arc()
        pending_branch = (state.branch(state.pending_freeform_id)
                          if state.pending_freeform_id else None)
        if pending_branch and pending_branch.status not in (
                BranchStatus.PREDICTED, BranchStatus.PLANNING, BranchStatus.NARRATIVE,
                BranchStatus.PRODUCTION, BranchStatus.GENERATING, BranchStatus.ASSEMBLING,
                BranchStatus.RETRYING):
            pending_branch = None
        view = {
            "session_id": state.id,
            "scenario": {"title": snapshot.get("title", ""),
                         "player_identity": player_char.get("identity", "玩家")},
            "arc": {"seq": arc.seq if arc else len(state.arcs), "total": len(state.arcs)},
            # 前情提要：OPENING_PREPARING 阶段立即给出，视频 READY 后由前端接管淡出。
            # 零生成（全来自 snapshot），不会阻塞首次视图返回。
            "opening": _opening_info(state),
            "player": {
                "status": state.player.status,
                "scene_title": _public_story_text(state, state.player.scene_title),
                "scene_text": _public_story_text(state, state.player.scene_text),
                "caption": _public_story_text(state, state.player.caption),
                "caption_speaker": chars.get(current.caption_speaker, {}).get("identity", "") if (current := state.branch(state.player.branch_id)) and current.caption_speaker else "",
                "location_name": _scenario_location_names(state).get(state.world.location, "当前区域"),
                "video_url": state.player.video_url,
                "duration": state.player.duration,
                "lead": state.player.lead,
                "decision_open_at": state.player.decision_open_at,
                "position": min(pos, state.player.duration),
            },
            "presentation": {"error_message": "这个行动暂时没有生成成功。" if state.player.status in ("FAILED", "FAILED_RECOVERABLE") else "",
                "recovery_actions": ["retry", "modify", "text_continue", "exit"] if state.player.status in ("FAILED", "FAILED_RECOVERABLE") else [],
                "state": "GENERATING_MEDIA" if state.player.status in ("GENERATING_NEXT", "OPENING_PREPARING") else state.player.status},
            "action_pending": state.player.status == "GENERATING_NEXT" or bool(state.pending_freeform_id and (pending := state.branch(state.pending_freeform_id)) and pending.status not in (BranchStatus.CANONICAL, BranchStatus.FAILED, BranchStatus.CANCELLED, BranchStatus.INVALIDATED, BranchStatus.EXPIRED)),
            # 问题6：pending 分支的执行描写与真实 pipeline 阶段，
            # 前端 ActionSequence 在等待期逐句淡入 + 进度带。
            "pending_effects": [
                _public_story_text(state, s)
                for s in (pending_branch.outcome.effects
                          if pending_branch and pending_branch.outcome else [])
            ] if (state.player.status == "GENERATING_NEXT" or pending_branch) else [],
            "pending_phase": pending_branch.status.value if pending_branch else "",
            "pending_label": _public_story_text(state, pending_branch.label) if pending_branch else "",
            "causal_presentation": {k: _public_story_text(state, v) for k, v in current.causal_presentation.items()
                                    if k in ("action", "result", "visual_focus", "transition") and isinstance(v, str)}
                                    if current and current.status == BranchStatus.CANONICAL and current.source != BranchSource.OPENING else None,
            "recommendations": recommendations,
            "selected": selected,
            "generating": [{"branch_id": b.id, "label": b.label,
                            "phase_label": PHASE_LABELS.get(b.status, "")}
                           for b in state.pipeline_branches()],
            "timed": timed_view,
            "pending_intent": state.pending_intent,
            # G27：最近一次失败的自由输入，供玩家重试/修改/放弃
            "last_failed_action": (
                {"branch_id": b.id, "label": b.label,
                 "raw_text": b.intent.raw_text, "error": "这个行动暂时没有生成成功。",
                 "fail_stage": b.fail_stage or ""}
                if (b := next(
                    (x for x in reversed(state.branches[-10:])
                     if x.status == BranchStatus.FAILED
                     and x.source == BranchSource.FREE and x.id == state.pending_freeform_id), None)) else None),
            "known": {"inventory": state.world.inventory, "inventory_labels": _mechanic_labels(state, "inventory"), "relationships": relationships,
                      "clues": clues, "knowledge": knowledge},
            "messages": state.messages[-20:],
            "hint_chips": state.hint_chips[:4],
            "ended": state.ended,
            "pending_continuation": state.pending_continuation,
            "wishes": [w.model_dump(mode="json") for w in state.wishes],
        }
        if state.ended:
            view["ending"] = self._ending_view(state)
        return view

    def _ending_view(self, state: SessionState) -> dict:
        """篇章结束页数据：保留清单 / 下一篇章预告 / 关键行动 / 篇章历史 / 继续条件。"""
        closed = [a for a in state.arcs if a.status == "CLOSED"]
        last = closed[-1] if closed else None
        family = last.ending_family if last else None
        chars = {c.get("id"): c for c in state.scenario_snapshot.get("characters", [])}
        arc_seq = last.seq if last else 1
        min_branch_cost = settings.effective_shots_per_branch * settings.shot_unit_cost
        return {
            "family": family,
            "title": _ending_families(state).get(family or "", "篇章收束"),
            "carried": {
                "relationships": [
                    {"id": cid,
                     "name": chars.get(cid, {}).get("identity", cid).split(" /")[0],
                     "value": v}
                    for cid, v in state.world.relationships.items()],
                "inventory": state.world.inventory,
                "knowledge": [{"id": k, "label": _clue_labels(state).get(k, k)}
                              for k in state.world.knowledge],
                "continue_note": "你的关系、物品与已知事实会带入下一篇章。",
            },
            "next_arc_hint": "故事还留有未解的部分，下一篇章将从这些事实继续。",
            "turns": [t for t in state.turns if t.get("arc_seq") == arc_seq],
            "arcs": [{"seq": a.seq, "ending_family": a.ending_family,
                      "closed_at": a.closed_at} for a in closed],
            "continue_available": state.budget.available() >= min_branch_cost,
            "budget": {"total": state.budget.total, "used": state.budget.used},
        }

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
from ..domain.schemas import (
    BaseVersions, Branch, BranchSource, BranchStatus, DramaticDirective, DramaPatchProposal,
    DramaState, Event, ForeshadowEntry, InteractionMode, OutcomeSpec, PatchOperation,
    PhaseHint, PresentationReceipt, PressureInstance, RecommendationEpoch, ResolvedIntent,
    SceneArtifact, ScenePacket, ShotPlan, StatePatchProposal, Wish, WishStatus, WorldState,
    now_ms,
)
from ..domain.state_manager import ProposalRejected, StateManager
from ..providers.router import ProviderBlocked, ProviderError, ProviderRouter
from ..skills.registry import is_enabled as skill_enabled
from ..skills import mechanic as mechanic_skill
from .session_state import Arc, BudgetLedger, SessionState, TimedState
from .tracer import tracer

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
        return {
            "title": snapshot.get("title", ""),
            "genre": snapshot.get("genre", ""),
            "tone": snapshot.get("tone", ""),
            "core_question": drama.get("core_question", ""),
            "ending_families": _ending_families(state),
            "truth_model": drama.get("truth_model", ""),
            "locations": _scenario_location_names(state),
            "location": state.world.location,
            "inventory": state.world.inventory,
            "clues": list(state.world.clues.keys()),
            "relationships": state.world.relationships,
            "phase": state.drama.phase.value,
            "npcs": [{"id": cid, "identity": chars.get(cid, {}).get("identity", cid)}
                     for cid in _npc_ids(state)],
        }

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
            extra=extra)
        state.add_event(evt)
        return evt

    async def create_session(self, scenario_version_id: str) -> SessionState:
        async with SessionLocal() as db:
            vrow = await db.get(ScenarioVersionRow, scenario_version_id)
            if vrow is None:
                raise EngineError(f"scenario version not found: {scenario_version_id}")
            snapshot = vrow.snapshot
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
                for role, ca_id in (srow.data.get("frozen_asset_refs") or {}).items():
                    if not ca_id or ca_id in g_assets:
                        continue
                    crow = await db.get(CharacterAssetRow, ca_id)
                    if crow is None:
                        continue
                    ca = crow.data
                    g_assets[ca_id] = {
                        "id": ca_id, "version": srow.data.get("character_version", 1),
                        "role": role or ca.get("role", "identity"),
                        "entity": cid, "binding": cid,
                        "name": f"{ca.get('role', role)}·v{srow.data.get('character_version',1)}",
                        "type": "image" if ca.get("url", "").startswith(("data:", "http", "/")) else "",
                        "path": ca.get("url", "")}
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
        state.asset_manifest = [
            {"id": r.data.get("id"), "version": r.data.get("version", 1),
             "role": r.data.get("role", ""), "entity": r.data.get("entity", ""),
             "binding": r.data.get("binding", ""), "name": r.data.get("name", ""),
             "type": r.data.get("type", ""), "path": r.data.get("storage_path", "")}
            for r in arows] + list(g_assets.values())
        self.sessions[state.id] = state
        await self._persist(state)
        await tracer.emit("session.create", "success", output={"session_id": state.id},
                          session_id=state.id)
        # 开场：为当前幕准备第一批推荐
        asyncio.get_running_loop().create_task(self._safe_prepare(state.id))
        return state

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
                state.asset_manifest = manifest
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
        candidates: list[dict] = [
            dict(label=f"仔细观察{here}的细节", confidence=0.6,
                 summary="不承诺立场，先收集眼前可观察的信息", kind="investigation"),
        ]
        for cid in npcs[:1]:
            name = chars.get(cid, {}).get("identity", cid).split(" /")[0]
            candidates.append(
                dict(label=f"和{name}谈谈，听 TA 怎么说", confidence=0.6,
                     summary="不推进调查，让关系自然流动", kind="social"))
        other_locs = [l for l in loc_ids if l != world.location]
        if other_locs:
            dest = loc_names.get(other_locs[-1], other_locs[-1])
            candidates.append(
                dict(label=f"离开这里，去{dest}", confidence=0.55,
                     summary="主动改变自己所处的位置", kind="withdrawal"))
        else:
            candidates.append(
                dict(label="主动退出眼前的故事", confidence=0.55,
                     summary="不再参与眼前的矛盾", kind="withdrawal"))
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
            "npcs": [{"id": cid, "identity": chars.get(cid, {}).get("identity", cid)}
                     for cid in npcs],
            "phase": state.drama.phase.value,
            "wishes": [w.raw for w in state.wishes if w.status == WishStatus.ACTIVE],
            "recent_events": [e.summary for e in state.events[-5:]],
            "instruction": "生成 3-5 个玩家此刻可采取的行动候选，"
                           "返回 JSON: {\"candidates\": [{\"label\",\"summary\",\"kind\"}]}，"
                           "kind ∈ investigation/social/risk/withdrawal",
        }
        candidates: list[dict] = []
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
                              output={"count": len(candidates)},
                              provider=rec.selected or "", session_id=state.id)
        except (ProviderBlocked, ProviderError, ValueError, KeyError) as e:
            await tracer.emit("director.candidates", "degraded",
                              output={"reason": str(e)[:200]}, session_id=state.id)
        if not candidates:
            candidates = self._generic_candidates(state)

        # Jev/Decision 排序（Mock 决策或真实 API）；不可用则保持现有顺序
        try:
            _, rec, answer = await self.router.call_decision(
                state={"location": world.location, "inventory": world.inventory,
                       "clues": world.clues, "raw_player_input": ""},
                questions=[{"id": "rank", "candidates": [c["label"] for c in candidates]}])
            ranked = answer.scores or {}
            if ranked:
                candidates.sort(key=lambda c: -ranked.get(c["label"], 0.0))
            await tracer.emit("decision.rank", "success",
                              input_={"candidates": [c["label"] for c in candidates]},
                              output={"ranked": ranked}, provider=rec.selected or "",
                              session_id=state.id)
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

        candidates = (await self.candidate_actions(state))[: settings.target_k]
        state.hint_chips = [c["label"] for c in candidates[:3]]
        # 限时互动触发（I02/I03）：Scenario 预先声明 + 时机条件（至少已完成两个有效行动）
        timed_node = self._next_timed_node(state)
        branch_ids: list[str] = []
        epoch_id = uid("epoch")
        mode = InteractionMode.TIMED if timed_node else InteractionMode.UNTIMED
        source = BranchSource.TIMED if timed_node else BranchSource.RECOMMENDATION
        for cand in candidates:
            estimated = settings.shots_per_branch * settings.shot_unit_cost
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
            id=epoch_id, k=len(branch_ids), target_k=settings.target_k,
            status="PLANNING", branch_ids=branch_ids, timed=bool(timed_node))
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
            state.budget.reserved += settings.shots_per_branch * settings.shot_unit_cost
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
        estimated = settings.shots_per_branch * settings.shot_unit_cost
        releasable = max(0, estimated - spent)
        state.budget.reserved = max(0, state.budget.reserved - releasable)

    # ==================================================================
    # 限时互动（I02/I03：TIMED 互动是 Scenario 声明的互动模式，不是 UI 特效）
    # ==================================================================
    def _next_timed_node(self, state: SessionState) -> Optional[dict]:
        """从 Scenario 声明中解析下一个待触发的限时节点。

        触发条件（确定性）：本篇章未触发过、QTE 玩法启用、且已经历至少两个有效行动
        （world.version >= 3，避免开场即倒计时）。超时结果由 Scenario 预先声明。
        """
        if not state.scenario_snapshot.get("mechanics", {}).get("qte", {}).get("enabled", True):
            return None
        arc = state.current_arc()
        turns_done = len([t for t in state.turns if arc and t.get("arc_seq") == arc.seq])
        if turns_done < 1:
            return None   # 至少完成一个关键行动后才可能进入限时节点
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
                    if not state or not state.timed.active or not state.timed.deadline_ms:
                        return
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

    # ==================================================================
    # Branch 生成流水线
    # ==================================================================
    def _spawn_pipeline(self, session_id: str, branch_id: str) -> None:
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
            await self._set_phase(state, branch, BranchStatus.PLANNING)

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
            await self._set_phase(state, branch, BranchStatus.PRODUCTION)

        await self._phase_sleep()
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if branch.status != BranchStatus.PRODUCTION:
                return
            await self._shoot_branch(state, branch)
            await self._set_phase(state, branch, BranchStatus.GENERATING)

        gen_error: Optional[str] = None
        try:
            await self._generate_branch_media(session_id, branch_id)
        except Exception as e:  # noqa: BLE001
            gen_error = str(e)
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            branch = state.branch(branch_id)
            if branch.status != BranchStatus.GENERATING:
                return
            if gen_error:
                if not retried:
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
            spent = settings.shots_per_branch * settings.shot_unit_cost
            state.budget.spent_by_branch[branch.id] = spent
            state.budget.reserved = max(0, state.budget.reserved - spent)
            state.budget.used += spent
            self._event(state, "branch_ready", f"候选已就绪：{branch.label}", branch_id=branch.id)
            await self._persist(state)
            await self._maybe_publish(state)
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
    async def _plan_branch(self, state: SessionState, branch: Branch) -> None:
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
            "\"target_changes\": [str], \"hard_constraints\": [str], \"avoid\": [str]}}。"
            "skill_triggers 仅在玩家行动明确触发玩法机制时给出（如获得物品→inventory、"
            "发现线索→clue-system、关心角色→relationship）；不触发则为空数组。")
        _, rec, resp = await self.router.call_text(
            "director",
            messages=[{"role": "user", "content":
                       f"raw_player_input: {branch.label}\n"
                       f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}\n"
                       f"{schema_hint}"}],
            output_contract={"purpose": "director_plan", "mechanics": mechanics},
            branch_id=branch.id)
        content = json.loads(resp.content)
        outcome = content.get("outcome") or {}
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
            kind=outcome.get("kind", "investigation"))
        branch.summary = branch.summary or branch.outcome.title
        # Mechanic Skill 闭环（G26）：director 产出的 skill_triggers 显式走
        # skill 函数 → 带 skill_version/input 的 Proposal → 合并进 state patch ops。
        # 禁用/不处理的 trigger 静默跳过；产出与普通 ops 走同一 validate→commit。
        for trig in outcome.get("skill_triggers") or []:
            sid = trig.get("skill", "")
            result = mechanic_skill.invoke(
                sid, trig, self._scenario_brief(state), mechanics,
                branch.id, state.world.version, state.drama.revision)
            if result is None:
                continue
            for op in result["proposal"]["operations"]:
                branch.outcome.ops.append(PatchOperation(**op))
            await tracer.emit(f"skill.{sid}", "success",
                              input_=result["input"],
                              output={"ops": len(result["proposal"]["operations"])},
                              provider="runtime",
                              session_id=state.id, branch_id=branch.id,
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
        branch.context = self.build_context(state, directive_data)
        branch.packet = self._build_scene_packet(state, branch)
        branch.routes.append(rec)
        await tracer.emit("director.plan", "success", input_={"label": branch.label},
                          output={"primary_function": branch.directive.primary_function},
                          provider=rec.selected or "", model=rec.model or "",
                          session_id=state.id, branch_id=branch.id)

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
        for key in branch.packet.forbidden_revelations:
            value = values.get(key, "")
            for seg in _re.split(r"[，。；、,.;！？\s]+", value):
                seg = seg.strip()
                # ≥6 字才视为泄密特征片段：短片段（如角色名 "Alice"、地名）会出现在
                # 任何正常叙事里，阈值过低会把合法文本误判为泄密（G07 泛化后暴露）。
                if len(seg) >= 6 and seg in text:
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

    async def _narrate_branch(self, state: SessionState, branch: Branch) -> None:
        outcome = branch.outcome
        base_messages = [{"role": "user", "content":
                          f"scene_title: {outcome.title if outcome else branch.label}\n"
                          f"scene_text: {outcome.text if outcome else branch.summary}\n"
                          f"caption: {branch.summary}"}]
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
                output_contract={"purpose": "narrative_beat", "context": branch.context,
                                 "packet": branch.packet.model_dump(mode="json")
                                 if branch.packet else {},
                                 "scenario_brief": self._scenario_brief(state)},
                branch_id=branch.id)
            content = json.loads(resp.content)
            text = content.get("text") or (outcome.text if outcome else branch.summary)
            leaked = self._forbidden_hits(state, branch, text)
            if not leaked:
                branch.narrative = text
                branch.caption = content.get("caption") or branch.summary
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
                          output={"chars": len(branch.narrative)},
                          provider=rec.selected or "", session_id=state.id, branch_id=branch.id)

    def _bound_references(self, state: SessionState) -> list[dict]:
        """Visual Continuity Skill 的确定性部分：在场角色的绑定素材进入 references。

        绑定规则：asset.binding 或 asset.entity 命中在场角色 id，或 role 为
        identity/wardrobe/voice/motion 的全局参考。Skills 只产 Proposal，不直接改状态。
        """
        if not skill_enabled("visual-continuity"):
            try:
                asyncio.get_running_loop().create_task(tracer.emit(
                    "visual-continuity.blocked", "blocked",
                    output={"reason": "skill disabled"},
                    skill_id="visual-continuity"))
            except RuntimeError:
                pass
            return []
        chars = {c.get("id") for c in state.scenario_snapshot.get("characters", [])}
        # v0.6 FR-093：按标准视图优先级挑图像参考（front > 3⁄4 > side > full_*），
        # 每角色 ≤4 张；voice/motion 不占用图像名额。
        _IMG_ORDER = {"front": 0, "three_quarter": 1, "side": 2,
                      "full_front": 3, "full_side": 4}
        picked: dict[str, list[dict]] = {}      # entity → image refs
        extras: list[dict] = []                 # voice / motion / 其他
        for a in state.asset_manifest:
            entity = a.get("entity") or ""
            binding = a.get("binding") or ""
            role = a.get("role") or ""
            if not (entity in chars or binding in chars or
                    role in ("identity", "wardrobe", "voice", "motion",
                             *list(_IMG_ORDER))):
                continue
            ref = {"asset_id": a.get("id"), "name": a.get("name", ""),
                   "role": role or "reference", "entity": entity,
                   "path": a.get("path", ""), "version": a.get("version", 1)}
            if role in _IMG_ORDER:
                bucket = picked.setdefault(entity or binding or "_", [])
                bucket.append(ref)
            else:
                extras.append(ref)
        refs: list[dict] = []
        for entity, bucket in picked.items():
            bucket.sort(key=lambda r: _IMG_ORDER.get(r["role"], 9))
            refs.extend(bucket[:4])             # 每角色 ≤4 张（FR-093 上限）
        refs.extend(extras[:6 - min(len(refs), 6)])
        return refs[:6]

    async def _shoot_branch(self, state: SessionState, branch: Branch) -> None:
        _, rec, resp = await self.router.call_text(
            "production",
            messages=[{"role": "user", "content":
                       f"raw_player_input: {branch.label}\n"
                       f"scene_title: {branch.outcome.title if branch.outcome else branch.label}\n"
                       f"scene_text: {branch.narrative[:120]}"}],
            output_contract={"purpose": "production_shots"},
            branch_id=branch.id)
        content = json.loads(resp.content)
        raw_shots = content.get("shots") or []
        refs = self._bound_references(state)
        branch.references = refs
        branch.shots = [
            ShotPlan(id=f"shot_{i + 1}", index=i + 1,
                     title=s.get("title", f"镜头 {i + 1}"),
                     duration=float(s.get("duration", settings.mock_shot_duration)),
                     trim_end=float(s.get("duration", settings.mock_shot_duration)),
                     subtitle=s.get("subtitle", ""), prompt=s.get("prompt", ""),
                     references=refs)
            for i, s in enumerate(raw_shots)
        ] or [ShotPlan(id="shot_1", index=1, title=branch.label,
                       duration=settings.mock_shot_duration,
                       trim_end=settings.mock_shot_duration, subtitle=branch.caption,
                       references=refs)]
        branch.shot_count = len(branch.shots)
        branch.routes.append(rec)
        await tracer.emit("production.shots", "success",
                          output={"shots": len(branch.shots)},
                          provider=rec.selected or "", session_id=state.id,
                          branch_id=branch.id, skill_id="h3-production")

    async def _generate_branch_media(self, session_id: str, branch_id: str) -> None:
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
                      "duration": s.duration, "references": s.references}
                     for s in branch.shots]
            references = branch.references
        provider, rec = self.router.video_provider(branch_id)
        # Real providers receive one request per Shot.  The previous code sent
        # the whole ShotPlan as one request, which produced one clip and made a
        # concatenated artifact look like multi-shot generation.
        async def submit_one(shot: dict):
            return await provider.submit({
                "job_id": f"{branch_id}_{shot['id']}", "shots": [shot],
                "references": references, "prompt": shot.get("title", "")})
        handles = await asyncio.gather(*(submit_one(shot) for shot in shots))
        clips: list[str] = []
        shot_provenance: list[dict] = []
        for shot, handle in zip(shots, handles):
            for _ in range(240):
                result = await provider.status(handle)
                if result.status == "READY":
                    shot_clips = (result.raw or {}).get("clips", [])
                    clips.extend(shot_clips)
                    shot_provenance.append({"shot_id": shot["id"],
                                            "provider": handle.provider,
                                            "request_id": handle.provider_job_id,
                                            "clips": shot_clips,
                                            "status": result.status})
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
        await asyncio.get_running_loop().run_in_executor(
            None, self._ffmpeg_concat, clips, target)
        branch.artifact = SceneArtifact(
            id=scene_id, branch_id=branch.id,
            clip_refs=[c.name for c in clips],
            assembled_path=f"scenes/{scene_id}.mp4", quality_status="READY",
            provenance={"assembler": "ffmpeg-concat",
                        "providers": [r.selected for r in branch.routes],
                        "jobs": branch.jobs,
                        "shot_provenance": [e.get("shots", []) for e in branch.pipeline_events
                                             if e.get("event") == "real_multi_shot_jobs"]},
            duration=sum(s.duration for s in branch.shots) or settings.mock_shot_duration)
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

    # ==================================================================
    # 原子发布（ALL_READY_BEFORE_PUBLISH / K-1）
    # ==================================================================
    async def _maybe_publish(self, state: SessionState) -> None:
        epoch = state.epoch
        if not epoch or epoch.published or epoch.status == "FAILED":
            return
        branches = [state.branch(bid) for bid in epoch.branch_ids]
        branches = [b for b in branches if b]
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
            state.timed.selection_open = True
            state.timed.deadline_ms = now_ms() + int(state.timed.timeout_seconds * 1000)
            await self._persist(state)
            await self._push(state)
            self._schedule_timed_watchdog(state.id)

    # ==================================================================
    # 玩家选择与两阶段提交
    # ==================================================================
    def valid_branch(self, state: SessionState, branch: Branch) -> bool:
        arc = state.current_arc()
        return (
            branch.session_id == state.id
            and (arc is None or branch.arc_id == arc.id)
            and branch.status == BranchStatus.READY
            and (not branch.expires_at or now_ms() <= branch.expires_at)
            and branch.fingerprint == self.compute_fingerprint(state)
            and branch.artifact is not None
            and branch.artifact.quality_status == "READY"
        )

    async def select_branch(self, session_id: str, branch_id: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            if state.selection_lock:
                raise EngineError("另一个选择正在提交中")
            if state.timed.active and not state.timed.selection_open:
                raise EngineError("选项正在准备中，倒计时开始后即可选择")
            branch = state.branch(branch_id)
            if not branch or not self.valid_branch(state, branch):
                raise EngineError("该选项已失效，请选择其他方向")
            state.selection_lock = True
            branch.status = BranchStatus.SELECTED
            state.counters.spend_attempts += 1
            if state.timed.active:
                self._cancel_timed(state)     # 玩家在窗口内作出选择：倒计时结束
            self._event(state, "branch_selected", f"玩家选择：{branch.label}",
                        branch_id=branch_id)
            await self._persist(state)
            await self._push(state)

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
            # Phase 2：媒体确认 → 双域原子提交 → CANONICAL
            await self._commit_branch(state, branch)
            branch.status = BranchStatus.CANONICAL
            branch.commit_event = f"commit:{branch.id}"
            state.counters.spend_success += 1
            self._invalidate_others(state, branch)
            self._event(state, "branch_canonical", f"已确认：{branch.label}",
                        branch_id=branch.id)
            await tracer.emit("commit.canonical", "success",
                              output={"branch": branch.id},
                              session_id=state.id, branch_id=branch.id)
        except (EngineError, ProposalRejected) as e:
            branch.status = BranchStatus.FAILED
            branch.rollback_reason = str(e)
            self._event(state, "commit_rolled_back", f"提交回滚：{branch.label}",
                        branch_id=branch.id, error=str(e))
            await tracer.emit("commit.canonical", "failed", output={"error": str(e)},
                              session_id=state.id, branch_id=branch.id)
        finally:
            state.selection_lock = False
        if branch.status == BranchStatus.CANONICAL:
            self._present(state, branch)
        await self._persist(state)
        await self._push(state)

    def _invalidate_others(self, state: SessionState, chosen: Branch) -> None:
        for b in state.branches:
            if b.id != chosen.id and b.status == BranchStatus.READY:
                b.status = BranchStatus.INVALIDATED
                b.invalidated_reason = "not_selected"

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
        duration = branch.artifact.duration if branch.artifact else settings.mock_shot_duration
        state.player.status = "PLAYING"
        state.player.scene_title = branch.outcome.title if branch.outcome else branch.label
        state.player.scene_text = branch.narrative
        state.player.caption = branch.caption
        state.player.video_url = f"/media/{branch.artifact.assembled_path}" if branch.artifact else ""
        state.player.branch_id = branch.id
        state.player.duration = duration
        state.player.lead = max(0.0, duration - settings.decision_lead_seconds)
        state.player.decision_open_at = state.player.lead
        state.player.position_base = 0.0
        state.player.playing = True
        state.player.clock_started_at = now_ms()
        state.player.receipt_committed = False
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

    async def player_command(self, session_id: str, command: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            player = state.player
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
                player.status = "READY"   # 场景播完，等待玩家选择下一步
            await self._persist(state)
            await self._push(state)
            return {"position": pos, "status": player.status}

    # ==================================================================
    # 自由输入
    # ==================================================================
    async def free_action(self, session_id: str, text: str) -> dict:
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            if not state:
                raise EngineError("session not found")
            if state.selection_lock:
                raise EngineError("正在提交上一个选择，请稍候")
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
            except (ProviderBlocked, ProviderError):
                intent_obs = {"confidence": 0.9, "impact": "LOW",
                              "clarification_required": False}
            if intent_obs.get("clarification_required"):
                # 高影响低置信：可编辑澄清卡（保留玩家原文，不覆盖）
                state.pending_intent = {
                    "raw_text": text,
                    "action": text,
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
        _, rec, resp = await self.router.call_text(
            "director",
            messages=[{"role": "user", "content":
                       f"raw_player_input: {text}\n"
                       f"scenario_context: {json.dumps(self._scenario_brief(state), ensure_ascii=False)}"}],
            output_contract={"purpose": "director_plan", "mechanics": mechanics})
        content = json.loads(resp.content)
        outcome = content.get("outcome") or {}
        mode = outcome.get("mode", "FULL_BEAT")
        if mode == "QUICK_ACK":
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
        state.branches.append(branch)
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
        _, _rec, resp = await self.router.call_text(
            "authoring",
            messages=[{"role": "user", "content": "new_arc: continue world"}],
            output_contract={"purpose": "new_arc"})
        content = json.loads(resp.content)
        async with self._lock(session_id):
            state = await self.load_session(session_id)
            seq = len(state.arcs) + 1
            state.arcs.append(Arc(id=uid("arc"), seq=seq))
            state.ended = False
            state.pending_continuation = False
            state.player.status = "READY"
            state.drama.phase = PhaseHint.SETUP
            self._event(state, "arc_opened",
                        f"新篇章开启：{content.get('question', '')}")
            await self._persist(state)
            await self._push(state)
        asyncio.get_running_loop().create_task(self._safe_prepare(session_id))
        return {"status": "CONTINUED", "arc": seq}

    async def _safe_prepare(self, session_id: str) -> None:
        try:
            async with self._lock(session_id):
                state = await self.load_session(session_id)
                if state and not state.ended:
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
        """玩家视图：只含 READY 分支与自然语言状态（术语隔离，I05 Ready Gate）。"""
        recommendations = []
        position = state.player.position()
        # Recommendation exposure is a server-side timing contract.  A missing
        # video never opens the gate early; only the recorded decision_open_at
        # (or an explicitly ended scene) can expose ready branches.
        lead_open = (state.player.status in ("READY", "ENDED")
                     or position >= state.player.decision_open_at)
        if lead_open and state.epoch and state.epoch.published:
            for bid in state.epoch.ready_ids:
                b = state.branch(bid)
                if b and self.valid_branch(state, b):
                    recommendations.append({
                        "branch_id": b.id, "label": b.label,
                        "summary": b.summary, "confidence": b.probability,
                        "source": b.source.value})
        pos = position
        if pos >= state.player.duration and state.player.status == "PLAYING":
            state.player.status = "READY"
            state.player.playing = False
            state.player.position_base = state.player.duration
        snapshot = state.scenario_snapshot
        chars = {c.get("id"): c for c in snapshot.get("characters", [])}
        player_char = chars.get(snapshot.get("player_character", "player"), {})
        # 已选分支（提交窗口内用于「已选收起」呈现）
        selected = None
        for b in reversed(state.branches[-10:]):
            if b.status in (BranchStatus.SELECTED, BranchStatus.PROVISIONAL,
                            BranchStatus.CANONICAL):
                selected = {"branch_id": b.id, "label": b.label,
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
        view = {
            "session_id": state.id,
            "scenario": {"title": snapshot.get("title", ""),
                         "player_identity": player_char.get("identity", "玩家")},
            "arc": {"seq": arc.seq if arc else len(state.arcs), "total": len(state.arcs)},
            "player": {
                "status": state.player.status,
                "scene_title": state.player.scene_title,
                "scene_text": state.player.scene_text,
                "caption": state.player.caption,
                "video_url": state.player.video_url,
                "duration": state.player.duration,
                "lead": state.player.lead,
                "decision_open_at": state.player.decision_open_at,
                "position": min(pos, state.player.duration),
            },
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
                 "raw_text": b.intent.raw_text, "error": b.last_error or "",
                 "fail_stage": b.fail_stage or ""}
                if (b := next(
                    (x for x in reversed(state.branches[-10:])
                     if x.status == BranchStatus.FAILED
                     and x.source == BranchSource.FREE), None)) else None),
            "known": {"inventory": state.world.inventory, "relationships": relationships,
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
        min_branch_cost = settings.shots_per_branch * settings.shot_unit_cost
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

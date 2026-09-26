"""核心数据契约（PRD 10.1 / 10.5）。所有跨层对象都在这里定义，模型输出必须过这些 Schema。"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Literal, Optional

from .media_language import MediaLanguage

from pydantic import BaseModel, Field


def now_ms() -> int:
    return int(time.time() * 1000)


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class BranchStatus(str, Enum):
    PREDICTED = "PREDICTED"
    PLANNING = "PLANNING"
    NARRATIVE = "NARRATIVE"
    PRODUCTION = "PRODUCTION"
    GENERATING = "GENERATING"
    ASSEMBLING = "ASSEMBLING"
    READY = "READY"
    SELECTED = "SELECTED"
    PROVISIONAL = "PROVISIONAL"
    CANONICAL = "CANONICAL"
    STALE_CANDIDATE = "STALE_CANDIDATE"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


BRANCH_PIPELINE = [
    BranchStatus.PLANNING,
    BranchStatus.NARRATIVE,
    BranchStatus.PRODUCTION,
    BranchStatus.GENERATING,
    BranchStatus.ASSEMBLING,
    BranchStatus.READY,
]

BRANCH_TERMINAL = {
    BranchStatus.CANONICAL, BranchStatus.FAILED, BranchStatus.EXPIRED,
    BranchStatus.INVALIDATED, BranchStatus.CANCELLED,
}


class BranchSource(str, Enum):
    OPENING = "opening"
    RECOMMENDATION = "recommendation"   # 系统推荐（投机预生成）
    FREE = "free"                       # 自由输入（demand）
    TIMED = "timed"                     # 限时互动候选
    MERGED = "merged"                   # 合并小动作过渡
    FALLBACK = "fallback"               # 限时互动的确定性超时结果（Scenario 预先声明）


class ResponseMode(str, Enum):
    QUICK_ACK = "QUICK_ACK"
    MERGED_TRANSITION = "MERGED_TRANSITION"
    FULL_BEAT = "FULL_BEAT"


class InteractionMode(str, Enum):
    UNTIMED = "UNTIMED"
    TIMED = "TIMED"


class WishStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEFERRED = "DEFERRED"
    CONFLICTED = "CONFLICTED"
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class ForeshadowStatus(str, Enum):
    PROPOSED = "PROPOSED"
    PLANTED = "PLANTED"
    REINFORCED = "REINFORCED"
    PAYOFF_READY = "PAYOFF_READY"
    PAID_OFF = "PAID_OFF"
    ABANDONED = "ABANDONED"


class ArcStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class PhaseHint(str, Enum):
    SETUP = "SETUP"
    EXPLORATION = "EXPLORATION"
    ESCALATION = "ESCALATION"
    REVELATION = "REVELATION"
    CRISIS = "CRISIS"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"


class RuntimeProfile(str, Enum):
    AGENT_LOCAL = "AGENT_LOCAL_PROFILE"
    VIDEO_LOCAL = "VIDEO_LOCAL_PROFILE"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    ASSEMBLING = "ASSEMBLING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ORPHANED = "ORPHANED"


class AssetType(str, Enum):
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"


# ---------------------------------------------------------------------------
# Scenario / 创作域
# ---------------------------------------------------------------------------

class MechanicConfig(BaseModel):
    enabled: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    skill_id: str = ""
    version: str = "1.0.0"
    title: str = ""
    tutorial: str = ""
    trigger: str = ""
    state_patch_contract: list[str] = Field(default_factory=list)


class CharacterOutfit(BaseModel):
    """One character's outfit, reusable in library and scenario scope."""
    id: str
    name: str = ""
    description: str = ""
    reference_assets: list[str] = Field(default_factory=list)
    reference_slots: dict[str, str | list[str] | None] = Field(default_factory=dict)
    is_default: bool = False


class ScenarioCharacter(BaseModel):
    """Scenario Character Instance（不是全局角色库条目）。"""
    id: str
    identity: str
    personality: str = ""
    desire: str = ""
    fear: str = ""
    secrets: str = ""
    knowledge: str = ""
    relationship: str = ""
    visual_state: str = ""
    global_character_id: Optional[str] = None       # 绑定全局角色库条目（版本快照）
    global_character_version: Optional[int] = None
    # Explicit OVERRIDE preserves an empty selection; only INHERIT uses the pin.
    outfit_id: Optional[str] = None
    pose_refs: list[str] = Field(default_factory=list)
    motion_refs: list[str] = Field(default_factory=list)
    voice_id: Optional[str] = None
    overlay_sources: dict[str, Literal["INHERIT", "OVERRIDE"]] = Field(default_factory=dict)
    local_outfits: list[CharacterOutfit] = Field(default_factory=list)
    reference_overrides: dict[str, str | list[str] | None] = Field(default_factory=dict)


class DramaSpec(BaseModel):
    core_question: str = ""
    central_conflict: str = ""
    truth_model: str = ""
    secrets: str = ""
    misbeliefs: str = ""
    pressures: str = ""
    anchors: str = ""
    ending_families: str = ""
    foreshadows: str = ""
    forbidden_outcomes: str = ""
    # 限时互动声明（I02/I03）：每行 "id｜kind(qte|urgent_dialogue)｜超时秒｜超时确定性结果"
    # 超时 fallback 必须由 Scenario 预先声明，模型不得临场改判。
    timed_interactions: str = ""


class WorldSpec(BaseModel):
    rules: str = ""
    lore: str = ""
    locations: str = ""        # 每行 "id｜名称"
    constraints: str = ""


class ThemeConfig(BaseModel):
    accent: str = "#245477"
    font: str = "system"
    density: str = "comfortable"
    subtitles: str = "normal"
    background: str = "plain"


class ScenarioDraft(BaseModel):
    """可编辑草案。发布后形成不可变 ScenarioVersion。"""
    id: str
    title: str = "未命名 Scenario"
    description: str = ""
    genre: str = ""
    tone: str = ""
    play_style: str = ""
    player_character: str = "player"
    status: str = "DRAFT"      # DRAFT / PUBLISHED / ARCHIVED
    version: str = "0.1.0"
    owner: str = "user"
    world: WorldSpec = Field(default_factory=WorldSpec)
    characters: list[ScenarioCharacter] = Field(default_factory=list)
    drama: DramaSpec = Field(default_factory=DramaSpec)
    mechanics: dict[str, MechanicConfig] = Field(default_factory=dict)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    authoring_intent: str = ""
    mechanic_authoring_intent: str = ""
    creator_projection: dict[str, Any] = Field(default_factory=dict)
    reviewed: bool = False
    manual_edits: list[str] = Field(default_factory=list)
    locks: list[str] = Field(default_factory=list)
    # G17：结构化变更日志 {path, before, after, source, at}
    changes: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: int = Field(default_factory=now_ms)


class ScenarioVersionRecord(BaseModel):
    id: str
    scenario_id: str
    version: str
    snapshot: ScenarioDraft
    created_at: int = Field(default_factory=now_ms)


# ---------------------------------------------------------------------------
# 全局角色库（跨 Scenario 共享，可检索）+ v0.6 Character Asset System
# ---------------------------------------------------------------------------

class GlobalCharacter(BaseModel):
    id: str
    name: str
    bio: str = ""
    aliases: list[str] = Field(default_factory=list)
    personality: str = ""
    tags: list[str] = Field(default_factory=list)
    default_desire: str = ""
    default_fear: str = ""
    default_secrets: str = ""
    default_knowledge: str = ""
    default_relationship: str = ""
    appearance: str = ""                            # 外观文字描述（AI 可补全，用户确认）
    ref_front_asset: Optional[str] = None     # asset_id
    ref_three_quarter_asset: Optional[str] = None
    ref_side_asset: Optional[str] = None
    ref_full_front_asset: Optional[str] = None
    ref_full_side_asset: Optional[str] = None
    ref_back_asset: Optional[str] = None
    ref_other_assets: list[str] = Field(default_factory=list)
    ref_voice_asset: Optional[str] = None
    ref_motion_asset: Optional[str] = None
    # v0.6 shared Character Studio granularity. These fields are optional so
    # existing rows and text-only characters remain valid.
    ref_pose_assets: list[str] = Field(default_factory=list)
    ref_motion_assets: list[str] = Field(default_factory=list)
    alternate_voice_assets: list[str] = Field(default_factory=list)
    outfits: list[dict[str, Any]] = Field(default_factory=list)
    current_version_id: Optional[str] = None        # CharacterVersion.id（v0.6）
    status: str = "ACTIVE"                         # ACTIVE / ARCHIVED
    version: int = 1
    created_at: int = Field(default_factory=now_ms)
    updated_at: int = Field(default_factory=now_ms)


class CharacterAssetStatus(str, Enum):
    GENERATED = "GENERATED"      # 模型刚产出
    CANDIDATE = "CANDIDATE"      # 候选，待用户选择
    APPROVED = "APPROVED"        # 用户批准（可作 Derived/Outfit ref）
    CANONICAL = "CANONICAL"      # 正式 Canonical Reference
    ARCHIVED = "ARCHIVED"        # 归档（被替换后）


class CharacterAsset(BaseModel):
    """角色视觉/声音资产（v0.6 FR-095）：非破坏式，role 与 status 分离。"""
    id: str
    character_id: str
    character_version_id: Optional[str] = None
    asset_id: Optional[str] = None              # 底层 Asset.id（文件）
    role: str = ""                # front / three_quarter / side / full_front /
                                # full_side / outfit / pose / motion / voice / derived
    status: CharacterAssetStatus = CharacterAssetStatus.CANDIDATE
    outfit_id: Optional[str] = None
    source_asset_refs: list[str] = Field(default_factory=list)   # edit 的输入引用
    generation_job_id: Optional[str] = None
    provenance: dict[str, Any] = Field(default_factory=dict)     # provider/model/prompt_hash
    url: str = ""                 # 可预览 URL（fal 返回或本地 /files/）
    created_at: int = Field(default_factory=now_ms)


class CharacterVersion(BaseModel):
    """角色可复现版本（Q84）：重要变化产生新版本，发布后不改写。"""
    id: str
    character_id: str
    version: int
    change_type: str = "METADATA"   # IDENTITY/APPEARANCE/METADATA/ASSET_ADDITION/VOICE
    identity_spec: dict[str, Any] = Field(default_factory=dict)  # name/bio/personality/appearance
    canonical_asset_refs: dict[str, Optional[str]] = Field(default_factory=dict)
    other_refs: list[str] = Field(default_factory=list)
    outfits: list[CharacterOutfit] = Field(default_factory=list)
    pose_refs: list[str] = Field(default_factory=list)
    motion_refs: list[str] = Field(default_factory=list)
    canonical_voice_ref: Optional[str] = None
    alternate_voice_refs: list[str] = Field(default_factory=list)
    source_version_id: Optional[str] = None
    breaking_identity_change: bool = False
    created_at: int = Field(default_factory=now_ms)


class ScenarioCharacterSnapshot(BaseModel):
    """Scenario 消费的角色快照（Q86）：Global 新版不自动渗透。"""
    id: str
    scenario_version_id: str
    global_character_id: str
    character_version_id: str
    character_version: int = 1
    frozen_identity: dict[str, Any] = Field(default_factory=dict)
    frozen_asset_refs: dict[str, Any] = Field(default_factory=dict)
    local_overrides: dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=now_ms)


class CharacterVersionDiff(BaseModel):
    from_version: int
    to_version: int
    change_types: list[str] = Field(default_factory=list)
    field_diffs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    asset_diffs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    breaking_identity_change: bool = False


class CharacterReferenceSelection(BaseModel):
    """Production Reference Resolver 输出（Q89-91 / FR-093）：实际发送可审计。"""
    scene_or_shot_id: str
    character_snapshot_id: str
    selected_image_refs: list[str] = Field(default_factory=list)   # 2-4 张
    voice_ref: Optional[str] = None
    motion_ref: Optional[str] = None
    selection_reason: str = ""
    developer_override: bool = False
    provider_limits_snapshot: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 素材
# ---------------------------------------------------------------------------

class Asset(BaseModel):
    id: str
    scenario_id: str
    type: AssetType
    name: str
    mime: str = ""
    size: int = 0
    duration: Optional[float] = None
    dimensions: Optional[list[int]] = None
    storage_path: str = ""           # 服务器本地路径（受控）
    content_hash: str = ""
    entity: str = ""                 # 绑定对象（角色 id / 地点 id / style）
    binding: str = ""                # Character / Location / Style / Voice / Motion reference
    role: str = ""                   # identity / wardrobe / location / style / voice / motion / camera
    canonical: bool = False
    authorized: bool = False
    source: str = ""
    version: int = 1
    trim_start: float = 0.0
    trim_end: float = 5.0
    created_at: int = Field(default_factory=now_ms)


# ---------------------------------------------------------------------------
# 世界 / 戏剧状态（Session 内）
# ---------------------------------------------------------------------------

class WorldState(BaseModel):
    """Hard State：只保存已确认事实。版本由 StateManager 单调递增。"""
    version: int = 1
    location: str = "start"          # Scenario 未声明 locations 时的中性默认值
    inventory: list[str] = Field(default_factory=list)
    relationships: dict[str, int] = Field(default_factory=dict)
    knowledge: list[str] = Field(default_factory=list)
    clues: dict[str, str] = Field(default_factory=dict)
    objects: dict[str, Any] = Field(default_factory=dict)
    fiction_minutes: int = 0
    health: int = 100
    inspected: list[str] = Field(default_factory=list)
    truth: dict[str, str] = Field(default_factory=dict)


class ForeshadowEntry(BaseModel):
    id: str
    origin: str = "AUTHOR_SEEDED"     # AUTHOR_SEEDED / EMERGENT
    status: ForeshadowStatus = ForeshadowStatus.PROPOSED
    truth: str = ""
    evidence: list[str] = Field(default_factory=list)      # event ids
    presentation: list[str] = Field(default_factory=list)  # receipt ids
    payoff_event: Optional[str] = None
    abandon_reason: Optional[str] = None


class TwistCandidate(BaseModel):
    id: str
    title: str
    status: str = "DEFERRED"          # DEFERRED / READY / EXECUTED / REJECTED
    required: list[str] = Field(default_factory=list)   # 需要已呈现的证据
    truth: str = ""
    belief: str = ""
    consequence: str = ""
    reviews: list[dict[str, Any]] = Field(default_factory=list)


class DramaState(BaseModel):
    revision: int = 1
    plan_version: int = 1
    phase: PhaseHint = PhaseHint.EXPLORATION
    secondary: list[PhaseHint] = Field(default_factory=lambda: [PhaseHint.SETUP])
    phase_reason: str = ""
    progress: list[dict[str, Any]] = Field(default_factory=list)
    foreshadows: list[ForeshadowEntry] = Field(default_factory=list)
    twists: list[TwistCandidate] = Field(default_factory=list)
    obligations: list[dict[str, Any]] = Field(default_factory=list)
    evaluated: list[str] = Field(default_factory=list)    # beat_id:revision 幂等键
    last_directive: Optional[dict[str, Any]] = None


class PressureInstance(BaseModel):
    id: str
    title: str
    progress: float = 0.0
    source: str = ""
    driver: str = "COMMITTED_ACTIONS"   # COMMITTED_ACTIONS / FICTION_TIME
    deadline_basis: str = ""
    evidence: list[str] = Field(default_factory=list)


class Wish(BaseModel):
    id: str
    raw: str
    normalized_preference: str = ""
    scope: str = "WORLD"              # WORLD / ARC
    arc_id: str = ""
    status: WishStatus = WishStatus.ACTIVE
    version: int = 1
    effective_from_turn: int = 0
    effective_boundary: str = "下一未锁定 Beat"
    evidence: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)


class PlayerPreferenceState(BaseModel):
    version: int = 0
    signals: dict[str, int] = Field(default_factory=lambda: {
        "investigation": 0, "social": 0, "risk": 0, "withdrawal": 0})
    evidence: list[str] = Field(default_factory=list)


class NarrativeMemory(BaseModel):
    unresolved_conflicts: list[str] = Field(default_factory=list)
    character_impressions: list[str] = Field(default_factory=list)
    emotional_context: str = ""
    source_events: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Proposal（Skills / 模型对状态的唯一写入方式）
# ---------------------------------------------------------------------------

class PatchOperation(BaseModel):
    op: str                            # set / increment / addItem / removeItem / inspect
    path: Optional[str] = None
    value: Any = None


class StatePatchProposal(BaseModel):
    proposal_id: str
    base_version: int
    source: str = ""
    operations: list[PatchOperation] = Field(default_factory=list)
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    base_drama_revision: Optional[int] = None


class DramaPatchProposal(BaseModel):
    proposal_id: str
    scope: str = "SPECULATIVE"         # SPECULATIVE / CANONICAL_CANDIDATE
    base_revision: int
    source: str = ""
    operations: list[dict[str, Any]] = Field(default_factory=list)
    expected_progress: list[Any] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    idempotency_key: Optional[str] = None


# ---------------------------------------------------------------------------
# 意图 / Directive / Beat / Shot
# ---------------------------------------------------------------------------

class ResolvedIntent(BaseModel):
    raw_text: str
    action: str = ""
    desire: Optional[str] = None
    strategy: Optional[str] = None
    desire_source: str = "UNKNOWN"     # PLAYER_EXPLICIT / PLAYER_CONFIRMED / INFERRED / UNKNOWN
    confidence: float = 0.0
    calibrated: bool = False
    impact: str = "MEDIUM"             # LOW / MEDIUM / HIGH
    clarification_required: bool = False


class DramaticDirective(BaseModel):
    id: str
    primary_function: str = "RESPOND_TO_PLAYER_ACTION"
    secondary_functions: list[str] = Field(default_factory=list)
    target_changes: list[dict[str, Any]] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    preferred_opportunities: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    player_input: str = ""


class OutcomeSpec(BaseModel):
    """Director 产出的分支结果说明（文本层）。模式区分见 ResponseMode。"""
    title: str
    text: str
    ops: list[PatchOperation] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    ending: Optional[str] = None       # ending family id
    kind: str = "investigation"        # investigation / social / risk / withdrawal
    mode: ResponseMode = ResponseMode.FULL_BEAT


class ShotPlan(BaseModel):
    id: str
    index: int
    title: str = ""
    duration: float = 5.0
    trim_start: float = 0.0
    trim_end: float = 5.0
    transition: str = "cut"
    subtitle: str = ""
    audio: str = "native"
    prompt: str = ""
    references: list[dict[str, Any]] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    status: str = "PLANNED"
    clip_path: Optional[str] = None


class SceneArtifact(BaseModel):
    media_type: Literal["video", "text"] = "video"
    id: str
    branch_id: str
    clip_refs: list[str] = Field(default_factory=list)
    assembled_path: Optional[str] = None    # 相对 media 目录
    quality_status: str = "PENDING"         # PENDING / READY / FAILED
    semantic_check: str = "not_run"
    technical_checks: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    duration: float = 0.0
    presentation_receipts: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ScenePacket（FR-068）：Narrative 的最小授权上下文
# ---------------------------------------------------------------------------

class ScenePacket(BaseModel):
    """Director knows the story; Narrative knows the scene.

    只含本幕必需信息：allowed_revelations 之外的秘密不出现在这里；
    forbidden_revelations 用于输出校验（泄露即拒绝），不放正文给模型。
    """
    branch_id: str = ""
    beat: str = ""                                # 已冻结的 StoryBeat / Branch Skeleton
    dramatic_function: str = "RESPOND_TO_PLAYER_ACTION"
    character_views: dict[str, Any] = Field(default_factory=dict)  # 人格/情绪/该角色可知内容
    scene_truth: list[str] = Field(default_factory=list)           # 本场景可见真相（已揭示）
    allowed_revelations: list[str] = Field(default_factory=list)
    forbidden_revelations: list[str] = Field(default_factory=list)  # 仅用于输出校验
    relationship_context: dict[str, int] = Field(default_factory=dict)
    style: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# BranchContract（推荐与自由输入统一的一级对象）
# ---------------------------------------------------------------------------

class BaseVersions(BaseModel):
    world: int
    drama: int
    arc: str
    wish: int


class ProviderRouteRecord(BaseModel):
    role: str
    primary: str
    selected: Optional[str]
    status: str
    reason: list[dict[str, str]] = Field(default_factory=list)
    profile: str = ""
    model: Optional[str] = None
    version: Optional[str] = None
    phase: str = ""
    at: int = Field(default_factory=now_ms)


class Branch(BaseModel):
    """BranchContract + SpeculativeBranch。未 CANONICAL 前不构成正式历史。"""
    id: str
    trace_id: str = ""
    session_id: str
    arc_id: str
    epoch_id: Optional[str] = None
    source: BranchSource = BranchSource.RECOMMENDATION
    rank: int = 1
    probability: float = 0.0
    label: str = ""
    summary: str = ""                            # 给玩家看的一句话推荐语
    intent: ResolvedIntent = Field(default_factory=lambda: ResolvedIntent(raw_text=""))
    outcome: Optional[OutcomeSpec] = None        # PLANNING 阶段产出
    directive: Optional[DramaticDirective] = None
    packet: Optional[ScenePacket] = None             # ScenePacket（FR-068）
    context: Optional[dict[str, Any]] = None         # WorkingContext
    interaction_mode: InteractionMode = InteractionMode.UNTIMED  # I02
    base_versions: BaseVersions
    read_set: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str = ""
    status: BranchStatus = BranchStatus.PREDICTED
    retry: int = 0
    fail_stage: Optional[str] = None
    last_error: Optional[str] = None
    invalidated_reason: Optional[str] = None
    created_at: int = Field(default_factory=now_ms)
    ready_at: Optional[int] = None
    expires_at: int = 0
    director_result: dict[str, Any] = Field(default_factory=dict)  # accepted FREE skeleton, never silently re-planned
    action_semantics: dict[str, Any] = Field(default_factory=dict)
    skill_decisions: list[dict[str, Any]] = Field(default_factory=list)
    causal_presentation: dict[str, Any] = Field(default_factory=dict)
    narrative: str = ""                          # NARRATIVE 阶段产出的 beat 文本
    caption: str = ""
    caption_speaker: str = ""
    media_language: Optional[MediaLanguage] = None  # Frozen before this beat is authored.
    dialogue: list[dict[str, str]] = Field(default_factory=list)
    media_clips: list[str] = Field(default_factory=list)   # GENERATING 产出的镜头文件
    shots: list[ShotPlan] = Field(default_factory=list)
    shot_count: int = 2
    jobs: list[str] = Field(default_factory=list)
    routes: list[ProviderRouteRecord] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    artifact: Optional[SceneArtifact] = None
    state_patch_proposal: Optional[StatePatchProposal] = None
    drama_patch_proposal: Optional[DramaPatchProposal] = None
    pipeline_events: list[dict[str, Any]] = Field(default_factory=list)
    commit_event: Optional[str] = None
    received: bool = False
    rollback_reason: Optional[str] = None


class RecommendationEpoch(BaseModel):
    id: str
    k: int = 0
    target_k: int = 3
    effective_k: int = 0
    status: str = "PLANNING"           # PLANNING / READY / BLOCKED / FAILED
    branch_ids: list[str] = Field(default_factory=list)
    ready_ids: list[str] = Field(default_factory=list)
    published: bool = False
    published_at: Optional[int] = None
    created_at: int = Field(default_factory=now_ms)
    reason: str = ""
    timed: bool = False
    options_exposed: bool = False
    options_exposed_at: Optional[int] = None


# ---------------------------------------------------------------------------
# Event / Receipt / Job / Trace
# ---------------------------------------------------------------------------

class Event(BaseModel):
    id: str
    session_id: str
    arc_id: str
    type: str
    summary: str
    operations: list[dict[str, Any]] = Field(default_factory=list)
    world_version: int = 0
    drama_revision: int = 0
    branch_id: Optional[str] = None
    raw_input: Optional[str] = None
    important: bool = False
    response_mode: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)
    at: int = Field(default_factory=now_ms)


class PresentationReceipt(BaseModel):
    id: str
    branch_id: Optional[str] = None
    artifact_id: Optional[str] = None
    method: str = "video"              # video / summary / text / opening
    knowledge_refs: list[str] = Field(default_factory=list)
    visible_segments: list[str] = Field(default_factory=list)
    event_id: Optional[str] = None
    at: int = Field(default_factory=now_ms)


class GenerationJob(BaseModel):
    id: str
    branch_id: Optional[str] = None
    shot_id: Optional[str] = None
    provider: str
    profile: str = ""
    node: str = ""
    status: JobStatus = JobStatus.QUEUED
    attempt: int = 0
    request: dict[str, Any] = Field(default_factory=dict)
    request_hash: str = ""
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: int = Field(default_factory=now_ms)
    finished_at: Optional[int] = None
    model_version: str = ""
    standalone: bool = False


class TraceSpan(BaseModel):
    id: str
    trace_id: str
    session_id: Optional[str] = None
    branch_id: Optional[str] = None
    name: str
    status: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    provider: str = "runtime"
    model: str = ""
    model_version: str = ""
    profile: str = ""
    downstream_target: str = ""
    duration_ms: int = 0
    skill_id: Optional[str] = None
    skill_version: Optional[str] = None
    at: int = Field(default_factory=now_ms)


class PlayerExperienceFeedback(BaseModel):
    id: str
    session_id: Optional[str] = None
    arc_id: Optional[str] = None
    name: str = ""
    relation: str = ""
    guided: str = ""
    liked: str
    reasons: str
    relevant_turn: str = ""
    wants_continue: str = ""
    at: int = Field(default_factory=now_ms)

/** 与后端契约对应的 TS 类型（PRD 10.1）。 */

export interface MechanicConfig {
  enabled: boolean;
  config: Record<string, any>;
  skill_id?: string; version?: string; tutorial?: string; title?: string; trigger?: string; state_patch_contract?: string[];
}

export interface ScenarioCharacter {
  id: string;
  identity: string;
  personality: string;
  desire: string;
  fear: string;
  secrets: string;
  knowledge: string;
  relationship: string;
  visual_state: string;
  global_character_id?: string | null;
  global_character_version?: number | null;
  outfit_id?: string | null;
  pose_refs?: string[];
  motion_refs?: string[];
  voice_id?: string | null;
  overlay_sources?: Record<string, string>;
  local_outfits?: CharacterOutfit[];
  reference_overrides?: Record<string, string | string[] | null>;
}

export interface CharacterOutfit {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  reference_assets?: string[];
  reference_slots?: Record<string, string | string[] | null>;
}

export interface WorldSpec {
  rules: string;
  lore: string;
  locations: string;
  constraints: string;
}

export interface DramaSpec {
  core_question: string;
  central_conflict: string;
  truth_model: string;
  secrets: string;
  misbeliefs: string;
  pressures: string;
  anchors: string;
  ending_families: string;
  foreshadows: string;
  forbidden_outcomes: string;
  timed_interactions: string;
}

export interface ThemeConfig {
  accent: string;
  font: string;
  density: string;
  subtitles: string;
  background: string;
}

export interface ScenarioDraft {
  id: string;
  title: string;
  description: string;
  genre: string;
  tone: string;
  play_style: string;
  player_character: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: string;
  owner: string;
  world: WorldSpec;
  characters: ScenarioCharacter[];
  drama: DramaSpec;
  mechanics: Record<string, MechanicConfig>;
  theme: ThemeConfig;
  authoring_intent?: string;
  mechanic_authoring_intent?: string;
  creator_projection?: Record<string, any>;
  reviewed: boolean;
  manual_edits: string[];
  locks: string[];
  changes: ChangeEntry[];
  updated_at: number;
}

export interface ChangeEntry {
  path: string;
  before: unknown;
  after: unknown;
  reason?: string;
  source: string;           // manual | instruct
  at: number;
}

export interface PublishCheck {
  id: string;
  label: string;
  ok: boolean;
  detail: string;
}

export interface ScenarioVersion {
  version_id: string;
  version: string;
  created_at: number;
}

export interface GlobalCharacter {
  id: string;
  name: string;
  bio: string;
  personality: string;
  appearance?: string;
  default_desire?: string; default_fear?: string; default_secrets?: string; default_knowledge?: string; default_relationship?: string;
  tags: string[];
  ref_front_asset?: string | null;
  ref_three_quarter_asset?: string | null;
  ref_side_asset?: string | null;
  ref_full_front_asset?: string | null;
  ref_full_side_asset?: string | null;
  ref_back_asset?: string | null;
  ref_other_assets: string[];
  ref_voice_asset?: string | null;
  ref_motion_asset?: string | null;
  ref_pose_assets?: string[];
  ref_motion_assets?: string[];
  alternate_voice_assets?: string[];
  outfits?: CharacterOutfit[];
  version: number;
  created_at: number;
  updated_at: number;
  status?: "ACTIVE" | "ARCHIVED";
}

export type CharacterAssetStatus = "GENERATED" | "CANDIDATE" | "APPROVED" | "CANONICAL" | "ARCHIVED";
export interface CharacterAsset {
  id: string; character_id: string; role: string; status: CharacterAssetStatus;
  url: string; source_asset_refs: string[]; outfit_id?: string | null;
  generation_job_id?: string | null; provenance: Record<string, any>; created_at: number;
}
export interface CharacterVersion {
  id: string; character_id: string; version: number; change_type: string;
  identity_spec: Record<string, any>; canonical_asset_refs: Record<string, string | string[] | null>;
  outfits: CharacterOutfit[];
  pose_refs?: string[];
  motion_refs?: string[];
  canonical_voice_ref?: string | null;
  alternate_voice_refs?: string[];
  created_at: number;
}
export interface CharacterSnapshot {
  id: string; scenario_version_id: string; global_character_id: string;
  character_version_id: string; character_version: number;
  frozen_identity: Record<string, any>; frozen_asset_refs: Record<string, string>;
  local_overrides: Record<string, any>;
}
export interface CharacterReferenceSelection {
  scene_or_shot_id: string; character_snapshot_id: string;
  selected_image_refs: string[]; voice_ref?: string | null; motion_ref?: string | null;
  selection_reason: string; developer_override: boolean;
}

export interface Asset {
  id: string;
  scenario_id: string;
  type: "image" | "voice" | "video";
  name: string;
  mime: string;
  size: number;
  duration?: number | null;
  storage_path: string;
  entity: string;
  binding: string;
  role: string;
  canonical: boolean;
  authorized: boolean;
  source: string;
  trim_start: number;
  trim_end: number;
  version: number;
  created_at: number;
}

export interface PlayerInfo {
  status: "OPENING_PREPARING" | "PLAYING" | "WAITING_DECISION" | "GENERATING_NEXT" | "FAILED_RECOVERABLE" | "LOADING" | "READY" | "ENDED" | "FAILED";
  scene_title: string;
  scene_text: string;
  caption: string;
  video_url: string;
  duration: number;
  lead: number;
  decision_open_at?: number;
  position: number;
}

export interface Recommendation {
  branch_id: string;
  label: string;
  summary: string;
  confidence: number;
  source: string;
  media_ready?: boolean;
}

export interface GeneratingItem {
  branch_id: string;
  label: string;
  phase_label: string;
}

export interface TimedView {
  active: boolean;
  kind: string;
  timeout_seconds: number;
  remaining_ms: number | null;
  selection_open: boolean;
  fallback_hint: string;
}

export interface PendingIntent {
  raw_text: string;
  action: string;
  desire: string;
  strategy: string;
  confidence: number;
  kind: "echo" | "clarification";
}

export interface KnownState {
  inventory: string[];
  inventory_labels?: Record<string, string>;
  relationships: { id: string; name: string; value: number }[];
  clues: { id: string; label: string }[];
  knowledge: { id: string; label: string }[];
}

export interface PlayerMessage {
  kind: "ack" | "merged" | "system";
  text: string;
  at: number;
}

export interface EndingTurn {
  at: number;
  arc_seq: number;
  label: string;
  title: string;
  artifact_id?: string | null;
  video_url?: string;
  duration?: number;
  timed?: boolean;
}

export interface EndingView {
  family: string | null;
  title: string;
  carried: {
    relationships: { id: string; name: string; value: number }[];
    inventory: string[];
    knowledge: { id: string; label: string }[];
    continue_note: string;
  };
  next_arc_hint: string;
  turns: EndingTurn[];
  arcs: { seq: number; ending_family: string | null; closed_at: number | null }[];
  continue_available: boolean;
  budget: { total: number; used: number };
}

/** 前情提要：OPENING_PREPARING 阶段立即可得的叙事文本（星战式 crawl）。
 * 全部由 scenario snapshot 组装，零生成；视频 READY 后接管淡出。 */
export interface OpeningInfo {
  location_line: string;    // "浣熊市 · 1998年9月"（world.locations 第一行 + 时间感）
  premise_lines: string[];  // premise 前 2–3 句
  identity_line: string;    // "你是 Leon S. Kennedy…"
  hook_line: string;        // core_question → 悬念句
  accent: string;           // 主题色（genre→色相映射）
}

export interface Wish {
  id: string;
  raw: string;
  status: string;
  version: number;
  scope: string;
  effective_boundary: string;
  history: any[];
}

export interface PlayerView {
  causal_presentation?: { action?: string; result?: string; visual_focus?: string; transition?: string } | null;
  session_id: string;
  scenario: { title: string; player_identity: string };
  arc: { seq: number; total: number };
  player: PlayerInfo;
  opening?: OpeningInfo;
  recommendations: Recommendation[];
  selected: { branch_id: string; label: string; status: string } | null;
  generating: GeneratingItem[];
  timed: TimedView | null;
  pending_intent: PendingIntent | null;
  last_failed_action?: { branch_id: string; label: string; raw_text: string;
    error: string; fail_stage: string } | null;
  known: KnownState;
  messages: PlayerMessage[];
  hint_chips: string[];
  ended: boolean;
  ending?: EndingView;
  pending_continuation: boolean;
  wishes: Wish[];
}

export interface BranchInfo {
  id: string;
  label: string;
  status: string;
  source: string;
  probability: number;
  fingerprint: string;
  last_error?: string | null;
  invalidated_reason?: string | null;
  rollback_reason?: string | null;
  routes: any[];
  pipeline_events: any[];
  artifact?: any;
  base_versions: any;
  outcome?: any;
}

export interface DevState {
  id: string;
  world: any;
  drama: any;
  pressures: any[];
  preferences: any;
  budget: any;
  epoch: any;
  branches: BranchInfo[];
  events: any[];
  wishes: Wish[];
  arcs: any[];
  counters: any;
  committed_keys: string[];
}

export interface ProviderHealth {
  status: string;
  errors: number;
  last_error?: string | null;
  circuit: string;
}

export interface SkillsRegistry {
  platform: SkillInfo[];
  mechanics: SkillInfo[];
}

export interface SkillInfo {
  id: string;
  version: string;
  kind: string;
  title: string;
  description: string;
  produces: string[];
  writes_state?: boolean;
  used_by?: string[];
  user_facing?: string;
  enabled?: boolean;
}

export interface ProfileStatus {
  profile: string;
  state: string;
  history: any[];
}

export interface Fixtures {
  confidence: string;
  response: string;
  leak_secret: boolean;
}

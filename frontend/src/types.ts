/** 与后端契约对应的 TS 类型（PRD 10.1）。 */

export interface MechanicConfig {
  enabled: boolean;
  config: Record<string, any>;
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
  tags: string[];
  ref_front_asset?: string | null;
  ref_side_asset?: string | null;
  ref_back_asset?: string | null;
  ref_other_assets: string[];
  ref_voice_asset?: string | null;
  ref_motion_asset?: string | null;
  version: number;
  created_at: number;
  updated_at: number;
}

export type CharacterAssetStatus = "GENERATED" | "CANDIDATE" | "APPROVED" | "CANONICAL" | "ARCHIVED";
export interface CharacterAsset {
  id: string; character_id: string; role: string; status: CharacterAssetStatus;
  url: string; source_asset_refs: string[]; outfit_id?: string | null;
  generation_job_id?: string | null; provenance: Record<string, any>; created_at: number;
}
export interface CharacterVersion {
  id: string; character_id: string; version: number; change_type: string;
  identity_spec: Record<string, any>; canonical_asset_refs: Record<string, string | null>;
  outfits: Array<{ id: string; name: string; description: string; reference_assets: string[]; is_default: boolean }>;
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
  status: "LOADING" | "PLAYING" | "READY" | "ENDED" | "FAILED";
  scene_title: string;
  scene_text: string;
  caption: string;
  video_url: string;
  duration: number;
  lead: number;
  position: number;
}

export interface Recommendation {
  branch_id: string;
  label: string;
  summary: string;
  confidence: number;
  source: string;
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
  session_id: string;
  scenario: { title: string; player_identity: string };
  arc: { seq: number; total: number };
  player: PlayerInfo;
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

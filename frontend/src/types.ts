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
  updated_at: number;
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

export interface Asset {
  id: string;
  scenario_id: string;
  type: "image" | "voice" | "video";
  name: string;
  mime: string;
  size: number;
  storage_path: string;
  entity: string;
  binding: string;
  role: string;
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
  player: PlayerInfo;
  recommendations: Recommendation[];
  generating: GeneratingItem[];
  ended: boolean;
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
}
